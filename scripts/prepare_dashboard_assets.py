"""Package reproducible, precomputed dashboard outputs for lightweight hosting."""

from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "dashboard/data"
INPUTS = {
    "evidence": ROOT / "data/processed/pubmed/transformer_case_study_evidence.csv",
    "graph": ROOT / "results/pharmaintel_transformer_case_graph.graphml",
    "summary": ROOT / "results/transformer_corpus_summary.json",
    "signals": ROOT / "results/transformer_case_study_signals.csv",
}


def _gzip_file(source: Path, destination: Path) -> None:
    with (
        source.open("rb") as src,
        destination.open("wb") as dst,
        gzip.GzipFile(fileobj=dst, mode="wb", filename="", mtime=0) as compressed,
    ):
        shutil.copyfileobj(src, compressed)


def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Generate corpus outputs first; missing: " + ", ".join(missing))
    ASSETS.mkdir(parents=True, exist_ok=True)
    _gzip_file(INPUTS["evidence"], ASSETS / "transformer_case_study_evidence.csv.gz")
    _gzip_file(INPUTS["graph"], ASSETS / "pharmaintel_transformer_case_graph.graphml.gz")
    shutil.copyfile(INPUTS["summary"], ASSETS / "transformer_corpus_summary.json")
    shutil.copyfile(INPUTS["signals"], ASSETS / "transformer_case_study_signals.csv")
    manifest = {
        "generated_by": "scripts/prepare_dashboard_assets.py",
        "model_revision": json.loads(INPUTS["summary"].read_text(encoding="utf-8"))["model"][
            "model_revision"
        ],
        "source_files": {name: str(path.relative_to(ROOT)) for name, path in INPUTS.items()},
        "purpose": "Precomputed public-literature outputs for the hosted Streamlit results explorer; no model weights or API credentials are included.",
    }
    (ASSETS / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({path.name: path.stat().st_size for path in ASSETS.iterdir()}, indent=2))


if __name__ == "__main__":
    main()
