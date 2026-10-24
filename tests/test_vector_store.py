"""Comprehensive unit tests for the FaultSense FAISS vector store and indexing subsystem.

Validates embedding dimensions, cosine similarity search, vector-to-case mapping,
save/load persistence, atomic rebuilds, duplicate prevention, and corrupt file resilience.
"""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase
from src.retrieval.document_builder import DocumentBuilder
from src.retrieval.embeddings import (
    EMBEDDING_DIMENSION,
    DeterministicEmbeddingGenerator,
    normalize_vectors,
)
from src.retrieval.index_manager import IndexManager
from src.retrieval.vector_store import FAISSVectorStore, VectorRecord
from src.utils.exceptions import RetrievalError


class TestVectorStore(unittest.TestCase):
    """Tests FAISS CPU vector indexing, explicit metadata mapping, and persistence."""

    def setUp(self):
        self.embedder = DeterministicEmbeddingGenerator(dimension=EMBEDDING_DIMENSION)
        self.store = FAISSVectorStore(dimension=EMBEDDING_DIMENSION)

        self.case_1 = FaultCase(
            case_id="CASE-VEC-001",
            source_title="Field Service Report #101",
            source_reference="FSR-101",
            source_type="field_service_log",
            verification_status="verified",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Door reopened 3 times", "Optical curtain obstructed"],
            telemetry_summary={"door_cycles": 142000, "motor_temp_c": 48.5},
            confirmed_root_cause="Grit obstruction in lower door sill track",
            corrective_action="Cleaned lower track and adjusted safety eye",
            timestamp="2024-10-10T08:00:00Z",
            metadata={"is_synthetic": False},
        )

        self.case_2 = FaultCase(
            case_id="CASE-VEC-002",
            source_title="Field Service Report #102",
            source_reference="FSR-102",
            source_type="synthetic_illustrative",
            verification_status="unverified",
            subsystem="traction_drive",
            fault_code="E-VFD-404",
            symptoms=["Elevator emergency deceleration", "DC bus overvoltage error"],
            telemetry_summary={"dc_bus_voltage_v": 785.0, "motor_rpm": 1450},
            confirmed_root_cause="Degraded dynamic braking transistor in regenerative drive",
            corrective_action="Replaced brake chopper module",
            timestamp="2024-10-11T09:00:00Z",
            metadata={"is_synthetic": True},
        )

    def test_embedding_dimensions_and_unit_normalization(self):
        """Embeddings must strictly have dimension 384 and unit Euclidean length."""
        texts = ["Elevator door obstruction", "VVVF DC bus overvoltage"]
        vecs = self.embedder.encode(texts, normalize=True)

        self.assertEqual(vecs.shape, (2, 384))
        self.assertEqual(vecs.dtype, np.float32)

        # Verify unit norm ||v||_2 = 1.0 within tolerance
        norms = np.linalg.norm(vecs, axis=1)
        for n in norms:
            self.assertAlmostEqual(n, 1.0, places=5)

    def test_document_builder_canonical_format(self):
        """DocumentBuilder must format all key fields reproducibly."""
        doc = DocumentBuilder.build_document(self.case_1)
        self.assertIn("[ELEVATOR FAULT CASE: CASE-VEC-001]", doc)
        self.assertIn("Subsystem: door_system", doc)
        self.assertIn("Fault Code: E-DR-201", doc)
        self.assertIn("Grit obstruction in lower door sill track", doc)
        self.assertIn("door_cycles=142000", doc)

    def test_vector_to_case_mapping_and_retrieval(self):
        """FAISS row positions must map strictly to the corresponding case_ids."""
        added = self.store.add_cases([self.case_1, self.case_2], self.embedder)
        self.assertEqual(added, 2)
        self.assertEqual(self.store.total_vectors, 2)

        # Query vector close to case_1
        q_vec = self.embedder.encode("optical curtain obstructed in door sill", normalize=True)
        results = self.store.search(q_vec, top_k=2)

        self.assertEqual(len(results), 2)
        # Top match should be case_1
        self.assertEqual(results[0].case_id, "CASE-VEC-001")
        self.assertEqual(results[0].vector_id, 0)
        self.assertGreater(results[0].score, results[1].score)
        self.assertEqual(results[0].record.subsystem, "door_system")

    def test_duplicate_prevention(self):
        """Re-indexing an already existing case_id should be skipped to prevent orphaned rows."""
        self.store.add_cases([self.case_1], self.embedder)
        self.assertEqual(self.store.total_vectors, 1)

        # Add duplicate
        added_again = self.store.add_cases([self.case_1], self.embedder, skip_duplicates=True)
        self.assertEqual(added_again, 0)
        self.assertEqual(self.store.total_vectors, 1)

    def test_empty_dataset_handling(self):
        """Empty vector store should handle operations gracefully without crashing."""
        self.assertEqual(self.store.total_vectors, 0)

        # Search empty store
        dummy_q = np.ones((1, 384), dtype=np.float32)
        res = self.store.search(dummy_q)
        self.assertEqual(res, [])

        # Save and reload empty store
        with tempfile.TemporaryDirectory() as tmpdir:
            self.store.save(tmpdir)
            loaded_store = FAISSVectorStore(dimension=384)
            loaded_store.load(tmpdir)
            self.assertEqual(loaded_store.total_vectors, 0)

    def test_save_and_load_persistence_and_restart_survival(self):
        """Vector store must persist index, metadata, manifest, and survive application restart."""
        self.store.add_cases([self.case_1, self.case_2], self.embedder)

        with tempfile.TemporaryDirectory() as tmpdir:
            self.store.save(tmpdir)

            target_path = Path(tmpdir)
            self.assertTrue((target_path / "index.faiss").exists())
            self.assertTrue((target_path / "metadata.json").exists())
            self.assertTrue((target_path / "manifest.json").exists())

            # Verify metadata is pure JSON (security check: no pickle)
            meta_content = (target_path / "metadata.json").read_text(encoding="utf-8")
            parsed_meta = json.loads(meta_content)
            self.assertEqual(len(parsed_meta), 2)
            self.assertEqual(parsed_meta[0]["case_id"], "CASE-VEC-001")

            # Load into fresh vector store
            new_store = FAISSVectorStore(dimension=384)
            new_store.load(tmpdir)

            self.assertEqual(new_store.total_vectors, 2)

            # Query the newly reloaded store
            q_vec = self.embedder.encode("DC bus overvoltage regenerative brake", normalize=True)
            res = new_store.search(q_vec, top_k=1)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0].case_id, "CASE-VEC-002")

    def test_atomic_index_rebuild_from_repository(self):
        """IndexManager should atomically rebuild index from SQLite and update indexed flags."""
        repo = FaultCaseRepository(db_path=":memory:")
        repo.add([self.case_1, self.case_2])

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = IndexManager(
                embedding_generator=self.embedder,
                index_dir=tmpdir,
            )

            # Rebuild
            indexed_count = mgr.rebuild_from_repository(repo)
            self.assertEqual(indexed_count, 2)
            self.assertEqual(mgr.total_vectors, 2)

            # Check that database cases are marked as indexed
            c1_db = repo.get("CASE-VEC-001")
            self.assertTrue(c1_db.is_indexed)
            self.assertIsNotNone(c1_db.indexed_at)

            # Search through index manager
            search_results = mgr.search(query="optical curtain", top_k=1)
            self.assertEqual(len(search_results), 1)
            self.assertEqual(search_results[0].case_id, "CASE-VEC-001")

        repo.close()

    def test_corrupt_index_file_rejection(self):
        """Loading a corrupt or truncated index file must raise RetrievalError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "index.faiss").write_text("corrupted_binary_garbage", encoding="utf-8")
            (p / "metadata.json").write_text("[]", encoding="utf-8")

            bad_store = FAISSVectorStore(dimension=384)
            with self.assertRaises(RetrievalError):
                bad_store.load(tmpdir)

    def test_corrupt_metadata_json_rejection(self):
        """Loading corrupted JSON metadata must raise RetrievalError."""
        self.store.add_cases([self.case_1], self.embedder)

        with tempfile.TemporaryDirectory() as tmpdir:
            self.store.save(tmpdir)
            # Corrupt metadata file
            (Path(tmpdir) / "metadata.json").write_text("{ unclosed_json: ", encoding="utf-8")

            bad_store = FAISSVectorStore(dimension=384)
            with self.assertRaises(RetrievalError):
                bad_store.load(tmpdir)

    def test_dimension_mismatch_rejection(self):
        """Loading index with dimension mismatch must raise RetrievalError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            manifest = {"dimension": 768, "total_vectors": 1}
            (p / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (p / "index.faiss").touch()
            (p / "metadata.json").write_text("[]", encoding="utf-8")

            bad_store = FAISSVectorStore(dimension=384)
            with self.assertRaises(RetrievalError) as ctx:
                bad_store.load(tmpdir)
            self.assertIn("dimension mismatch", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
