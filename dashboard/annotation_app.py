"""Local Streamlit screen for reviewing PharmaIntel NER gold annotations."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from pharmaintel.evaluation.annotation import find_exact_occurrences, make_annotation_entity

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANNOTATION_FILE = PROJECT_ROOT / "data/annotated/ner_annotation_sample.csv"


def _load_entities(value: str) -> list[dict[str, object]]:
    if not value:
        return []
    try:
        entities = json.loads(value)
    except json.JSONDecodeError:
        return []
    return entities if isinstance(entities, list) else []


def _save_row(
    path: Path,
    frame: pd.DataFrame,
    row_index: int,
    entities: list[dict[str, object]],
    status: str,
    notes: str,
) -> None:
    frame.at[row_index, "gold_entities_json"] = json.dumps(
        sorted(entities, key=lambda entity: (entity["start"], entity["end"], entity["label"])),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    frame.at[row_index, "review_status"] = status
    frame.at[row_index, "annotator_notes"] = notes
    frame.to_csv(path, index=False, encoding="utf-8-sig")


st.set_page_config(page_title="PharmaIntel Annotation Studio", page_icon="🧬", layout="wide")
st.title("PharmaIntel · NER Annotation Studio")
st.caption("Review entity spans. Candidate model predictions are hidden.")

path_text = st.sidebar.text_input("Annotation CSV", value=str(DEFAULT_ANNOTATION_FILE))
annotation_path = Path(path_text).expanduser()
if not annotation_path.exists():
    st.error(f"Annotation file not found: {annotation_path}")
    st.stop()

frame = pd.read_csv(annotation_path, encoding="utf-8-sig", keep_default_na=False)
required_columns = {
    "sample_id", "sampling_stratum", "pmid", "sentence", "title", "abstract_context",
    "gold_entities_json", "annotator_notes", "review_status",
}
if missing := required_columns - set(frame.columns):
    st.error(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    st.stop()
if frame.empty:
    st.info("This annotation file has no rows.")
    st.stop()

if "annotation_row_index" not in st.session_state:
    st.session_state.annotation_row_index = 0
st.session_state.annotation_row_index = min(
    max(0, int(st.session_state.annotation_row_index)), len(frame) - 1
)

complete_count = int((frame["review_status"] == "complete").sum())
adjudication_count = int((frame["review_status"] == "needs_adjudication").sum())
pending_count = len(frame) - complete_count - adjudication_count
st.caption(
    f"{complete_count} complete · {adjudication_count} need adjudication · {pending_count} pending · "
    "random and target-enriched strata are reported separately"
)

previous_col, status_col, next_col = st.columns([1, 3, 1])
with previous_col:
    if st.button("← Previous", disabled=st.session_state.annotation_row_index == 0):
        st.session_state.annotation_row_index -= 1
        st.rerun()
with next_col:
    if st.button(
        "Next →", disabled=st.session_state.annotation_row_index >= len(frame) - 1
    ):
        st.session_state.annotation_row_index += 1
        st.rerun()

row_index = st.session_state.annotation_row_index
row = frame.iloc[row_index]
with status_col:
    st.markdown(
        f"**{row['sample_id']}** · {row['sampling_stratum']} · PMID "
        f"[{row['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{row['pmid']}/) · "
        f"row {row_index + 1} of {len(frame)}"
    )

st.subheader(row["title"] or "Untitled PubMed record")
with st.expander("Abstract context", expanded=False):
    st.write(row["abstract_context"] or "No abstract is available for this citation.")
st.markdown("**Sentence to annotate**")
st.code(row["sentence"], language=None, wrap_lines=True)
st.caption("Offsets are zero-based, inclusive at start and exclusive at end.")

sample_id = str(row["sample_id"])
entities_key = f"entities_{sample_id}"
if entities_key not in st.session_state:
    st.session_state[entities_key] = _load_entities(row["gold_entities_json"])
entities: list[dict[str, object]] = st.session_state[entities_key]

with st.form(f"add_entity_{sample_id}", clear_on_submit=True):
    mention_col, label_col, occurrence_col, add_col = st.columns([3, 1, 1, 1])
    with mention_col:
        mention = st.text_input("Entity text exactly as it appears")
    with label_col:
        label = st.selectbox("Label", ["DRUG", "ADR"])
    occurrences = find_exact_occurrences(str(row["sentence"]), mention)
    with occurrence_col:
        occurrence = st.selectbox(
            "Occurrence",
            options=list(range(len(occurrences))) or [0],
            format_func=lambda index: f"{index + 1} ({occurrences[index][0]}:{occurrences[index][1]})"
            if occurrences
            else "No match",
        )
    with add_col:
        st.write("")
        add_clicked = st.form_submit_button("Add span", disabled=not occurrences)
    if add_clicked:
        entity = make_annotation_entity(str(row["sentence"]), mention, label, occurrence)
        if entity not in entities:
            entities.append(entity)
            st.session_state[entities_key] = entities
        st.session_state[f"no_entities_{sample_id}"] = False
        st.rerun()

if entities:
    st.markdown("**Current spans**")
    for entity_index, entity in enumerate(entities):
        remove_col, span_col = st.columns([1, 8])
        with remove_col:
            if st.button("Remove", key=f"remove_{sample_id}_{entity_index}"):
                entities.pop(entity_index)
                st.session_state[entities_key] = entities
                st.rerun()
        with span_col:
            st.write(
                f"`{entity['label']}` · **{entity['text']}** · "
                f"{entity['start']}:{entity['end']}"
            )
else:
    st.info("No spans added. Mark the sentence as reviewed with no entities if that is correct.")

no_entities_key = f"no_entities_{sample_id}"
no_entities = st.checkbox(
    "I reviewed this sentence and it contains no DRUG or ADR entities",
    value=bool(row["gold_entities_json"] == "[]" and row["review_status"] == "complete"),
    key=no_entities_key,
)
notes_key = f"annotation_notes_{sample_id}"
notes = st.text_area("Annotation notes", value=str(row["annotator_notes"]), key=notes_key)

save_col, adjudicate_col = st.columns(2)
with save_col:
    save_disabled = not entities and not no_entities
    if st.button("Save as complete", type="primary", disabled=save_disabled):
        _save_row(annotation_path, frame, row_index, entities, "complete", notes)
        st.success("Gold annotation saved.")
        st.rerun()
    if st.button("Save & next", disabled=save_disabled or row_index >= len(frame) - 1):
        _save_row(annotation_path, frame, row_index, entities, "complete", notes)
        st.session_state.annotation_row_index = row_index + 1
        st.rerun()
with adjudicate_col:
    if st.button("Save for adjudication"):
        _save_row(annotation_path, frame, row_index, entities, "needs_adjudication", notes)
        st.success("Saved for adjudication.")
        st.rerun()

st.caption("Annotations are saved to the selected CSV.")
