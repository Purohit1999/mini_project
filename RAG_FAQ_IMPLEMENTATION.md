# RAG FAQ Implementation Guide

## What RAG is
RAG (Retrieval-Augmented Generation) retrieves relevant text from a document and uses that text as the source of truth for an answer. This keeps the answer grounded in the Expedia FAQ PDF instead of guessing.

## What FAISS does
FAISS is used for fast dense vector search. It compares the question to FAQ chunks in a vector space and finds the closest matches.

## What sparse retrieval does
Sparse retrieval uses a simple local keyword overlap / TF-IDF style ranking. It helps catch exact terms like "cancellation" or "refund" even when the dense score is not enough.

## What dense retrieval does
Dense retrieval uses local deterministic embeddings to understand the meaning of the question and retrieve related FAQ chunks.

## How hybrid retrieval works
The FAQ feature combines:
1. Dense retrieval via FAISS + local embeddings
2. Sparse retrieval via local keyword weighting
3. A merged score that ranks the best chunks and removes duplicates

## How the Expedia FAQ PDF is used
The loader reads `data/E_FAQs.pdf`, extracts text using `pypdf`, splits the content into FAQ-style chunks, and stores source metadata such as page number and chunk id.

## How to run the FAQ feature
- Streamlit: `streamlit run streamlit_app.py`
- CLI: `python main.py --faq "What is Expedia's cancellation policy?"`

## How to rebuild the index
The FAQ index is built on demand from the PDF file at runtime. If the PDF is updated, rerun the FAQ search and the index is rebuilt from the latest document.

## How to test it
Run:

```bash
python -m unittest discover -s tests
```

The test suite now includes FAQ-specific tests for PDF loading, chunking, hybrid retrieval, and insufficient-context refusal.
