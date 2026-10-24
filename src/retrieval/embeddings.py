"""Embedding generation and vector normalization for FaultSense.

Generates dense vector embeddings using all-MiniLM-L6-v2. Normalizes vectors
to unit L2-norm so FAISS IndexFlatIP computes exact Cosine Similarity.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from config.settings import get_settings
from src.utils.exceptions import RetrievalError
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Standard embedding vector dimension for all-MiniLM-L6-v2
EMBEDDING_DIMENSION = 384
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class BaseEmbeddingGenerator(ABC):
    """Abstract interface for dense vector embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the vector dimensionality produced by the model."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the canonical model identifier."""

    @abstractmethod
    def encode(
        self, texts: Union[str, Sequence[str]], normalize: bool = True
    ) -> np.ndarray:
        """Encodes texts into an (N, dimension) float32 NumPy array."""


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """Normalizes an (N, d) float32 matrix to unit Euclidean (L2) length.

    Mathematical Basis:
    For vectors u, v where ||u||_2 = 1 and ||v||_2 = 1, the inner product
    <u, v> equals the Cosine Similarity:
        <u, v> = (u . v) / (||u|| * ||v||) = cos(theta)
    This allows FAISS IndexFlatIP to perform exact cosine similarity matching.
    """
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    # Avoid division by zero
    norms = np.maximum(norms, 1e-12)
    normalized = vectors / norms
    return normalized.astype(np.float32)


class SentenceTransformerEmbeddingGenerator(BaseEmbeddingGenerator):
    """Production embedding generator using sentence-transformers (all-MiniLM-L6-v2)."""

    _SHARED_MODEL_CACHE: Dict[Tuple[str, str, Optional[str]], Any] = {}

    def __init__(
        self,
        model_name: Optional[str] = None,
        cache_dir: Optional[str] = None,
        device: str = "cpu",
    ):
        settings = get_settings()
        self._model_name = model_name or settings.embedding_model or DEFAULT_MODEL_NAME
        self._cache_dir = cache_dir
        self._device = device
        self._model = None  # Lazy loaded

    @property
    def dimension(self) -> int:
        return EMBEDDING_DIMENSION

    @property
    def model_name(self) -> str:
        return self._model_name

    def _load_model(self) -> None:
        """Lazily imports and instantiates SentenceTransformer model with class-level caching."""
        if self._model is not None:
            return

        cache_key = (self._model_name, self._device, self._cache_dir)
        if cache_key in self._SHARED_MODEL_CACHE:
            self._model = self._SHARED_MODEL_CACHE[cache_key]
            return

        try:
            logger.info("Loading embedding model '%s' on %s...", self._model_name, self._device)
            from sentence_transformers import SentenceTransformer

            loaded_model = SentenceTransformer(
                self._model_name,
                cache_folder=self._cache_dir,
                device=self._device,
            )
            self._SHARED_MODEL_CACHE[cache_key] = loaded_model
            self._model = loaded_model
            logger.info("Embedding model '%s' loaded and cached successfully.", self._model_name)
        except Exception as exc:
            msg = (
                f"Failed to load embedding model '{self._model_name}': {exc}. "
                "Ensure network connectivity for the initial model download or configure a local model cache."
            )
            logger.error(msg)
            raise RetrievalError(msg, details={"model_name": self._model_name, "error": str(exc)}) from exc

    def encode(
        self, texts: Union[str, Sequence[str]], normalize: bool = True
    ) -> np.ndarray:
        """Generates normalized embeddings for input text strings."""
        self._load_model()

        if isinstance(texts, str):
            input_list = [texts]
        else:
            input_list = list(texts)

        if not input_list:
            return np.empty((0, self.dimension), dtype=np.float32)

        try:
            embeddings = self._model.encode(
                input_list,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=normalize,
            )
        except Exception as exc:
            raise RetrievalError(f"Embedding encoding failure: {exc}") from exc

        embeddings = np.asarray(embeddings, dtype=np.float32)

        # Defensive post-normalization to guarantee unit L2 norm
        if normalize:
            embeddings = normalize_vectors(embeddings)

        # Validate dimensional integrity
        if embeddings.shape[1] != self.dimension:
            raise RetrievalError(
                f"Model dimension mismatch: expected {self.dimension}, got {embeddings.shape[1]}"
            )

        return embeddings


class DeterministicEmbeddingGenerator(BaseEmbeddingGenerator):
    """Fast, deterministic, offline embedding generator for test suites.

    Produces unit-normalized 384-dimensional float32 vectors via text hashing
    without requiring external model weights or internet access.
    """

    def __init__(self, dimension: int = EMBEDDING_DIMENSION):
        self._dimension = dimension
        self._model_name = "deterministic-hash-384"

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def encode(
        self, texts: Union[str, Sequence[str]], normalize: bool = True
    ) -> np.ndarray:
        """Generates deterministic pseudo-semantic vectors based on token hashes."""
        if isinstance(texts, str):
            input_list = [texts]
        else:
            input_list = list(texts)

        if not input_list:
            return np.empty((0, self.dimension), dtype=np.float32)

        vectors = np.zeros((len(input_list), self.dimension), dtype=np.float32)

        for i, text in enumerate(input_list):
            words = text.lower().split()
            if not words:
                words = ["empty"]

            # Accumulate hashed projections for tokens
            row = np.zeros(self.dimension, dtype=np.float32)
            for word in words:
                h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                val = ((h >> 8) % 100) / 50.0 - 1.0  # -1.0 to +1.0
                row[idx] += val

            vectors[i] = row

        if normalize:
            vectors = normalize_vectors(vectors)

        return vectors
