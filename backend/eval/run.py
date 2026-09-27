"""Measure retrieval quality on the real demo course.

Indexes the committed OpenStax PDFs into a throwaway in-memory store using the
same chunking and embedding settings as production, then scores every question
in ``golden_set.jsonl``. No API key is needed.

Run from the ``backend`` directory::

    python -m eval.run            # default k from settings (top_k)
    python -m eval.run --k 8 --show-misses
"""

import argparse
from pathlib import Path

from rag.chunking import chunk_text
from rag.config import get_settings
from rag.embeddings import Embedder
from rag.evaluation import evaluate, load_golden
from rag.pdf import extract_text
from rag.store import DEFAULT_DIM, SearchHit, VectorStore

HERE = Path(__file__).parent
GOLDEN = HERE / "golden_set.jsonl"
DATA_DIR = HERE.parent / "seed" / "data"
COURSE_ID = "EVAL"


def build_store(embedder: Embedder) -> VectorStore:
    """Index every demo PDF into a fresh in-memory store."""
    settings = get_settings()
    store = VectorStore(dim=DEFAULT_DIM)
    for pdf in sorted(DATA_DIR.glob("*.pdf")):
        chunks = chunk_text(
            extract_text(str(pdf)), size=settings.chunk_size, overlap=settings.chunk_overlap
        )
        store.add(COURSE_ID, pdf.name, chunks, embedder.embed(chunks))
    return store


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--k", type=int, default=get_settings().top_k)
    parser.add_argument("--show-misses", action="store_true")
    args = parser.parse_args()

    embedder = Embedder()
    store = build_store(embedder)
    items = load_golden(GOLDEN)

    def retrieve(question: str, k: int) -> list[SearchHit]:
        return store.search(COURSE_ID, embedder.embed_query(question), k=k)

    report = evaluate(retrieve, items, k=args.k)
    print(f"questions : {len(items)}  (chunks indexed: {store.count(COURSE_ID)})")
    print(f"Hit@{report.k:<5}: {report.hit_rate:.1%}")
    print(f"MRR      : {report.mrr:.3f}")
    print(f"latency  : {report.mean_latency_ms:.1f} ms / question")
    if args.show_misses:
        by_id = {i.id: i for i in items}
        for miss in report.misses:
            print(f"  miss {miss}: {by_id[miss].question}")


if __name__ == "__main__":
    main()
