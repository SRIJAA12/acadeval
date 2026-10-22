"""
Build AcadEval_TrendBase using Semantic Scholar API with proper rate limiting.
Uses random jitter and exponential backoff to avoid 429 errors.
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

# Reduced to key representative topics to stay under rate limit
TOPIC_MAP = [
    ("Artificial Intelligence","Deep Learning","deep learning neural networks"),
    ("Artificial Intelligence","Generative AI","generative AI large language models LLM"),
    ("Natural Language Processing","NLP","natural language processing text classification"),
    ("Natural Language Processing","Large Language Models","BERT GPT transformer language model"),
    ("Computer Vision","Image Recognition","image recognition object detection CNN"),
    ("Computer Vision","Generative Vision","GAN image generation stable diffusion"),
    ("Machine Learning","Reinforcement Learning","reinforcement learning reward optimization"),
    ("Machine Learning","Federated Learning","federated learning privacy distributed ML"),
    ("Cybersecurity","Malware Detection","malware detection intrusion detection security"),
    ("Cybersecurity","Network Security","network security threat detection firewall"),
    ("Blockchain & Web3","Blockchain","blockchain smart contracts cryptocurrency"),
    ("Healthcare & Medical Technology","Medical Imaging","medical imaging radiology deep learning diagnosis"),
    ("Healthcare & Medical Technology","Drug Discovery","drug discovery molecular machine learning"),
    ("Healthcare & Medical Technology","Clinical NLP","clinical NLP EHR patient records"),
    ("Bioinformatics","Genomics ML","genomics sequencing bioinformatics machine learning"),
    ("Agriculture & AgriTech","Precision Agriculture","precision agriculture crop disease detection yield"),
    ("Finance & FinTech","Financial ML","fintech financial machine learning fraud detection"),
    ("Law & Legal Tech","Legal NLP","legal NLP contract analysis court documents"),
    ("Education Technology","Learning Analytics","learning analytics intelligent tutoring education"),
    ("Smart Cities","Urban Computing","smart cities urban computing traffic IoT"),
    ("Energy & Power Systems","Renewable Energy","renewable energy solar wind power prediction"),
    ("Environmental Science","Climate ML","climate change environmental ML prediction"),
    ("Automotive Engineering","Autonomous Driving","autonomous driving self-driving LIDAR perception"),
    ("Robotics","Robot Learning","robotics manipulation learning control"),
    ("Manufacturing & Industry 4.0","Industry 4.0","industry 4.0 digital twin predictive maintenance"),
    ("Quantum Computing","Quantum ML","quantum computing machine learning quantum algorithms"),
    ("GIS & Remote Sensing","Remote Sensing","remote sensing satellite image segmentation"),
    ("Speech & Audio Processing","Speech Recognition","speech recognition text-to-speech acoustic"),
    ("AR/VR & Metaverse","XR Technology","augmented reality virtual reality metaverse XR"),
    ("Internet of Things","IoT ML","internet of things IoT anomaly detection edge"),
    ("Databases & Big Data","Big Data","big data processing Spark streaming analytics"),
    ("DevOps & Cloud Native","Cloud Native","cloud native Kubernetes microservices DevOps"),
    ("Social Media Analytics","Social Media AI","social media sentiment analysis misinformation"),
    ("Fashion & Textile Technology","Fashion AI","fashion recommendation virtual try-on style"),
    ("Food Science & Nutrition","Food AI","food safety nutrition machine learning"),
    ("Mental Health & Psychology Technology","Mental Health AI","mental health depression detection NLP"),
    ("Architecture & Construction Technology","Construction AI","BIM construction safety monitoring digital twin"),
    ("Journalism & Media Technology","Media AI","fake news detection deepfake media journalism"),
    ("Sports Analytics","Sports AI","sports analytics performance prediction tracking"),
    ("Marine & Ocean Engineering","Ocean AI","marine ocean monitoring underwater ML"),
    ("Disaster Management","Disaster AI","disaster management early warning prediction"),
    ("Defense & Security","Defense AI","military defense AI surveillance"),
    ("Digital Forensics","Forensics AI","digital forensics malware analysis OSINT"),
]

S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"


def fetch_stats(query: str, year: int, max_retries: int = 5) -> dict:
    params = {
        "query": query,
        "fields": "year,citationCount,influentialCitationCount,venue",
        "publicationDateOrYear": str(year),
        "limit": "100",
    }
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"{S2_BASE}?{qs}"
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "AcadEval-Research/1.0 (academic, non-commercial)"
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            papers = data.get("data", [])
            total = data.get("total", len(papers))
            citations = sum(p.get("citationCount", 0) or 0 for p in papers)
            influential = sum(p.get("influentialCitationCount", 0) or 0 for p in papers)
            from collections import Counter
            venues = [p.get("venue","") for p in papers if p.get("venue")]
            top_venues = "|".join([v for v,_ in Counter(venues).most_common(3)])
            return {"paper_count": total, "citation_count": citations,
                    "influential_count": influential, "top_venues": top_venues, "ok": True}
        
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = (2 ** attempt) * 5 + random.uniform(3, 8)
                print(f"    429 rate limit — waiting {wait:.1f}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                print(f"    HTTP {e.code}: {e}")
                break
        except Exception as e:
            print(f"    Error: {e}")
            break
    
    return {"paper_count": 0, "citation_count": 0, "influential_count": 0, "top_venues": "", "ok": False}


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
    
    for tid, (domain, sub_domain, query) in enumerate(TOPIC_MAP, start=1):
        topic_name = " ".join(query.split()[:3])
        print(f"\n[{tid}/{len(TOPIC_MAP)}] {domain} — {sub_domain}")
        
        year_counts = []
        year_rows = []
        
        for year in years:
            stats = fetch_stats(query, year)
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
                "source": "Semantic Scholar API",
                "fetched_at": now,
            })
            
            ok = "ok" if stats["ok"] else "ERR"
            print(f"  {year}: {stats['paper_count']:>6} papers  [{ok}]")
            
            # Polite delay between requests: 3-5 seconds
            time.sleep(random.uniform(3.0, 5.0))
        
        ts = trending_score(year_counts)
        for row in year_rows:
            row["trending_score"] = ts
        rows.extend(year_rows)
        
        # Longer pause between topics
        time.sleep(random.uniform(5.0, 8.0))
    
    print(f"\nWriting {len(rows)} rows to {OUTPUT}")
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print("Done!")


if __name__ == "__main__":
    main()
