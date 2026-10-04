"""Ad-hoc end-to-end check of the RAG pipeline (not part of the app)."""

import shutil
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, rag  # noqa: E402

if __name__ == "__main__":
    shutil.rmtree(config.CHROMA_DIR, ignore_errors=True)
    for pdf in sorted(config.DEMO_DIR.glob("*.pdf")):
        summary = rag.index_document(str(pdf), filename=pdf.name)
        print("indexed:", summary)

    print("\ndocuments:", rag.document_count(), "chunks:", rag.chunk_count())

    questions = [
        "Which normal form removes partial dependency?",
        "What is a dirty read?",
        "How does HAVING differ from WHERE?",
        "What is the capital city of Peru?",
    ]
    for question in questions:
        print("\n" + "=" * 70)
        print("Q:", question)
        hits = rag.search_documents(question, n_results=4)
        for hit in hits:
            print(f"   score={hit.score:.3f} {hit.short_label}")
        answer = rag.answer_question(question)
        print("grounded:", answer.grounded)
        print("sources :", [s.label for s in answer.sources])
        print("answer  :", answer.text[:400].replace("\n", " "))
        if answer.note:
            print("note    :", answer.note[:200])