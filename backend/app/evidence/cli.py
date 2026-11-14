"""python -m app.evidence.cli ingest | add-url URL EXP | reembed | psi"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.db import init_engine, session_factory
from app.evidence import ingest as ing
from app.evidence.observations import load_psi_csvs
from app.evidence.synthetic import seed_synthetic
from app.models import EvidenceChunk
from app.rag.embeddings import get_embedder


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fireguard-ingest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest", help="download official NASA documents (needs internet)")
    p.add_argument("--ids", nargs="*", help="specific NTRS IDs")
    p.add_argument("--no-web", action="store_true")
    a = sub.add_parser("add-url", help="ingest one public *.nasa.gov URL")
    a.add_argument("url")
    a.add_argument("experiment", nargs="?", default="SFS")
    sub.add_parser("demo", help="load SYNTHETIC/DEMO passages")
    sub.add_parser("psi", help="load CSV files from data/raw/psi")
    sub.add_parser("reembed", help="recompute embeddings with the configured provider")
    args = ap.parse_args(argv)
    init_engine()
    with session_factory()() as s:
        if args.cmd == "ingest":
            print(ing.run_ingestion(s, args.ids, not args.no_web, say=print, actor="cli"))
        elif args.cmd == "add-url":
            key = "WEB-" + "".join(c if c.isalnum() else "-" for c in args.url.split("//", 1)[-1])[:55]
            print(ing.ingest_web(s, key, args.experiment, args.url, print, "cli"))
        elif args.cmd == "demo":
            print(seed_synthetic(s))
        elif args.cmd == "psi":
            print(load_psi_csvs(s))
        elif args.cmd == "reembed":
            emb = get_embedder()
            rows = list(s.scalars(select(EvidenceChunk)))
            for i in range(0, len(rows), 64):
                batch = rows[i : i + 64]
                for r, v in zip(batch, emb.embed([b.content for b in batch]), strict=True):
                    r.embedding = v
                s.commit()
            print(len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
