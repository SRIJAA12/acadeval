"""Ingests the real (non-synthetic) sample documents in datasets/PROJECTS into
the reference corpus, using the app's own document parser, classifier and
extractor — the same pipeline a live student submission goes through — so the
new rows are genuinely comparable to what real submissions will look like.

These are real project write-ups (PDFs/DOCX/PPTX of actual student/academic
work), not the corpus's bulk machine-generated rows, so they're tagged with a
distinct Publication_Type and a REAL### id prefix to keep them identifiable.
Re-running is idempotent: existing REAL### ids are skipped.

Usage (inside the api container): python scripts/ingest_real_project_samples.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.document_parser import document_parser_service
from app.services.classifier import classifier_service
from app.services.extractor import extractor_service
from app.services.dataset_paths import resolve_dataset_dir, resolve_dataset_file

SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt"}


def _flatten(entities: dict, *categories: str) -> str:
    seen, out = set(), []
    for cat in categories:
        for name in entities.get(cat, []) or []:
            key = str(name).strip()
            if key and key.lower() not in seen:
                seen.add(key.lower())
                out.append(key)
    return ", ".join(out)


def main() -> None:
    projects_dir = resolve_dataset_dir("PROJECTS")
    corpus_path = resolve_dataset_file("corpus", "AcadEval_Corpus_MASTER.csv")
    if not projects_dir.exists():
        print(f"No PROJECTS folder found at {projects_dir}")
        return
    if not corpus_path:
        print("Could not resolve the canonical corpus CSV")
        return

    with open(corpus_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        existing_rows = list(reader)
    existing_ids = {row["Project_ID"] for row in existing_rows}

    files = sorted(p for p in projects_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTS)
    print(f"{len(files)} real sample documents found in {projects_dir}")

    new_rows = []
    next_num = 1
    for path in files:
        project_id = f"REAL{next_num:04d}"
        if project_id in existing_ids:
            next_num += 1
            continue

        try:
            parsed = document_parser_service.parse_uploaded_file(file_path=path, filename=path.name)
        except Exception as e:
            print(f"  SKIP {path.name}: parse failed ({e})")
            continue

        struct = parsed.get("parsed_structure", {}) or {}
        raw_text = parsed.get("raw_text", "") or ""
        if len(raw_text.strip()) < 200:
            print(f"  SKIP {path.name}: too little extractable text")
            continue

        title = (struct.get("title") or "").strip() or path.stem.replace("_", " ").strip()
        abstract = (struct.get("abstract") or "").strip() or raw_text[:1500].strip()

        try:
            cls = classifier_service.classify_project(title, abstract)
        except Exception as e:
            print(f"  WARN {path.name}: classification failed ({e}); using defaults")
            cls = {}
        domain = cls.get("domain") or "General CSE"
        sub_domain = cls.get("sub_domain") or "Machine Learning"

        try:
            entities = extractor_service.extract_from_full_proposal(title=title, abstract=abstract, body=raw_text)
        except Exception as e:
            print(f"  SKIP {path.name}: extraction failed ({e})")
            continue

        row = {k: "" for k in fieldnames}
        row.update({
            "Project_ID": project_id,
            "Title": title,
            "Abstract": abstract[:2000],
            "Domain": domain,
            "Sub_Domain": sub_domain,
            "Keywords": _flatten(entities, "applications"),
            "Technologies": _flatten(entities, "technologies"),
            "Algorithms": _flatten(entities, "algorithms"),
            "Dataset_Used": _flatten(entities, "datasets"),
            "Programming_Languages": "",
            "Frameworks": _flatten(entities, "frameworks"),
            "Tools": _flatten(entities, "libraries"),
            "Hardware": _flatten(entities, "hardware"),
            "Source": path.name,
            "Publication_Type": "Real Student/Academic Project Sample",
            "Notes": "Parsed directly from an actual submitted document in datasets/PROJECTS "
                     "via the app's own document parser/classifier/extractor pipeline — not "
                     "machine-generated like the bulk corpus rows.",
        })
        new_rows.append(row)
        print(f"  ok   {path.name} -> {project_id} | {title[:60]!r} | {domain} / {sub_domain}")
        next_num += 1

    if not new_rows:
        print("Nothing new to add.")
        return

    with open(corpus_path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerows(new_rows)

    print(f"\nAppended {len(new_rows)} real project rows to {corpus_path}")


if __name__ == "__main__":
    main()
