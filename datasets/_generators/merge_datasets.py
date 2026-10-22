"""
AcadEval Comprehensive Dataset Merger & Deduplicator
===================================================
Combines all records from `datasets/new_dataset` and existing datasets,
removes duplicate entries, cleans titles and synthetic bracketed IDs,
standardizes schemas and re-assigns sequential IDs.
"""

import os
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ──────────────────────────────────────────────────────────────────────────────
# String & Normalization Helpers
# ──────────────────────────────────────────────────────────────────────────────

def clean_title_text(t: str) -> str:
    """Removes trailing [ID] or (ID) tags from titles."""
    if not t:
        return ""
    t = re.sub(r"\s*\[[A-Za-z0-9_-]+\]\s*$", "", t)
    t = re.sub(r"\s*\([A-Za-z0-9_-]+\)\s*$", "", t)
    return t.strip()

def normalize_for_key(s: str) -> str:
    """Lowercase, strip accents, punctuation and excess whitespace for comparison."""
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def clean_abstract_text(a: str) -> str:
    """Removes trailing [ID: ...] tags from abstracts."""
    if not a:
        return ""
    a = re.sub(r"\s*\[ID:\s*[A-Za-z0-9_-]+\]\s*$", "", a)
    return a.strip()

DOMAIN_NORM = {
    "AI": "Artificial Intelligence",
    "Artificial Intelligence": "Artificial Intelligence",
    "NLP": "Natural Language Processing",
    "Natural Language Processing": "Natural Language Processing",
    "IoT": "Internet of Things",
    "Internet of Things": "Internet of Things",
    "Cyber Security": "Cybersecurity",
    "Cybersecurity": "Cybersecurity",
    "Digital Security": "Cybersecurity",
    "Blockchain": "Blockchain & Web3",
    "Blockchain & Web3": "Blockchain & Web3",
    "Computer Science": "Computer Science & Engineering",
    "Computer Science & Engineering": "Computer Science & Engineering",
    "Computer Vision": "Computer Vision",
    "Machine Learning": "Machine Learning",
    "Data Science": "Data Science",
    "Data Engineering": "Data Science",
    "Web/Mobile Application": "Web & Mobile Development",
    "Web & Mobile Development": "Web & Mobile Development",
    "Software Engineering": "Software Engineering",
    "Cloud Computing": "Cloud Computing",
    "DevOps & Cloud Native": "DevOps & Cloud Native",
    "Databases & Big Data": "Databases & Big Data",
    "Networking": "Networking",
    "Operating Systems & Systems Programming": "Operating Systems & Systems Programming",
    "Scientific Computing": "Scientific Computing",
    "Embedded Systems": "Embedded Systems",
    "Smart Systems": "Smart Systems",
    "Geospatial Computing": "GIS & Remote Sensing",
    "GIS & Remote Sensing": "GIS & Remote Sensing",
    "Robotics": "Robotics",
    "Healthcare": "Healthcare & Medical Technology",
    "Healthcare & Medical Technology": "Healthcare & Medical Technology",
    "Bioinformatics": "Bioinformatics",
    "Biotechnology": "Biotechnology",
    "Agriculture": "Agriculture & AgriTech",
    "Agriculture & AgriTech": "Agriculture & AgriTech",
    "Education": "Education Technology",
    "Education Technology": "Education Technology",
    "Finance & FinTech": "Finance & FinTech",
    "Law & Legal Tech": "Law & Legal Tech",
    "Supply Chain & Logistics": "Supply Chain & Logistics",
    "Manufacturing / Industry 4.0": "Manufacturing & Industry 4.0",
    "Manufacturing & Industry 4.0": "Manufacturing & Industry 4.0",
    "Energy & Power Systems": "Energy & Power Systems",
    "Environmental Science": "Environmental Science",
    "Climate & Weather": "Climate & Weather",
    "Quantum Computing": "Quantum Computing",
    "Aerospace & Aviation": "Aerospace & Aviation",
    "Automotive Engineering": "Automotive Engineering",
    "Smart Cities": "Smart Cities",
    "Smart Governance / E-Governance": "Smart Governance & E-Governance",
    "Smart Governance & E-Governance": "Smart Governance & E-Governance",
    "Defense & Security": "Defense & Security",
    "Digital Forensics": "Digital Forensics",
    "Disaster Management": "Disaster Management",
    "Marine & Ocean Engineering": "Marine & Ocean Engineering",
    "Chemistry & Material Science": "Chemistry & Material Science",
    "Physics": "Physics",
    "Mathematics": "Mathematics",
    "Human Resources": "Human Resources Technology",
    "Human Resources Technology": "Human Resources Technology",
    "Marketing Analytics": "Marketing Analytics",
    "Social Media Analytics": "Social Media Analytics",
    "Multimedia & Entertainment": "Multimedia & Entertainment",
    "AR / VR / Metaverse": "AR/VR & Metaverse",
    "AR/VR & Metaverse": "AR/VR & Metaverse",
    "Gaming": "Gaming & Game Development",
    "Gaming & Game Development": "Gaming & Game Development",
    "Speech & Audio Processing": "Speech & Audio Processing",
    "Tourism & Hospitality": "Tourism & Hospitality",
    "Sports Analytics": "Sports Analytics",
    "E-Commerce": "E-Commerce & Retail Tech",
    "E-Commerce & Retail Tech": "E-Commerce & Retail Tech",
}

def norm_domain(d: str) -> str:
    d = d.strip()
    return DOMAIN_NORM.get(d, d)

# ──────────────────────────────────────────────────────────────────────────────
# 1. AcadEval_Corpus Merge
# ──────────────────────────────────────────────────────────────────────────────
CORPUS_COLUMNS = [
    "Project_ID", "Title", "Abstract", "Domain", "Sub_Domain", "Keywords",
    "Objectives", "Problem_Statement", "Methodology", "Modules",
    "Technologies", "Algorithms", "Dataset_Used", "Programming_Languages",
    "Frameworks", "Tools", "Hardware", "Expected_Output",
    "GitHub_Link", "Paper_Link", "Authors", "Institution",
    "Year", "Source", "Publication_Type", "Faculty_Label", "Notes"
]

def merge_corpus():
    print("\n" + "="*70)
    print("1. MERGING ACADEVAL CORPUS")
    print("="*70)
    
    source_files = [
        BASE_DIR / "AcadEval_Corpus_MASTER.csv",
        BASE_DIR / "corpus" / "new_AcadEval_Corpus.csv",
        BASE_DIR / "new_dataset" / "new_AcadEval_Corpus.csv.xls",
        BASE_DIR / "new_dataset" / "AcadEval_Corpus.csv.xls",
        BASE_DIR / "new_dataset" / "AcadEval_Corpus_250_Projects.csv.xls",
        BASE_DIR / "corpus" / "AcadEval_Corpus.csv",
        BASE_DIR / "corpus" / "AcadEval_Corpus_250_Projects.csv",
    ]
    
    seen_keys = set()
    merged_rows = []
    
    for fpath in source_files:
        if not fpath.exists():
            print(f"  [SKIP] Not found: {fpath}")
            continue
        
        file_count = 0
        added_count = 0
        with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
            reader = csv.reader(fp)
            raw_headers = next(reader, None)
            if not raw_headers:
                continue
            headers = [h.strip().lstrip("\ufeff") for h in raw_headers]
            
            for row in reader:
                if not row or not any(row):
                    continue
                file_count += 1
                row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                
                raw_title = row_dict.get("Title", "").strip()
                cleaned_title = clean_title_text(raw_title)
                norm_key = normalize_for_key(cleaned_title)
                
                if not norm_key or norm_key in seen_keys:
                    continue
                
                seen_keys.add(norm_key)
                
                # Normalize domain and clean fields
                row_dict["Title"] = cleaned_title
                row_dict["Abstract"] = clean_abstract_text(row_dict.get("Abstract", ""))
                row_dict["Domain"] = norm_domain(row_dict.get("Domain", ""))
                
                # Fill missing columns
                clean_row = {col: row_dict.get(col, "") for col in CORPUS_COLUMNS}
                merged_rows.append(clean_row)
                added_count += 1
                
        print(f"  Processed {fpath.name}: {file_count} total rows, {added_count} unique added (cumulative: {len(merged_rows)})")

    # Re-assign sequential IDs
    for idx, row in enumerate(merged_rows, start=1):
        row["Project_ID"] = f"P{idx:06d}"
        
    out_master = BASE_DIR / "AcadEval_Corpus_MASTER.csv"
    with open(out_master, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=CORPUS_COLUMNS)
        writer.writeheader()
        writer.writerows(merged_rows)
    print(f"  -> Successfully written to {out_master} ({len(merged_rows)} records)")
    
    # Also update corpus/new_AcadEval_Corpus.csv for compatibility
    out_corpus = BASE_DIR / "corpus" / "new_AcadEval_Corpus.csv"
    if out_corpus.parent.exists():
        with open(out_corpus, "w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=CORPUS_COLUMNS)
            writer.writeheader()
            writer.writerows(merged_rows)
        print(f"  -> Synchronized {out_corpus}")

# ──────────────────────────────────────────────────────────────────────────────
# 2. AcadEval_DomainTaxonomy Merge
# ──────────────────────────────────────────────────────────────────────────────
TAXONOMY_COLUMNS = [
    "Taxonomy_ID", "Domain", "Sub_Domain", "Topic", "Parent_Topic", "Description",
    "Common_Keywords", "Related_Keywords", "Technologies", "Algorithms",
    "Programming_Languages", "Frameworks", "Libraries", "Hardware",
    "Typical_Datasets", "Research_Areas", "Application_Areas", "Difficulty_Level",
    "Industry", "Emerging_Topic", "Trend_Level", "Related_Domains", "Source", "Notes"
]

def merge_taxonomy():
    print("\n" + "="*70)
    print("2. MERGING ACADEVAL DOMAIN TAXONOMY")
    print("="*70)
    
    source_files = [
        BASE_DIR / "AcadEval_DomainTaxonomy.csv",
        BASE_DIR / "taxonomy" / "AcadEval_DomainTaxonomy.csv",
        BASE_DIR / "new_dataset" / "AcadEval_DomainTaxonomy.csv.xls",
    ]
    
    seen_keys = set()
    merged_rows = []
    
    for fpath in source_files:
        if not fpath.exists():
            print(f"  [SKIP] Not found: {fpath}")
            continue
            
        file_count = 0
        added_count = 0
        with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
            reader = csv.reader(fp)
            raw_headers = next(reader, None)
            if not raw_headers:
                continue
            headers = [h.strip().lstrip("\ufeff") for h in raw_headers]
            
            for row in reader:
                if not row or not any(row):
                    continue
                file_count += 1
                row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                
                domain = norm_domain(row_dict.get("Domain", ""))
                sub_domain = row_dict.get("Sub_Domain", "").strip()
                topic = clean_title_text(row_dict.get("Topic", ""))
                
                key = (normalize_for_key(domain), normalize_for_key(sub_domain), normalize_for_key(topic))
                if not topic or key in seen_keys:
                    continue
                    
                seen_keys.add(key)
                row_dict["Domain"] = domain
                row_dict["Topic"] = topic
                
                clean_row = {col: row_dict.get(col, "") for col in TAXONOMY_COLUMNS}
                merged_rows.append(clean_row)
                added_count += 1
                
        print(f"  Processed {fpath.name}: {file_count} total rows, {added_count} unique added (cumulative: {len(merged_rows)})")
        
    # Re-assign sequential Taxonomy IDs
    for idx, row in enumerate(merged_rows, start=1):
        row["Taxonomy_ID"] = f"AE-{idx:05d}"
        
    out_root = BASE_DIR / "AcadEval_DomainTaxonomy.csv"
    with open(out_root, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=TAXONOMY_COLUMNS)
        writer.writeheader()
        writer.writerows(merged_rows)
    print(f"  -> Successfully written to {out_root} ({len(merged_rows)} records)")
    
    out_tax = BASE_DIR / "taxonomy" / "AcadEval_DomainTaxonomy.csv"
    if out_tax.parent.exists():
        with open(out_tax, "w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=TAXONOMY_COLUMNS)
            writer.writeheader()
            writer.writerows(merged_rows)
        print(f"  -> Synchronized {out_tax}")

# ──────────────────────────────────────────────────────────────────────────────
# 3. AcadEval_FeatureKnowledgeBase (8-column standard) Merge
# ──────────────────────────────────────────────────────────────────────────────
FEATURE_8_COLUMNS = [
    "feature_id", "name", "category", "aliases", "first_seen_year",
    "description", "difficulty", "default_rarity"
]

def merge_feature_kb_8col():
    print("\n" + "="*70)
    print("3. MERGING ACADEVAL FEATURE KNOWLEDGE BASE (8-COL SCHEMA)")
    print("="*70)
    
    source_files = [
        BASE_DIR / "AcadEval_FeatureKnowledgeBase.csv",
        BASE_DIR / "feature_kb" / "AcadEval_FeatureKnowledgeBase.csv",
        BASE_DIR / "new_dataset" / "AcadEval_FeatureKnowledgeBase.csv.xls",
    ]
    
    seen_keys = set()
    merged_rows = []
    
    for fpath in source_files:
        if not fpath.exists():
            print(f"  [SKIP] Not found: {fpath}")
            continue
            
        file_count = 0
        added_count = 0
        with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
            reader = csv.reader(fp)
            raw_headers = next(reader, None)
            if not raw_headers:
                continue
            headers = [h.strip().lstrip("\ufeff") for h in raw_headers]
            
            for row in reader:
                if not row or not any(row):
                    continue
                file_count += 1
                row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                
                name = clean_title_text(row_dict.get("name", ""))
                norm_key = normalize_for_key(name)
                
                if not norm_key or norm_key in seen_keys:
                    continue
                    
                seen_keys.add(norm_key)
                row_dict["name"] = name
                
                # Handle default_weight vs default_rarity
                if "default_rarity" not in row_dict and "default_weight" in row_dict:
                    row_dict["default_rarity"] = row_dict["default_weight"]
                if not row_dict.get("default_rarity"):
                    row_dict["default_rarity"] = "0.5"
                    
                clean_row = {col: row_dict.get(col, "") for col in FEATURE_8_COLUMNS}
                merged_rows.append(clean_row)
                added_count += 1
                
        print(f"  Processed {fpath.name}: {file_count} total rows, {added_count} unique added (cumulative: {len(merged_rows)})")
        
    for idx, row in enumerate(merged_rows, start=1):
        row["feature_id"] = f"FEAT-{idx:05d}"
        
    out_root = BASE_DIR / "AcadEval_FeatureKnowledgeBase.csv"
    with open(out_root, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=FEATURE_8_COLUMNS)
        writer.writeheader()
        writer.writerows(merged_rows)
    print(f"  -> Successfully written to {out_root} ({len(merged_rows)} records)")
    
    out_kb = BASE_DIR / "feature_kb" / "AcadEval_FeatureKnowledgeBase.csv"
    if out_kb.parent.exists():
        with open(out_kb, "w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=FEATURE_8_COLUMNS)
            writer.writeheader()
            writer.writerows(merged_rows)
        print(f"  -> Synchronized {out_kb}")
        
    # Also regenerate JSON representations
    json_list = []
    for r in merged_rows:
        raw_aliases = r.get("aliases", "")
        if isinstance(raw_aliases, str):
            aliases = [a.strip() for a in raw_aliases.split(",") if a.strip()]
        else:
            aliases = list(raw_aliases)
            
        try:
            year = int(float(r.get("first_seen_year", 2020)))
        except (ValueError, TypeError):
            year = 2020
            
        try:
            rarity = float(r.get("default_rarity", 0.5))
        except (ValueError, TypeError):
            rarity = 0.5
            
        json_list.append({
            "feature_id": r["feature_id"],
            "name": r["name"],
            "category": r.get("category", "Technology"),
            "aliases": aliases,
            "first_seen_year": year,
            "description": r.get("description", ""),
            "difficulty": r.get("difficulty", "Intermediate"),
            "default_rarity": rarity
        })
        
    json_root = BASE_DIR / "AcadEval_FeatureKnowledgeBase.json"
    with open(json_root, "w", encoding="utf-8") as fp:
        json.dump(json_list, fp, indent=2)
    print(f"  -> Generated JSON at {json_root}")
    
    json_kb = BASE_DIR / "feature_kb" / "AcadEval_FeatureKnowledgeBase.json"
    if json_kb.parent.exists():
        with open(json_kb, "w", encoding="utf-8") as fp:
            json.dump(json_list, fp, indent=2)
        print(f"  -> Synchronized {json_kb}")

# ──────────────────────────────────────────────────────────────────────────────
# 4. AcadEval_FeatureKnowledgeBase (10-column variant) Merge
# ──────────────────────────────────────────────────────────────────────────────
FEATURE_10_COLUMNS = [
    "id", "feature_name", "category", "domain", "technology", "difficulty",
    "innovation_score", "description", "typical_use_case", "source"
]

def merge_feature_kb_10col():
    print("\n" + "="*70)
    print("4. MERGING ACADEVAL FEATURE KNOWLEDGE BASE (10-COL CORPUS SCHEMA)")
    print("="*70)
    
    source_files = [
        BASE_DIR / "corpus" / "AcadEval_FeatureKnowledgeBase.csv",
        BASE_DIR / "new_dataset" / "AcadEval_FeatureKnowledgeBase.csv (1).xls",
    ]
    
    seen_keys = set()
    merged_rows = []
    
    for fpath in source_files:
        if not fpath.exists():
            print(f"  [SKIP] Not found: {fpath}")
            continue
            
        file_count = 0
        added_count = 0
        with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
            reader = csv.reader(fp)
            raw_headers = next(reader, None)
            if not raw_headers:
                continue
            headers = [h.strip().lstrip("\ufeff") for h in raw_headers]
            
            for row in reader:
                if not row or not any(row):
                    continue
                file_count += 1
                row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                
                fname = clean_title_text(row_dict.get("feature_name", ""))
                norm_key = normalize_for_key(fname)
                
                if not norm_key or norm_key in seen_keys:
                    continue
                    
                seen_keys.add(norm_key)
                row_dict["feature_name"] = fname
                
                clean_row = {col: row_dict.get(col, "") for col in FEATURE_10_COLUMNS}
                merged_rows.append(clean_row)
                added_count += 1
                
        print(f"  Processed {fpath.name}: {file_count} total rows, {added_count} unique added (cumulative: {len(merged_rows)})")
        
    for idx, row in enumerate(merged_rows, start=1):
        row["id"] = f"KB{idx:05d}"
        
    out_corpus = BASE_DIR / "corpus" / "AcadEval_FeatureKnowledgeBase.csv"
    if out_corpus.parent.exists():
        with open(out_corpus, "w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=FEATURE_10_COLUMNS)
            writer.writeheader()
            writer.writerows(merged_rows)
        print(f"  -> Successfully written to {out_corpus} ({len(merged_rows)} records)")

# ──────────────────────────────────────────────────────────────────────────────
# 5. AcadEval_SimBench Merge
# ──────────────────────────────────────────────────────────────────────────────
SIMBENCH_COLUMNS = [
    "Pair_ID", "Project_A_ID", "Project_B_ID", "Project_A_Title", "Project_B_Title",
    "Project_A_Abstract", "Project_B_Abstract", "Project_A_Features", "Project_B_Features",
    "Project_A_Keywords", "Project_B_Keywords", "SBERT_Similarity", "TFIDF_Similarity",
    "Cosine_Similarity", "Faculty_Label", "AI_Label", "Similarity_Category",
    "Reviewer_Name", "Review_Date", "Comments"
]

def merge_simbench():
    print("\n" + "="*70)
    print("5. MERGING ACADEVAL SIMBENCH")
    print("="*70)
    
    source_files = [
        BASE_DIR / "AcadEval_SimBench.csv",
        BASE_DIR / "corpus" / "AcadEval_SimBench.csv",
        BASE_DIR / "new_dataset" / "AcadEval_SimBench.csv.xls",
    ]
    
    seen_keys = set()
    merged_rows = []
    
    for fpath in source_files:
        if not fpath.exists():
            print(f"  [SKIP] Not found: {fpath}")
            continue
            
        file_count = 0
        added_count = 0
        with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
            reader = csv.reader(fp)
            raw_headers = next(reader, None)
            if not raw_headers:
                continue
            headers = [h.strip().lstrip("\ufeff") for h in raw_headers]
            
            for row in reader:
                if not row or not any(row):
                    continue
                file_count += 1
                row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                
                title_a = clean_title_text(row_dict.get("Project_A_Title", ""))
                title_b = clean_title_text(row_dict.get("Project_B_Title", ""))
                
                norm_a = normalize_for_key(title_a)
                norm_b = normalize_for_key(title_b)
                
                if not norm_a or not norm_b:
                    continue
                    
                pair_key = tuple(sorted([norm_a, norm_b]))
                if pair_key in seen_keys:
                    continue
                    
                seen_keys.add(pair_key)
                row_dict["Project_A_Title"] = title_a
                row_dict["Project_B_Title"] = title_b
                row_dict["Project_A_Abstract"] = clean_abstract_text(row_dict.get("Project_A_Abstract", ""))
                row_dict["Project_B_Abstract"] = clean_abstract_text(row_dict.get("Project_B_Abstract", ""))
                
                clean_row = {col: row_dict.get(col, "") for col in SIMBENCH_COLUMNS}
                merged_rows.append(clean_row)
                added_count += 1
                
        print(f"  Processed {fpath.name}: {file_count} total rows, {added_count} unique added (cumulative: {len(merged_rows)})")
        
    for idx, row in enumerate(merged_rows, start=1):
        row["Pair_ID"] = f"SB{idx:05d}"
        
    out_root = BASE_DIR / "AcadEval_SimBench.csv"
    with open(out_root, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=SIMBENCH_COLUMNS)
        writer.writeheader()
        writer.writerows(merged_rows)
    print(f"  -> Successfully written to {out_root} ({len(merged_rows)} records)")
    
    out_corpus = BASE_DIR / "corpus" / "AcadEval_SimBench.csv"
    if out_corpus.parent.exists():
        with open(out_corpus, "w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=SIMBENCH_COLUMNS)
            writer.writeheader()
            writer.writerows(merged_rows)
        print(f"  -> Synchronized {out_corpus}")

# ──────────────────────────────────────────────────────────────────────────────
# Main Execution
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting AcadEval dataset consolidation...")
    merge_corpus()
    merge_taxonomy()
    merge_feature_kb_8col()
    merge_feature_kb_10col()
    merge_simbench()
    print("\n" + "="*70)
    print("ALL DATASETS SUCCESSFULLY CONSOLIDATED AND DEDUPLICATED!")
    print("="*70)
