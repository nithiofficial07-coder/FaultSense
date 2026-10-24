"""Unit tests for the FaultSense vector embedding and indexing adapter."""

import unittest

from fault_sense.indexing_interface import FaultCaseIndexingAdapter
from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase


class TestIndexingInterface(unittest.TestCase):
    """Tests embedding document generation and vector database formatting."""

    def setUp(self):
        self.adapter = FaultCaseIndexingAdapter()
        self.repo = FaultCaseRepository(db_path=":memory:")

        self.case = FaultCase(
            case_id="CASE-VEC-001",
            source_title="Field Dispatch #88",
            source_reference="SR-88",
            source_type="field_service_log",
            verification_status="verified",
            subsystem="braking_system",
            fault_code="E-BR-10",
            symptoms=["Brake shoe chatter", "Deceleration jerk"],
            telemetry_summary={"brake_shoe_gap_mm": 1.2, "lift_time_ms": 320},
            confirmed_root_cause="Worn bronze sleeve bushing on brake arm pivot",
            corrective_action="Replaced pivot bushings and adjusted air gap to 0.4mm",
            timestamp="2024-10-18T12:00:00Z",
            metadata={"is_synthetic": False, "speed_mps": 2.5},
        )

    def test_case_to_document(self):
        """Should convert FaultCase to EmbeddingDocument with correct text and metadata."""
        doc = self.adapter.case_to_document(self.case)
        self.assertEqual(doc.doc_id, "CASE-VEC-001")
        self.assertIn("Worn bronze sleeve bushing", doc.text)
        self.assertEqual(doc.metadata["subsystem"], "braking_system")
        self.assertEqual(doc.metadata["fault_code"], "E-BR-10")
        self.assertFalse(doc.metadata["is_synthetic"])

    def test_chroma_payload_format(self):
        """to_chroma_payload should format records into ids, documents, metadatas arrays."""
        doc = self.adapter.case_to_document(self.case)
        payload = self.adapter.to_chroma_payload([doc])

        self.assertIn("ids", payload)
        self.assertIn("documents", payload)
        self.assertIn("metadatas", payload)
        self.assertEqual(payload["ids"], ["CASE-VEC-001"])
        self.assertEqual(len(payload["documents"]), 1)
        self.assertEqual(payload["metadatas"][0]["fault_code"], "E-BR-10")

    def test_generic_vector_payload_format(self):
        """to_generic_vector_payload should format records into id, text, payload structures."""
        doc = self.adapter.case_to_document(self.case)
        payload = self.adapter.to_generic_vector_payload([doc])

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], "CASE-VEC-001")
        self.assertEqual(payload[0]["payload"]["subsystem"], "braking_system")

    def test_end_to_end_indexing_flow(self):
        """Test retrieving pending documents, preparing them, and marking them as indexed."""
        self.repo.add(self.case)

        # 1. Fetch pending documents
        pending_docs = self.adapter.get_pending_documents(self.repo)
        self.assertEqual(len(pending_docs), 1)
        self.assertEqual(pending_docs[0].doc_id, "CASE-VEC-001")

        # 2. Confirm indexed
        updated_count = self.adapter.confirm_indexed(self.repo, [d.doc_id for d in pending_docs])
        self.assertEqual(updated_count, 1)

        # 3. Verify no pending docs remain
        remaining_pending = self.adapter.get_pending_documents(self.repo)
        self.assertEqual(len(remaining_pending), 0)


if __name__ == "__main__":
    unittest.main()
