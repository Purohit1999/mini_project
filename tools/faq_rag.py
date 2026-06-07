"""Lightweight FAQ RAG helpers for the Expedia FAQ PDF.

This module uses:
- safe PDF extraction via pypdf
- deterministic local embeddings for dense retrieval
- a simple sparse TF-IDF style scoring layer
- FAISS for fast vector similarity search when available
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover - dependency is optional at runtime
    faiss = None  # type: ignore

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - handled by runtime install
    PdfReader = None  # type: ignore

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - optional fallback
    fitz = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FAQ_PATH = PROJECT_ROOT / "data" / "E_FAQs.pdf"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text)
    return [token for token in tokens if len(token) > 1]


def _split_into_chunks(text: str, page_number: int, source_name: str, chunk_id_start: int = 0) -> List[Dict[str, Any]]:
    """Split FAQ text into small, meaningful chunks.

    The chunks are designed to preserve FAQ-style question/answer layout when possible.
    """
    raw_blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    chunks: List[Dict[str, Any]] = []
    chunk_id = chunk_id_start

    for block in raw_blocks:
        block_text = _normalize_text(block)
        if not block_text:
            continue

        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", block_text) if part.strip()]
        current = ""

        for sentence in sentences:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= 220:
                current = candidate
                continue
            if current:
                chunks.append({
                    "chunk_id": f"faq_{chunk_id:03d}",
                    "text": current,
                    "source": source_name,
                    "page": page_number,
                })
                chunk_id += 1
                current = sentence
        if current:
            chunks.append({
                "chunk_id": f"faq_{chunk_id:03d}",
                "text": current,
                "source": source_name,
                "page": page_number,
            })
            chunk_id += 1

    if not chunks:
        chunks.append({
            "chunk_id": f"faq_{chunk_id_start:03d}",
            "text": block_text[:500],
            "source": source_name,
            "page": page_number,
        })

    return chunks


def load_faq_pdf(path: str | Path = DEFAULT_FAQ_PATH) -> List[Dict[str, Any]]:
    """Load and chunk the Expedia FAQ PDF.

    Returns a list of chunk dictionaries with metadata.
    Raises:
        FileNotFoundError: If the PDF file does not exist.
        RuntimeError: If pypdf is unavailable or text extraction fails completely.
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"FAQ PDF not found at {pdf_path}. Place the file under data/E_FAQs.pdf before using FAQ search.")

    if PdfReader is None:
        raise RuntimeError("pypdf is required for FAQ PDF loading. Install the project requirements and try again.")

    reader = PdfReader(str(pdf_path))
    chunks: List[Dict[str, Any]] = []

    # First, try regular text extraction. If the PDF is image-based, fall back to OCR.
    ocr_reader = None
    if easyocr is not None:
        try:
            ocr_reader = easyocr.Reader(["en"], gpu=False)
        except Exception:
            ocr_reader = None

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip() and fitz is not None:
            try:
                with fitz.open(str(pdf_path)) as doc:
                    text = doc.load_page(page_number - 1).get_text("text") or ""
            except Exception:
                text = ""

        if not text.strip() and fitz is not None and ocr_reader is not None:
            try:
                with fitz.open(str(pdf_path)) as doc:
                    pix = doc.load_page(page_number - 1).get_pixmap(matrix=fitz.Matrix(2, 2))
                    image_bytes = pix.tobytes("png")
                from io import BytesIO
                from PIL import Image

                image = Image.open(BytesIO(image_bytes)).convert("RGB")
                text = "\n".join(ocr_reader.readtext(np.asarray(image), detail=0))
            except Exception:
                text = ""

        if not text.strip():
            continue
        chunks.extend(_split_into_chunks(text, page_number, pdf_path.name, chunk_id_start=len(chunks)))

    if not chunks:
        raise RuntimeError("The FAQ PDF could not be read into text chunks. The document may be image-only or encrypted.")

    return chunks


def _deterministic_embedding(text: str, dim: int = 64) -> np.ndarray:
    """Create a deterministic local embedding for dense retrieval.

    This avoids any dependency on OpenAI embeddings and works in offline mode.
    """
    tokens = _tokenize(text)
    if not tokens:
        return np.zeros(dim, dtype=np.float32)

    vector = np.zeros(dim, dtype=np.float32)
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        seed = int.from_bytes(digest, byteorder="big", signed=False)
        rng = np.random.default_rng(seed)
        vector += rng.standard_normal(dim)

    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return (vector / norm).astype(np.float32)


def build_faq_index(path: str | Path = DEFAULT_FAQ_PATH) -> Dict[str, Any]:
    """Build a hybrid index from the FAQ PDF chunks."""
    chunks = load_faq_pdf(path)
    embeddings = np.stack([_deterministic_embedding(chunk["text"]) for chunk in chunks], axis=0).astype(np.float32)
    normalized_embeddings = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9)

    dense_index = None
    if faiss is not None:
        dense_index = faiss.IndexFlatIP(normalized_embeddings.shape[1])
        dense_index.add(normalized_embeddings)

    # Simple sparse TF-IDF style retrieval structure.
    vocab = sorted(set(token for chunk in chunks for token in _tokenize(chunk["text"])))
    doc_vectors = []
    doc_freq = Counter()
    for chunk in chunks:
        counts = Counter(_tokenize(chunk["text"]))
        doc_freq.update(counts.keys())
        doc_vectors.append(counts)

    idf = {term: math.log((1 + len(chunks)) / (1 + doc_freq.get(term, 0)) + 1.0) for term in vocab}

    return {
        "chunks": chunks,
        "embeddings": normalized_embeddings,
        "dense_index": dense_index,
        "idf": idf,
        "doc_vectors": doc_vectors,
        "vocab": vocab,
        "source_path": str(Path(path)),
    }


def _sparse_scores(question: str, index: Dict[str, Any]) -> List[float]:
    question_tokens = Counter(_tokenize(question))
    if not question_tokens:
        return [0.0 for _ in index["chunks"]]

    q_norm = math.sqrt(sum((weight * weight) for weight in question_tokens.values()))
    if q_norm == 0:
        return [0.0 for _ in index["chunks"]]

    scores = []
    for counts in index["doc_vectors"]:
        dot = 0.0
        for token, count in counts.items():
            weight = count * index["idf"].get(token, 1.0)
            dot += weight * question_tokens.get(token, 0)
        doc_norm = math.sqrt(sum((count * index["idf"].get(token, 1.0)) ** 2 for token, count in counts.items()))
        scores.append(dot / (doc_norm * q_norm + 1e-9))
    return scores


def retrieve_faq_context(question: str, top_k: int = 5, path: str | Path = DEFAULT_FAQ_PATH) -> List[Dict[str, Any]]:
    """Retrieve relevant FAQ chunks using dense + sparse hybrid ranking."""
    index = build_faq_index(path)
    chunks = list(index["chunks"])
    if not chunks:
        return []

    question_embedding = _deterministic_embedding(question).astype(np.float32)
    question_embedding = question_embedding / (np.linalg.norm(question_embedding) + 1e-9)

    sparse_scores = _sparse_scores(question, index)
    dense_scores = [0.0] * len(chunks)

    if index["dense_index"] is not None and faiss is not None:
        scores, _ = index["dense_index"].search(question_embedding.reshape(1, -1), min(top_k, len(chunks)))
        dense_scores = scores[0].tolist()
    else:
        # Fallback when FAISS is unavailable: use a lightweight lexical score.
        dense_scores = [1.0 if token in question.lower() else 0.0 for token in [t for c in chunks for t in _tokenize(c["text"])] ]
        dense_scores = [0.0] * len(chunks)
        for i, chunk in enumerate(chunks):
            chunk_tokens = set(_tokenize(chunk["text"]))
            question_tokens = set(_tokenize(question))
            dense_scores[i] = len(chunk_tokens & question_tokens) / (len(question_tokens) or 1)

    # Normalise both scores into comparable ranges.
    max_sparse = max(sparse_scores) if sparse_scores else 0.0
    min_sparse = min(sparse_scores) if sparse_scores else 0.0
    max_dense = max(dense_scores) if dense_scores else 0.0
    min_dense = min(dense_scores) if dense_scores else 0.0

    def normalise(values: List[float], maximum: float, minimum: float) -> List[float]:
        if maximum == minimum:
            return [0.0 for _ in values]
        return [(value - minimum) / (maximum - minimum + 1e-9) for value in values]

    sparse_norm = normalise(sparse_scores, max_sparse, min_sparse)
    dense_norm = normalise(dense_scores, max_dense, min_dense)

    combined = []
    for i, chunk in enumerate(chunks):
        combined_score = 0.55 * dense_norm[i] + 0.45 * sparse_norm[i]
        combined.append({
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "source": chunk["source"],
            "page": chunk["page"],
            "dense_score": float(dense_scores[i]),
            "sparse_score": float(sparse_scores[i]),
            "combined_score": float(combined_score),
        })

    combined.sort(key=lambda item: item["combined_score"], reverse=True)
    deduped = []
    seen = set()
    for item in combined:
        if item["chunk_id"] in seen:
            continue
        seen.add(item["chunk_id"])
        deduped.append(item)
        if len(deduped) == top_k:
            break

    return deduped


def answer_faq_question(question: str, path: str | Path = DEFAULT_FAQ_PATH) -> Dict[str, Any]:
    """Answer a question using the Expedia FAQ PDF as the only source of truth."""
    if not (question or "").strip():
        return {
            "answer": "Please enter an Expedia FAQ question to search the FAQ document.",
            "sources": [],
            "confidence": "low",
            "retrieval_note": "No question was provided.",
        }

    try:
        results = retrieve_faq_context(question, top_k=4, path=path)
    except (FileNotFoundError, RuntimeError) as exc:
        return {
            "answer": "The Expedia FAQ document is not available right now, so I cannot answer from the FAQ source.",
            "sources": [],
            "confidence": "low",
            "retrieval_note": str(exc),
        }

    if not results or results[0]["combined_score"] < 0.08:
        return {
            "answer": "The Expedia FAQ document does not contain enough information to answer that question confidently.",
            "sources": [],
            "confidence": "low",
            "retrieval_note": "No sufficiently relevant FAQ chunk matched the question.",
        }

    top_chunk = results[0]
    answer_text = top_chunk["text"]
    if "?" in answer_text and "A:" in answer_text:
        answer_text = answer_text.split("A:", 1)[-1].strip()
    elif answer_text.startswith("Q:") and "A:" in answer_text:
        answer_text = answer_text.split("A:", 1)[-1].strip()
    elif "?" in answer_text:
        answer_text = answer_text.split("?", 1)[-1].strip().lstrip(":- ")

    answer = answer_text if answer_text else top_chunk["text"]
    answer = answer.replace("\n", " ")
    answer = re.sub(r"\s+", " ", answer).strip()

    return {
        "answer": f"Based on the Expedia FAQ document, {answer}",
        "sources": [
            {
                "chunk_id": top_chunk["chunk_id"],
                "page": top_chunk["page"],
                "source": top_chunk["source"],
            }
        ],
        "confidence": "high" if top_chunk["combined_score"] >= 0.25 else "medium",
        "retrieval_note": "Hybrid retrieval used FAISS-style dense scoring and local sparse scoring.",
        "retrieved_chunks": results,
    }
