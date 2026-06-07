import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.faq_rag import _split_into_chunks, answer_faq_question, build_faq_index, load_faq_pdf, retrieve_faq_context


class FaqRagTests(unittest.TestCase):
    def test_load_faq_pdf_handles_missing_file_gracefully(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_faq_pdf("data/does-not-exist.pdf")

    def test_chunking_returns_chunks(self) -> None:
        chunks = _split_into_chunks(
            "Q: What is the cancellation policy? A: You can cancel before midnight.\n\nQ: Are pets allowed? A: Pets are allowed in some rooms.",
            page_number=1,
            source_name="sample.pdf",
        )

        self.assertTrue(chunks)
        self.assertIn("chunk_id", chunks[0])
        self.assertIn("page", chunks[0])

    def test_hybrid_retrieval_returns_relevant_chunks(self) -> None:
        sample_chunks = [
            {"chunk_id": "faq_000", "text": "Q: What is the cancellation policy? A: You can cancel before midnight.", "source": "sample.pdf", "page": 1},
            {"chunk_id": "faq_001", "text": "Q: Are pets allowed? A: Pets are allowed in some rooms.", "source": "sample.pdf", "page": 2},
        ]

        with mock.patch("tools.faq_rag.load_faq_pdf", return_value=sample_chunks):
            results = retrieve_faq_context("cancellation policy", top_k=2, path="sample.pdf")

        self.assertTrue(results)
        self.assertIn("combined_score", results[0])
        self.assertGreaterEqual(results[0]["combined_score"], 0.0)
        self.assertTrue(any("cancellation" in chunk["text"].lower() for chunk in results))

    def test_answer_faq_question_refuses_when_context_is_insufficient(self) -> None:
        sample_chunks = [
            {"chunk_id": "faq_000", "text": "Q: What is the weather today? A: The weather is not in this FAQ document.", "source": "sample.pdf", "page": 1},
        ]

        with mock.patch("tools.faq_rag.load_faq_pdf", return_value=sample_chunks):
            answer = answer_faq_question("What is the refund policy?", path="sample.pdf")

        self.assertIn("does not contain enough information", answer["answer"])
        self.assertEqual(answer["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
