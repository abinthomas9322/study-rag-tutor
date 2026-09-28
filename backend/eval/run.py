"""Measure retrieval quality on the real demo course.

Indexes the committed OpenStax PDFs into a throwaway in-memory store using the
same chunking and embedding settings as production, then scores every question
in ``golden_set.jsonl``. No API key is needed.

Run from the ``backend`` directory::

    python -m eval.run            # default k from settings (top_k)
    python -m eval.run --k 8 --show-misses
    python -m eval.run --mode all  # compare every retrieval mode
    python -m eval.run --mode hybrid+rerank --min-hit 0.95  # CI quality gate
"""

import argparse
from pathlib import Path

from rag.chunking import chunk_text
from rag.config import get_settings
from rag.embeddings import Embedder
from rag.evaluation import Retriever, evaluate, load_golden
from rag.pdf import extract_text
from rag.rerank import Reranker
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


MODES = ("vector", "keyword", "hybrid", "vector+rerank", "hybrid+rerank")
CANDIDATES = 20  # first-stage hits handed to the reranker


def make_retriever(
    mode: str, store: VectorStore, embedder: Embedder, reranker: Reranker
) -> Retriever:
    """Build a ``(question, k) -> hits`` function for one retrieval mode."""
    base, _, rerank = mode.partition("+")

    def retrieve(question: str, k: int) -> list[SearchHit]:
        depth = CANDIDATES if rerank else k
        if base == "keyword":
            hits = store.keyword_search(COURSE_ID, question, k=depth)
        elif base == "hybrid":
            vector = embedder.embed_query(question)
            hits = store.hybrid_search(COURSE_ID, question, vector, k=depth)
        else:
            hits = store.search(COURSE_ID, embedder.embed_query(question), k=depth)
        return reranker.rerank(question, hits, k=k) if rerank else hits

    return retrieve


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--k", type=int, default=get_settings().top_k)
    parser.add_argument("--mode", choices=[*MODES, "all"], default="all")
    parser.add_argument("--show-misses", action="store_true")
    parser.add_argument(
        "--min-hit", type=float, default=None, help="exit non-zero if any mode scores below this"
    )
    args = parser.parse_args()

    embedder = Embedder()
    reranker = Reranker()
    store = build_store(embedder)
    items = load_golden(GOLDEN)
    by_id = {i.id: i for i in items}
    print(f"questions: {len(items)}  chunks indexed: {store.count(COURSE_ID)}  k={args.k}\n")
    print(f"{'mode':<14} {'Hit@k':>7} {'MRR':>6} {'ms/q':>6}")

    modes = MODES if args.mode == "all" else (args.mode,)
    failed: list[str] = []
    for mode in modes:
        report = evaluate(make_retriever(mode, store, embedder, reranker), items, k=args.k)
        print(
            f"{mode:<14} {report.hit_rate:>7.1%} {report.mrr:>6.3f} {report.mean_latency_ms:>6.1f}"
        )
        if args.show_misses:
            for miss in report.misses:
                print(f"    miss {miss}: {by_id[miss].question}")
        if args.min_hit is not None and report.hit_rate < args.min_hit:
            failed.append(mode)

    if failed:
        raise SystemExit(f"\nFAIL: Hit@{args.k} below {args.min_hit:.0%} for: {', '.join(failed)}")


if __name__ == "__main__":
    main()
