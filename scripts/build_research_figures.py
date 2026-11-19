"""Create reproducible, publication-friendly PNG summaries from dashboard assets."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import networkx as nx
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "dashboard/data"
OUT = ROOT / "results/figures"
OUT.mkdir(parents=True, exist_ok=True)
PALETTE = {"paper": "#FFFCF6", "wine": "#930031", "blue": "#BDE0FF", "yellow": "#FFF2A7", "orange": "#FFA500", "ink": "#24151B", "muted": "#715D65", "line": "#E6DDE0"}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    options = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for option in options:
        if Path(option).exists():
            return ImageFont.truetype(option, size)
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: str, outline: str | None = None) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1 if outline else 0)


def build_signal_chart() -> Path:
    frame = pd.read_csv(ASSETS / "transformer_case_study_signals.csv")
    frame = frame.sort_values("priority_score", ascending=True)
    width, height = 1500, 920
    image = Image.new("RGB", (width, height), PALETTE["paper"])
    draw = ImageDraw.Draw(image)
    rounded(draw, (46, 36, width - 46, height - 36), 28, "#FFFFFF", PALETTE["line"])
    draw.text((92, 74), "PHARMAINTEL  /  LITERATURE SIGNALS", font=font(22, True), fill=PALETTE["wine"])
    draw.text((92, 118), "Clozapine · blood-cell event candidates", font=font(40, True), fill=PALETTE["ink"])
    draw.text((92, 174), "Ranked by log(1 + positive unique PMIDs) × assertion consistency", font=font(21), fill=PALETTE["muted"])
    max_value = max(float(v) for v in frame["priority_score"])
    x0, x1, top, row_h = 520, width - 130, 270, 112
    for i, (_, row) in enumerate(frame.iterrows()):
        y = top + i * row_h
        term = str(row["adr"])
        score = float(row["priority_score"])
        draw.text((95, y + 13), term, font=font(28, True), fill=PALETTE["ink"])
        draw.text((95, y + 52), f"{int(row['positive_pmid_count'])} positive PMIDs  ·  {float(row['consistency']):.0%} consistency", font=font(17), fill=PALETTE["muted"])
        rounded(draw, (x0, y + 12, x1, y + 58), 17, "#F3EEF0")
        end = x0 + int((x1 - x0) * score / max_value)
        rounded(draw, (x0, y + 12, end, y + 58), 17, PALETTE["wine"] if i >= len(frame) - 2 else PALETTE["orange"] if i == len(frame) - 1 else PALETTE["blue"])
        draw.text((x1 - 78, y + 66), f"{score:.2f}", font=font(19, True), fill=PALETTE["wine"])
    note_y = top + len(frame) * row_h + 20
    draw.line((95, note_y, width - 95, note_y), fill=PALETTE["line"], width=2)
    draw.text((95, note_y + 24), "Literature triage only · not incidence, clinical risk, or causal probability", font=font(18), fill=PALETTE["muted"])
    path = OUT / "literature_signal_ranking.png"
    image.save(path, optimize=True)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">', f'<rect width="{width}" height="{height}" fill="{PALETTE["paper"]}"/>', f'<rect x="46" y="36" width="{width-92}" height="{height-72}" rx="28" fill="white" stroke="{PALETTE["line"]}"/>', f'<text x="92" y="98" font-family="sans-serif" font-size="22" font-weight="700" fill="{PALETTE["wine"]}">PHARMAINTEL / LITERATURE SIGNALS</text>', f'<text x="92" y="152" font-family="sans-serif" font-size="40" font-weight="700" fill="{PALETTE["ink"]}">Clozapine · blood-cell event candidates</text>', f'<text x="92" y="194" font-family="sans-serif" font-size="21" fill="{PALETTE["muted"]}">Ranked by log(1 + positive unique PMIDs) × assertion consistency</text>']
    for i, (_, row) in enumerate(frame.iterrows()):
        y = top + i * row_h
        score = float(row["priority_score"])
        end = x0 + int((x1 - x0) * score / max_value)
        color = PALETTE["wine"] if i >= len(frame)-2 else PALETTE["blue"]
        svg.extend([f'<text x="95" y="{y+40}" font-family="sans-serif" font-size="28" font-weight="700" fill="{PALETTE["ink"]}">{row["adr"]}</text>', f'<text x="95" y="{y+72}" font-family="sans-serif" font-size="17" fill="{PALETTE["muted"]}">{int(row["positive_pmid_count"])} positive PMIDs · {float(row["consistency"]):.0%} consistency</text>', f'<rect x="{x0}" y="{y+12}" width="{x1-x0}" height="46" rx="17" fill="#F3EEF0"/>', f'<rect x="{x0}" y="{y+12}" width="{end-x0}" height="46" rx="17" fill="{color}"/>', f'<text x="{x1-78}" y="{y+88}" font-family="sans-serif" font-size="19" font-weight="700" fill="{PALETTE["wine"]}">{score:.2f}</text>'])
    svg.append(f'<text x="95" y="{height-70}" font-family="sans-serif" font-size="18" fill="{PALETTE["muted"]}">Literature triage only · not incidence, clinical risk, or causal probability</text></svg>')
    (OUT / "literature_signal_ranking.svg").write_text("\n".join(svg), encoding="utf-8")
    return path


def build_evidence_network() -> Path:
    graph_path = ASSETS / "pharmaintel_transformer_case_graph.graphml.gz"
    with gzip.open(graph_path, "rt", encoding="utf-8") as handle:
        graph = nx.read_graphml(handle)
    drug, adr = "drug:clozapine", "adr:neutropenia"
    selected = []
    for node, attrs in graph.nodes(data=True):
        if attrs.get("node_type") != "evidence":
            continue
        neighbors = {target for _, target in graph.out_edges(node)}
        if drug in neighbors and adr in neighbors:
            selected.append(node)
            if len(selected) >= 28:
                break
    keep = {drug, adr, *selected}
    for node in selected:
        keep.update(target for _, target in graph.out_edges(node))
    sub = graph.subgraph(keep).copy()
    pos = nx.spring_layout(sub, seed=21, k=0.85, iterations=90)
    width, height, margin = 1500, 1060, 100
    image = Image.new("RGB", (width, height), PALETTE["paper"])
    draw = ImageDraw.Draw(image)
    rounded(draw, (42, 32, width - 42, height - 32), 28, "#FFFFFF", PALETTE["line"])
    draw.text((88, 72), "PHARMAINTEL  /  EVIDENCE GRAPH", font=font(22, True), fill=PALETTE["wine"])
    draw.text((88, 118), "One drug · one event · many traceable sentences", font=font(36, True), fill=PALETTE["ink"])
    draw.text((88, 170), "Edges represent extracted text evidence and publication links, not causality", font=font(20), fill=PALETTE["muted"])
    coords = {n: (margin + (width - 2 * margin) * float(p[0] - min(v[0] for v in pos.values())) / max(1e-9, max(v[0] for v in pos.values()) - min(v[0] for v in pos.values())), 260 + (height - 420) * float(p[1] - min(v[1] for v in pos.values())) / max(1e-9, max(v[1] for v in pos.values()) - min(v[1] for v in pos.values()))) for n, p in pos.items()}
    for source, target in sub.edges():
        draw.line((*coords[source], *coords[target]), fill="#D7CCD0", width=2)
    kinds = {"drug": PALETTE["wine"], "adverse_event": PALETTE["orange"], "evidence": PALETTE["blue"], "publication": "#E8DDE1"}
    for node, attrs in sub.nodes(data=True):
        x, y = coords[node]
        kind = str(attrs.get("node_type", "evidence"))
        radius = 19 if kind in {"drug", "adverse_event"} else 9 if kind == "evidence" else 6
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=kinds.get(kind, PALETTE["blue"]), outline="white", width=2)
    draw.text((95, height - 116), "DRUG", font=font(17, True), fill=PALETTE["wine"])
    draw.text((220, height - 116), "EVENT", font=font(17, True), fill="#C47C00")
    draw.text((365, height - 116), "SENTENCE EVIDENCE", font=font(17, True), fill="#4C83B2")
    draw.text((620, height - 116), "PUBMED RECORD", font=font(17, True), fill=PALETTE["muted"])
    for x, color in [(80, PALETTE["wine"]), (194, PALETTE["orange"]), (340, PALETTE["blue"]), (595, "#E8DDE1")]:
        draw.ellipse((x, height - 91, x+16, height - 75), fill=color)
    path = OUT / "clozapine_neutropenia_evidence_graph.png"
    image.save(path, optimize=True)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">', f'<rect width="{width}" height="{height}" fill="{PALETTE["paper"]}"/>', f'<rect x="42" y="32" width="{width-84}" height="{height-64}" rx="28" fill="white" stroke="{PALETTE["line"]}"/>', f'<text x="88" y="100" font-family="sans-serif" font-size="22" font-weight="700" fill="{PALETTE["wine"]}">PHARMAINTEL / EVIDENCE GRAPH</text>', f'<text x="88" y="150" font-family="sans-serif" font-size="36" font-weight="700" fill="{PALETTE["ink"]}">One drug · one event · traceable sentences</text>', f'<text x="88" y="190" font-family="sans-serif" font-size="20" fill="{PALETTE["muted"]}">Edges represent extracted text evidence and publication links, not causality</text>']
    for source, target in sub.edges():
        x0,y0=coords[source];x1,y1=coords[target]
        svg.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#D7CCD0" stroke-width="1.5"/>')
    for node,attrs in sub.nodes(data=True):
        x,y=coords[node];kind=str(attrs.get("node_type","evidence"));radius=19 if kind in {"drug","adverse_event"} else 9 if kind=="evidence" else 6
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{kinds.get(kind,PALETTE["blue"])}" stroke="white" stroke-width="2"/>')
    for x,color,label in [(80,PALETTE["wine"],"DRUG"),(194,PALETTE["orange"],"EVENT"),(340,PALETTE["blue"],"SENTENCE EVIDENCE"),(595,"#E8DDE1","PUBMED RECORD")]:
        svg.extend([f'<circle cx="{x+8}" cy="{height-83}" r="8" fill="{color}"/>',f'<text x="{x+25}" y="{height-77}" font-family="sans-serif" font-size="17" font-weight="700" fill="{PALETTE["muted"]}">{label}</text>'])
    svg.append('</svg>')
    (OUT / "clozapine_neutropenia_evidence_graph.svg").write_text("\n".join(svg), encoding="utf-8")
    return path


if __name__ == "__main__":
    for artifact in (build_signal_chart(), build_evidence_network()):
        print(artifact.relative_to(ROOT))
