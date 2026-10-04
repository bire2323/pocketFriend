"""Calibrate the relevance threshold: real questions vs off-topic noise."""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import rag  # noqa: E402

RELEVANT = [
    "Which normal form removes partial dependency?",
    "What is a dirty read?",
    "How does HAVING differ from WHERE?",
    "Explain the ACID properties",
    "What is a foreign key constraint?",
    "How do indexes speed up queries?",
    "What is two phase locking?",
    "What causes a phantom read?",
    "When is a decomposition lossless?",
    "What is the difference between serializable and read committed?",
]

IRRELEVANT = [
    "What is the capital city of Peru?",
    "How do I bake sourdough bread?",
    "Summarise the plot of Hamlet",
    "What is the boiling point of water?",
    "Explain photosynthesis briefly",
    "Who won the 1998 world cup?",
    "How do I change a bicycle gear?",
]


def top_score(question: str) -> tuple[float, str]:
    hits = rag.search_documents(question, n_results=3)
    if not hits:
        return 0.0, "-"
    return hits[0].score, hits[0].short_label


if __name__ == "__main__":
    print("RELEVANT questions")
    relevant_scores = []
    for question in RELEVANT:
        score, where = top_score(question)
        relevant_scores.append(score)
        print(f"  {score:.3f}  {question}  ->  {where}")

    print("\nIRRELEVANT questions")
    irrelevant_scores = []
    for question in IRRELEVANT:
        score, where = top_score(question)
        irrelevant_scores.append(score)
        print(f"  {score:.3f}  {question}  ->  {where}")

    print(f"\nmin(relevant)={min(relevant_scores):.3f}")
    print(f"max(irrelevant)={max(irrelevant_scores):.3f}")
    midpoint = (min(relevant_scores) + max(irrelevant_scores)) / 2
    print(f"suggested threshold={midpoint:.3f}")