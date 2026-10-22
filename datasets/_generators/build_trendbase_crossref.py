"""
Build AcadEval_TrendBase using CrossRef API (rate-limit friendly).
CrossRef allows ~50 req/s with polite pool (email in headers).
Uses /works endpoint with keyword+year filters.
Output: datasets/AcadEval_TrendBase.csv
"""

import csv, time, os, json, random, datetime
import urllib.request, urllib.parse, urllib.error

OUTPUT = r"D:\acadeval-1\datasets\AcadEval_TrendBase.csv"

COLUMNS = [
    "topic_id","domain","sub_domain","topic_name","year",
    "paper_count","citation_count","influential_count",
    "top_venues","trending_score","source","fetched_at"
]

# Email for CrossRef polite pool (gets higher rate limits)
CONTACT_EMAIL = "acadeval.research@example.com"

TOPIC_MAP = [
    ("Artificial Intelligence","Deep Learning","deep learning"),
    ("Artificial Intelligence","Generative AI","large language models"),
    ("Natural Language Processing","NLP","natural language processing"),
    ("Natural Language Processing","Large Language Models","transformer BERT GPT"),
    ("Computer Vision","Image Recognition","image recognition convolutional neural network"),
    ("Computer Vision","Object Detection","object detection YOLO"),
    ("Machine Learning","Reinforcement Learning","reinforcement learning"),
    ("Machine Learning","Federated Learning","federated learning"),
    ("Cybersecurity","Malware Detection","malware detection intrusion detection"),
    ("Cybersecurity","Network Security","network intrusion detection cybersecurity"),
    ("Blockchain & Web3","Blockchain","blockchain smart contracts"),
    ("Healthcare & Medical Technology","Medical Imaging","medical image classification"),
    ("Healthcare & Medical Technology","Drug Discovery","drug discovery machine learning"),
    ("Healthcare & Medical Technology","Clinical NLP","clinical natural language processing"),
    ("Bioinformatics","Genomics ML","genomics deep learning"),
    ("Agriculture & AgriTech","Precision Agriculture","precision agriculture crop disease"),
    ("Finance & FinTech","Financial ML","financial machine learning fraud detection"),
    ("Law & Legal Tech","Legal NLP","legal text analysis NLP"),
    ("Education Technology","Learning Analytics","learning analytics intelligent tutoring"),
    ("Smart Cities","Urban Computing","smart city IoT traffic management"),
    ("Energy & Power Systems","Renewable Energy","solar wind energy prediction machine learning"),
    ("Environmental Science","Climate ML","climate change machine learning"),
    ("Automotive Engineering","Autonomous Driving","autonomous driving self-driving"),
    ("Robotics","Robot Learning","robot learning manipulation"),
    ("Manufacturing & Industry 4.0","Industry 4.0","predictive maintenance Industry 4.0"),
    ("Quantum Computing","Quantum ML","quantum computing machine learning"),
    ("GIS & Remote Sensing","Remote Sensing","remote sensing satellite deep learning"),
    ("Speech & Audio Processing","Speech Recognition","speech recognition synthesis"),
    ("AR/VR & Metaverse","XR Technology","augmented reality virtual reality"),
    ("Internet of Things","IoT ML","internet of things anomaly detection"),
    ("Databases & Big Data","Big Data","big data processing analytics"),
    ("DevOps & Cloud Native","Cloud Native","cloud computing microservices"),
    ("Social Media Analytics","Social Media AI","social media sentiment analysis"),
    ("Fashion & Textile Technology","Fashion AI","fashion recommendation virtual try-on"),
    ("Food Science & Nutrition","Food AI","food safety machine learning"),
    ("Mental Health & Psychology Technology","Mental Health AI","mental health depression NLP"),
    ("Architecture & Construction Technology","Construction AI","building information modeling BIM"),
    ("Journalism & Media Technology","Media AI","fake news detection deepfake"),
    ("Sports Analytics","Sports AI","sports analytics performance prediction"),
    ("Marine & Ocean Engineering","Ocean AI","ocean monitoring underwater robotics"),
    ("Disaster Management","Disaster AI","disaster prediction early warning"),
    ("Defense & Security","Defense AI","military surveillance AI"),
    ("Digital Forensics","Forensics AI","digital forensics malware analysis"),
]

CROSSREF_BASE = "https://api.crossref.org/works"


def fetch_crossref(query: str, year: int) -> dict:
    """Fetch paper count from CrossRef for query+year."""
    params = {
        "query": query,
        "filter": f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31",
        "rows": "0",  # We only want the count
        "mailto": CONTACT_EMAIL,
    }
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"{CROSSREF_BASE}?{qs}"
    
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": f"AcadEval-Research/1.0 (academic, non-commercial; mailto:{CONTACT_EMAIL})"
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        total = data.get("message", {}).get("total-results", 0)
        return {"paper_count": total, "citation_count": 0, "influential_count": 0, 
                "top_venues": "", "ok": True}
    except Exception as e:
        print(f"    Error {year}: {e}")
        return {"paper_count": 0, "citation_count": 0, "influential_count": 0, 
                "top_venues": "", "ok": False}


def trending_score(counts):
    if len(counts) < 6:
        return 0.0
    recent = sum(counts[-3:]) / 3
    older = sum(counts[-6:-3]) / 3
    if older == 0:
        return 1.0 if recent > 0 else 0.0
    return round((recent - older) / older, 4)


def main():
    rows = []
    years = list(range(2015, 2026))
    now = datetime.datetime.utcnow().isoformat()
    
    print(f"Building TrendBase using CrossRef API ({len(TOPIC_MAP)} topics x {len(years)} years)")
    
    for tid, (domain, sub_domain, query) in enumerate(TOPIC_MAP, start=1):
        topic_name = " ".join(query.split()[:3])
        print(f"\n[{tid}/{len(TOPIC_MAP)}] {domain} — {sub_domain}")
        
        year_counts = []
        year_rows = []
        
        for year in years:
            stats = fetch_crossref(query, year)
            year_counts.append(stats["paper_count"])
            year_rows.append({
                "topic_id": f"T{tid:04d}",
                "domain": domain,
                "sub_domain": sub_domain,
                "topic_name": topic_name,
                "year": year,
                "paper_count": stats["paper_count"],
                "citation_count": stats["citation_count"],
                "influential_count": stats["influential_count"],
                "top_venues": stats["top_venues"],
                "trending_score": 0.0,
                "source": "CrossRef API",
                "fetched_at": now,
            })
            
            status = "ok" if stats["ok"] else "ERR"
            print(f"  {year}: {stats['paper_count']:>8,} papers  [{status}]")
            
            # Polite delay: CrossRef recommends ~1 req/s for polite pool
            time.sleep(random.uniform(1.0, 2.0))
        
        ts = trending_score(year_counts)
        for row in year_rows:
            row["trending_score"] = ts
        rows.extend(year_rows)
        
        # Short break between topics
        time.sleep(random.uniform(2.0, 4.0))
    
    print(f"\nWriting {len(rows)} rows to {OUTPUT}")
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    
    # Summary
    print("\nTop trending topics:")
    import csv as csv2
    with open(OUTPUT, "r", encoding="utf-8") as f:
        all_rows = list(csv2.DictReader(f))
    seen = {}
    for r in all_rows:
        k = r["topic_id"]
        if k not in seen or int(r["year"]) == 2024:
            seen[k] = r
    by_trend = sorted(seen.values(), key=lambda x: float(x["trending_score"]), reverse=True)
    for r in by_trend[:10]:
        print(f"  {r['domain']}/{r['sub_domain']}: trending={r['trending_score']}")
    
    print(f"\nDone! AcadEval_TrendBase.csv written with {len(rows)} rows.")


if __name__ == "__main__":
    main()
