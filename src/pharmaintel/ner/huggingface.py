"""Hugging Face token-classification inference with raw and mapped labels retained."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

MODEL_CANDIDATES = (
    "Glasgow-AI4BioMed/bioner_bc5cdr",
    "d4data/biomedical-ner-all",
)


def map_candidate_label(model_id: str, source_label: str) -> str | None:
    """Map a checkpoint's broad label into the benchmark's DRUG/ADR target labels."""
    label = source_label.removeprefix("B-").removeprefix("I-").strip()
    if model_id == "Glasgow-AI4BioMed/bioner_bc5cdr":
        return {"Chemical": "DRUG", "Disease": "ADR"}.get(label)
    if model_id == "d4data/biomedical-ner-all":
        if label == "Medication":
            return "DRUG"
        if label in {"Disease_disorder", "Sign_symptom", "Clinical_event"}:
            return "ADR"
    return None


def predict_entities(
    texts: Sequence[str],
    model_id: str,
    batch_size: int = 8,
    device: int = -1,
    revision: str | None = None,
    local_files_only: bool = False,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[list[list[dict[str, Any]]], dict[str, str]]:
    """Run HF token classification and return per-text spans plus model provenance.

    Scores are model outputs, not probabilities that a span is true or causal. Raw
    checkpoint labels are retained because label-to-ADR mappings are intentionally broad.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")
    if not texts:
        return [], {"model_id": model_id, "model_revision": revision or "not-loaded"}

    try:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
    except ImportError as exc:
        raise RuntimeError(
            "Install the NLP extras and CPU/GPU PyTorch before model inference."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(
        model_id, revision=revision, use_fast=True, local_files_only=local_files_only
    )
    model = AutoModelForTokenClassification.from_pretrained(
        model_id, revision=revision, local_files_only=local_files_only
    )
    model.eval()
    pipe = pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",
        device=device,
    )

    outputs: list[list[dict[str, Any]]] = []
    stride = 64 if tokenizer.is_fast else 0
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            batch_texts = list(texts[start : start + batch_size])
            batch_outputs = pipe(batch_texts, batch_size=batch_size, stride=stride)
            for text, predictions in zip(batch_texts, batch_outputs, strict=True):
                spans_by_key: dict[tuple[int, int, str], dict[str, Any]] = {}
                for prediction in predictions:
                    start_offset, end_offset = int(prediction["start"]), int(prediction["end"])
                    source_label = str(prediction["entity_group"])
                    key = (start_offset, end_offset, source_label)
                    candidate = {
                        "text": text[start_offset:end_offset],
                        "label": map_candidate_label(model_id, source_label),
                        "source_label": source_label,
                        "start": start_offset,
                        "end": end_offset,
                        "score": float(prediction["score"]),
                    }
                    if key not in spans_by_key or candidate["score"] > spans_by_key[key]["score"]:
                        spans_by_key[key] = candidate
                outputs.append(
                    sorted(spans_by_key.values(), key=lambda span: (span["start"], span["end"]))
                )
            if progress_callback is not None:
                progress_callback(min(start + len(batch_texts), len(texts)), len(texts))

    model_revision = getattr(model.config, "_commit_hash", None) or revision or "unresolved"
    provenance = {
        "model_id": model_id,
        "model_revision": str(model_revision),
        "tokenizer_class": tokenizer.__class__.__name__,
        "aggregation_strategy": "simple",
        "device": "cpu" if device < 0 else f"cuda:{device}",
        "stride": str(stride),
    }
    return outputs, provenance
