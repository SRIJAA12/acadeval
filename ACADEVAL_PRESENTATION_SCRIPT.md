# AcadEval+ — Presentation Script

### A simple, spoken walk-through of what we built and why it counts as research

*Use this as a talking script — read it out loud, in your own voice, when explaining the project to your guide or a panel. Each feature is written as: what screen to show, what it does (plain words), then why it matters for the paper (the research angle).*

---

## Quick Screen Navigation Summary

| Section | 🖥️ Screen / Page to Show | 🔘 What to Click |
| :--- | :--- | :--- |
| **Opening** | Faculty Dashboard | Main page overview |
| **1. Document Parsing & GitHub** | Student Upload Page | Mode selector (PDF/PPT/Video/GitHub) |
| **2. Domain Classification** | Project Report View | Top Header badges (*Domain / Subdomain*) |
| **3. Entity & Feature Extraction** | Project Report View | `Extracted Entities (Module 3)` Card |
| **4. Knowledge Graph Construction** | Project Report View | `Graph Novelty` Tab |
| **5. The Graph-Based Novelty Engine** | Project Report View | `5 Explainable Graph Novelty Signals` |
| **6. Interactive Knowledge Graph Explorer** | Sidebar Menu | `Graph Explorer` Page |
| **7. Faculty Entity Review Queue** | Sidebar Menu | `Entity Review Queue` Page |
| **8. Automated AI Technical Viva Voce** | Student Report View | `Take Technical Viva` Button |
| **9. Citation & Reference Analysis** | Project Report View | Citation Analysis Section |
| **10. Writing Quality Analysis** | Project Report View | Writing Quality Section |
| **11. Research Trend Scoring** | Project Report View | `Graph Novelty` → Literature Trend Card |
| **12. Explainable AI Layer** | Project Report View | `AI Explainability` Tab |
| **13. Student Appeals & Re-Evaluation** | Sidebar Menu | `Appeals Inbox` Page |
| **14. Faculty Ground Truth & Rubrics** | Project Report View / Rubric Builder | `Module 7: Faculty Ground Truth` Form |
| **15. Semester Benchmarks & Leaderboard** | Sidebar Menu | `Leaderboard & Benchmarks` Page |
| **Closing** | Project Report View | Top Overall Score Gauge Card |

---

## Opening (30 seconds)

* 🖥️ **Page to Show:** Faculty Dashboard (`http://localhost:5173`)

"Right now, when a guide has to judge whether a student's project idea is actually new, there's no tool for that. Plagiarism checkers like Turnitin only catch copied *text*. Nothing checks whether the *idea itself* is new. That's the gap we're filling. We call the project AcadEval+, and everything I'm about to show you is built around one core idea: instead of guessing whether a project is novel, we turn every proposal into a small structured graph, and we measure novelty from the *shape* of that graph."

---

## 1. Document & Repository Parsing

* 🖥️ **Page to Show:** Student Upload Form (`/upload` or `/projects`) — *Click file upload or GitHub URL field*

**What it does:** The student uploads their proposal — PDF, Word, PowerPoint, or an MP4 presentation video — or provides a GitHub repo URL. The system reads it and pulls out the title, abstract, and code structure automatically.

**Why it matters for the paper:** Honestly, this part isn't research — it's plumbing. It has to exist so everything else can work, but it won't appear in the paper except as a line in the "system implementation" section. Good to have, not something to spend pitch time on.

---

## 2. Domain Classification

* 🖥️ **Page to Show:** Project Report Header (`/projects/:id`) — *Point to the Domain badge (e.g. AI/ML → Computer Vision)*

**What it does:** The system reads the abstract and figures out which field the project belongs to — for example, "Artificial Intelligence → Computer Vision" — by comparing it against a list of known categories.

**Why it matters for the paper:** This is what makes every later comparison fair. If we didn't do this, the system might compare a face-recognition project against a blockchain project, which is meaningless. In the paper, this shows up as: "we scope novelty comparisons within the same domain," which is a small but necessary methodological choice reviewers will expect us to have made deliberately.

---

## 3. Entity and Feature Extraction

* 🖥️ **Page to Show:** Project Report View — *Scroll to "Extracted Entities (Module 3)" card*

**What it does:** The system picks out the specific building blocks of a project from the text — which algorithm, which technology, which framework, dataset, or real-world application it's aimed at.

**Why it matters for the paper:** This is the step that turns a paragraph of text into structured data. Without it, there's nothing to build a graph from. In the paper, this becomes part of the "method" section — how we go from raw text to structured knowledge.

---

## 4. Project Knowledge Graph Construction

* 🖥️ **Page to Show:** Project Report View — *Click the "Graph Novelty" tab*

**What it does:** Once we know a project's algorithm, technology, dataset, and application, we connect them into a small graph — the project sits in the middle, linked out to each of its parts, like a mind-map.

**Why it matters for the paper:** This is the actual shift we're proposing — representing a project as a *graph* instead of a block of text. This is the idea we'd put in the title of the paper. It's not something anyone else in this space is doing for academic project evaluation.

---

## 5. The Graph-Based Novelty Engine

* 🖥️ **Page to Show:** Project Report View → `Graph Novelty` Tab — *Point to the 5 score progress bars card*

**What it does:** This is the heart of the whole project. Instead of comparing text, we compare *graphs*. We look at five things: how far this project's graph sits from every existing one, how rare its individual parts are, how rare the *combination* of parts is, how crowded its neighborhood is, and whether it creates a connection between two ideas that's never existed before.

**Why it matters for the paper:** This is the actual research contribution. Every other tool that claims to check "novelty" uses either a simple text-match or a made-up weighted formula nobody can defend. We're doing neither — we're deriving novelty from the *structure* of the data itself, using methods that already have decades of academic backing in network science. This is what we'd defend in front of a reviewer, and it's the part of the system worth the most time in any pitch or demo.

---

## 6. Interactive Knowledge Graph Explorer

* 🖥️ **Page to Show:** Sidebar Navigation — *Click "Graph Explorer"*

**What it does:** This gives guides and department heads an interactive map of the whole department's projects. You can zoom in, search any tool or algorithm, filter by category, and see how all student projects link together in 1-hop or 2-hop neighborhoods.

**Why it matters for the paper:** It proves our system works on a full collection of projects, not just one file. In the paper, this powers our visual figures showing how different project clusters separate cleanly in graph space.

---

## 7. Faculty Entity Review Queue

* 🖥️ **Page to Show:** Sidebar Navigation — *Click "Entity Review Queue"*

**What it does:** When student text contains brand-new tools or terms that aren't in our system dictionary, the AI flags them and puts them in a pending list for faculty to approve or reject with one click.

**Why it matters for the paper:** It shows we have a "human-in-the-loop" design. The system doesn't get stuck when new technologies appear — faculty can continuously update the dictionary, keeping the tool accurate over time.

---

## 8. Automated AI Technical Viva Voce

* 🖥️ **Page to Show:** Student Report View — *Click the "Take Technical Viva" button to open the popup modal*

**What it does:** The system automatically generates 5 technical viva questions based on the exact algorithms and tools extracted from the student's own project. The student answers on screen, and the AI grades their technical depth instantly.

**Why it matters for the paper:** It tests whether the student actually understands what they submitted, helping catch cases where someone copied a project report without knowing how it works.

---

## 9. Citation and Reference Analysis

* 🖥️ **Page to Show:** Project Report View — *Scroll to Citation & References section*

**What it does:** The system checks a proposal's reference list — are there enough citations, are they real, are they recent — using tools that read the bibliography and cross-check it against a real research database.

**Why it matters for the paper:** This isn't part of the novelty score — it's a separate, supporting signal. In the paper, it shows we're not just measuring one thing in isolation; we're giving the guide a fuller picture. It's a nice-to-have section, not a core contribution.

---

## 10. Writing Quality Analysis

* 🖥️ **Page to Show:** Project Report View — *Point to Clarity / Completeness scores*

**What it does:** A quick readability and clarity check on the proposal text — flags writing that might need editing before submission.

**Why it matters for the paper:** Same as citation analysis — it's a practical, supporting feature for the tool, not something we'd claim as a research result. Worth mentioning as part of the complete system, not worth dwelling on.

---

## 11. Research Trend Scoring

* 🖥️ **Page to Show:** Project Report View → `Graph Novelty` Tab — *Scroll down to "Literature Trend (Semantic Scholar)" card*

**What it does:** We check whether a project's topic is currently rising or fading in the research world, by pulling real publication data from Semantic Scholar.

**Why it matters for the paper:** This adds context to novelty. A topic that's rare *and* rising is a different story from a topic that's rare *and* dying out. It's a secondary signal that makes the final report richer — worth a short mention in the method section, not a headline feature.

---

## 12. Explainable AI Layer

* 🖥️ **Page to Show:** Project Report View — *Click the "AI Explainability" tab*

**What it does:** Whenever the system produces a score using machine learning, this layer explains *why* — showing line-by-line highlights of which sentences pushed the score up or down — instead of just handing back a black-box number.

**Why it matters for the paper:** This directly answers the question every reviewer and every faculty member will ask: "how do I know I can trust this score?" A method that can explain itself is taken far more seriously than a black box. This is worth mentioning any time someone questions whether the system is trustworthy.

---

## 13. Student Appeals and Re-Evaluation Workflow

* 🖥️ **Page to Show:** Sidebar Navigation — *Click "Appeals Inbox"*

**What it does:** If a student thinks their automated score is unfair, they can submit an appeal explaining why. The appeal goes directly to the faculty inbox, where a guide can review the student's reason and override the score if needed.

**Why it matters for the paper:** It demonstrates system fairness and practical governance. In real deployment, automated tools can't be 100% final — having a clean human override workflow makes the system production-ready.

---

## 14. Faculty Ground-Truth and Custom Rubrics

* 🖥️ **Page to Show:** `Graph Novelty` Tab — *Scroll to "Module 7: Faculty Ground Truth Feedback" box* (or Rubric Builder page)

**What it does:** After the system outputs a report, real faculty members give their own 1-to-10 rating on the project's novelty and can set custom rubric weights for different evaluation criteria.

**Why it matters for the paper:** This is what turns the project from "a tool we built" into "a tool we tested." Once we collect faculty scores side-by-side with system scores, we run statistical tests to prove our system matches real expert human judgment. This comparison is the most important number in the whole paper.

---

## 15. Semester Benchmarks and Leaderboards

* 🖥️ **Page to Show:** Sidebar Navigation — *Click "Leaderboard & Benchmarks"*

**What it does:** Shows department-wide project rankings, score averages for the semester, and comparisons across past academic years.

**Why it matters for the paper:** Shows institutional utility for HODs and department admins. It proves the system scales beyond single projects to provide high-level academic analytics.

---

## Closing (30 seconds)

* 🖥️ **Page to Show:** Project Report View — *Point to the overall score gauge at the top*

"So to sum it up: the graph construction and the novelty engine are the actual research — that's what makes this different from anything on the market. The AI viva, citation, writing-quality, and trend checks make it a genuinely useful tool day-to-day. The explainability layer makes it trustworthy. And the faculty feedback loop is what lets us *prove*, with real numbers, that it works — which is exactly what we need to get this published."

---

### If asked "isn't this just a website?"

"The website is just how people reach it. The actual contribution is the idea underneath — that novelty can be measured from the structure of a knowledge graph instead of a guess or a made-up formula. That idea, plus the dataset we're building to prove it works, is what makes this a research paper and not just a project."
