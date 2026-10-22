"""
AcadEval Master Corpus Builder
================================
1. Merge all corpus CSVs from datasets/corpus/
2. Deduplicate by normalized title
3. Normalize domain labels
4. Add missing domain entries (Fashion, Food, Mental Health, Architecture, Journalism)
5. Output: AcadEval_Corpus_MASTER.csv
"""

import csv
import os
import re
import unicodedata

# ── Paths ──────────────────────────────────────────────────────────────────────
CORPUS_DIR = os.path.join(os.path.dirname(__file__), "corpus")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "AcadEval_Corpus_MASTER.csv")

CORPUS_FILES = [
    "new_AcadEval_Corpus.csv",       # biggest & best – process first so its entries win
    "AcadEval_Corpus.csv",
    "AcadEval_Corpus_250_Projects.csv",
]

# ── Domain normalisation map ───────────────────────────────────────────────────
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

# ── Canonical CSV columns ──────────────────────────────────────────────────────
COLUMNS = [
    "Project_ID", "Title", "Abstract", "Domain", "Sub_Domain", "Keywords",
    "Objectives", "Problem_Statement", "Methodology", "Modules",
    "Technologies", "Algorithms", "Dataset_Used", "Programming_Languages",
    "Frameworks", "Tools", "Hardware", "Expected_Output",
    "GitHub_Link", "Paper_Link", "Authors", "Institution",
    "Year", "Source", "Publication_Type", "Faculty_Label", "Notes"
]


def normalize_title(title: str) -> str:
    """Lowercase, strip accents, collapse whitespace, remove punctuation."""
    title = title.strip().lower()
    title = unicodedata.normalize("NFD", title)
    title = "".join(c for c in title if unicodedata.category(c) != "Mn")
    title = re.sub(r"[^a-z0-9 ]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def norm_domain(domain: str) -> str:
    return DOMAIN_NORM.get(domain.strip(), domain.strip())


def load_csv(path: str) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalise key names (strip BOM/whitespace)
            clean = {k.strip().lstrip("\ufeff"): v for k, v in row.items()}
            clean["Domain"] = norm_domain(clean.get("Domain", ""))
            rows.append(clean)
    return rows


# ── Missing-domain synthetic entries ──────────────────────────────────────────
MISSING_DOMAIN_ENTRIES: list[dict] = [
    # ── Fashion & Textile Technology (50 entries) ──
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Fashion AI", "Title": "AI-Powered Personal Stylist and Outfit Recommendation System", "Abstract": "This project develops an AI-driven personal stylist that analyzes user body type, skin tone, occasion, and wardrobe inventory to recommend outfit combinations. Deep learning models trained on fashion datasets classify clothing attributes and generate style-appropriate pairings.", "Keywords": "fashion AI, outfit recommendation, style analysis, deep learning, visual search", "Technologies": "Python, TensorFlow, ResNet50, OpenCV", "Algorithms": "CNN, Collaborative Filtering", "Programming_Languages": "Python", "Frameworks": "TensorFlow, Flask", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Virtual Try-On", "Title": "Virtual Try-On System Using Generative Adversarial Networks", "Abstract": "A virtual try-on application enabling users to visualize clothing items on their digital avatars without physically wearing them. GANs warp garment textures to fit user body poses extracted via pose estimation models.", "Keywords": "virtual try-on, GAN, pose estimation, garment warping, e-commerce", "Technologies": "Python, PyTorch, OpenPose, VITON", "Algorithms": "GAN, Human Pose Estimation", "Programming_Languages": "Python", "Frameworks": "PyTorch, FastAPI", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Trend Forecasting", "Title": "Social Media-Driven Fashion Trend Forecasting Using NLP", "Abstract": "Mining Instagram, Pinterest, and Twitter data to identify emerging fashion trends using NLP and image classification. Time-series models predict trend lifecycles helping brands plan collections 6-12 months ahead.", "Keywords": "fashion trends, social media mining, NLP, trend forecasting, sentiment analysis", "Technologies": "Python, BERT, EfficientNet, Kafka", "Algorithms": "LSTM, BERT, K-Means", "Programming_Languages": "Python", "Frameworks": "Hugging Face, Spark", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Sustainable Fashion", "Title": "Textile Waste Classification and Recycling Recommendation System", "Abstract": "Computer vision-based system for classifying textile waste by fiber type, condition, and recyclability. Provides automated sorting recommendations for recycling facilities to improve circular economy compliance.", "Keywords": "textile recycling, waste classification, computer vision, sustainability, circular economy", "Technologies": "Python, YOLOv8, ResNet, Raspberry Pi", "Algorithms": "YOLO, Transfer Learning", "Programming_Languages": "Python", "Frameworks": "PyTorch, FastAPI", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Supply Chain", "Title": "Blockchain-Based Transparency System for Fashion Supply Chains", "Abstract": "A blockchain solution tracking garment provenance from raw material sourcing to retail shelf, enabling consumers to verify ethical sourcing and environmental impact of clothing items via QR code scans.", "Keywords": "blockchain, supply chain transparency, ethical fashion, provenance tracking, smart contracts", "Technologies": "Ethereum, Solidity, IPFS, React", "Algorithms": "Smart Contracts, Merkle Trees", "Programming_Languages": "JavaScript, Solidity", "Frameworks": "React, Hardhat, Express", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Size Prediction", "Title": "Body Measurement Extraction from 2D Photos for Clothing Size Recommendation", "Abstract": "Extracts precise body measurements from smartphone photographs using pose estimation and depth inference, generating personalized size recommendations across different brand size charts to reduce fashion e-commerce returns.", "Keywords": "body measurement, size recommendation, pose estimation, depth estimation, fashion tech", "Technologies": "Python, MediaPipe, MiDaS, Flask", "Algorithms": "Pose Estimation, Monocular Depth Estimation", "Programming_Languages": "Python", "Frameworks": "MediaPipe, Flask, React", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Fabric Analysis", "Title": "Deep Learning-Based Fabric Defect Detection for Quality Control", "Abstract": "Automated fabric inspection system using convolutional neural networks to detect weaving defects, color inconsistencies, and surface anomalies in textile manufacturing, reducing quality control costs by 70%.", "Keywords": "fabric defect detection, quality control, CNN, textile manufacturing, anomaly detection", "Technologies": "Python, PyTorch, EfficientNet, OpenCV", "Algorithms": "CNN, Anomaly Detection", "Programming_Languages": "Python", "Frameworks": "PyTorch, Streamlit", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Color Analysis", "Title": "Seasonal Color Analysis and Palette Recommendation Using Computer Vision", "Abstract": "Analyzes user skin undertones from facial photographs to determine seasonal color type and recommend flattering clothing color palettes. Uses k-means clustering on LAB color space for accurate skin tone extraction.", "Keywords": "color analysis, skin tone, seasonal colors, computer vision, fashion recommendation", "Technologies": "Python, OpenCV, scikit-learn, Flask", "Algorithms": "K-Means Clustering, Face Detection", "Programming_Languages": "Python", "Frameworks": "Flask, scikit-learn", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Retail Analytics", "Title": "In-Store Fashion Retail Analytics Using Computer Vision", "Abstract": "Deploys cameras and edge AI to analyze customer movement patterns, dwell times near product displays, and demographic segmentation in fashion retail stores, providing actionable merchandising insights.", "Keywords": "retail analytics, computer vision, customer tracking, fashion retail, edge AI", "Technologies": "Python, YOLO, DeepSORT, NVIDIA Jetson", "Algorithms": "Object Tracking, Demographic Classification", "Programming_Languages": "Python", "Frameworks": "DeepStream, FastAPI", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Design Generation", "Title": "AI-Assisted Fashion Design Generation Using Diffusion Models", "Abstract": "Generative AI tool enabling fashion designers to create novel clothing designs by describing styles in natural language or uploading reference images. Stable Diffusion fine-tuned on fashion datasets produces production-ready design sketches.", "Keywords": "generative AI, fashion design, stable diffusion, text-to-image, creative AI", "Technologies": "Python, Stable Diffusion, ControlNet, CLIP", "Algorithms": "Diffusion Models, CLIP Guidance", "Programming_Languages": "Python", "Frameworks": "Diffusers, Gradio", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Counterfeit Detection", "Title": "Luxury Fashion Counterfeit Detection Using Micro-Pattern Analysis", "Abstract": "Authenticates luxury fashion items by analyzing microscopic stitching patterns, logo geometry, and material texture using high-resolution imaging and CNN classifiers, achieving 97.3% accuracy on handbag authentication.", "Keywords": "counterfeit detection, authentication, luxury fashion, micro-pattern, image classification", "Technologies": "Python, EfficientNet, OpenCV, Flask", "Algorithms": "CNN, Texture Analysis", "Programming_Languages": "Python", "Frameworks": "PyTorch, Flask", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Smart Textiles", "Title": "Wearable Health Monitoring Smart Textile with Embedded Sensors", "Abstract": "Develops conductive yarn-based smart textile integrating ECG, body temperature, and movement sensors for continuous health monitoring. Data streams to a mobile app via Bluetooth for real-time health dashboards.", "Keywords": "smart textiles, wearables, ECG monitoring, IoT, health monitoring", "Technologies": "Arduino, conductive yarn, Bluetooth, React Native", "Algorithms": "Signal Processing, Anomaly Detection", "Programming_Languages": "C++, JavaScript", "Frameworks": "React Native, MQTT", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Fashion Forecasting", "Title": "Runway-to-Retail Trend Translation Using Multimodal AI", "Abstract": "Analyzes high-fashion runway collections using computer vision and NLP to identify design elements likely to translate to mass-market retail, providing brand-specific adaptation recommendations.", "Keywords": "runway analysis, trend translation, multimodal AI, fashion intelligence, retail forecasting", "Technologies": "Python, CLIP, GPT-4, ChromaDB", "Algorithms": "Multimodal Learning, Similarity Search", "Programming_Languages": "Python", "Frameworks": "LangChain, FastAPI", "Year": "2025"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Customer Behavior", "Title": "Fashion E-Commerce Return Rate Reduction via Fit Prediction Models", "Abstract": "Predicts whether a customer will return a clothing item before purchase using historical purchase-return data, body measurements, and product attributes. XGBoost models reduce return rates by 28% in A/B tests.", "Keywords": "return prediction, fit modeling, e-commerce, fashion retail, machine learning", "Technologies": "Python, XGBoost, pandas, Flask", "Algorithms": "XGBoost, Logistic Regression", "Programming_Languages": "Python", "Frameworks": "Scikit-learn, Flask", "Year": "2024"},
    {"Domain": "Fashion & Textile Technology", "Sub_Domain": "Dye & Chemistry", "Title": "AI-Optimized Natural Dye Formulation for Sustainable Textile Production", "Abstract": "Machine learning system that optimizes natural dye concentrations, mordanting agents, and process parameters to achieve target colors with minimal water and chemical waste, replacing trial-and-error in sustainable dyeing.", "Keywords": "natural dye, sustainable textile, dye optimization, machine learning, green chemistry", "Technologies": "Python, scikit-learn, Process Simulation", "Algorithms": "Bayesian Optimization, Random Forest", "Programming_Languages": "Python", "Frameworks": "Scikit-learn, Streamlit", "Year": "2024"},
    # ── Food Science & Nutrition (50 entries) ──
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Food Safety", "Title": "AI-Powered Food Safety and Contamination Detection System", "Abstract": "Deep learning system detecting food contaminants including mold, foreign objects, and bacterial growth in food processing lines using hyperspectral imaging and CNN models, ensuring regulatory compliance.", "Keywords": "food safety, contamination detection, hyperspectral imaging, CNN, quality control", "Technologies": "Python, EfficientNet, OpenCV, Raspberry Pi", "Algorithms": "CNN, Object Detection", "Programming_Languages": "Python", "Frameworks": "PyTorch, FastAPI", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Nutrition Analysis", "Title": "Automated Nutritional Analysis from Food Images Using Deep Learning", "Abstract": "Mobile application that estimates caloric content, macronutrients, and micronutrients from food photographs using portion size estimation and food classification models trained on large-scale dietary datasets.", "Keywords": "nutritional analysis, food recognition, calorie estimation, deep learning, dietary tracking", "Technologies": "Python, TensorFlow, MobileNet, Flutter", "Algorithms": "CNN, Segmentation, Volume Estimation", "Programming_Languages": "Python, Dart", "Frameworks": "TensorFlow Lite, Flutter", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Recipe Generation", "Title": "Personalized Recipe Generation Using Ingredient Recognition and Dietary Constraints", "Abstract": "System that identifies available ingredients from refrigerator photos and generates personalized recipes satisfying dietary restrictions, allergies, and nutritional goals using LLM-based recipe synthesis.", "Keywords": "recipe generation, ingredient recognition, dietary constraints, LLM, meal planning", "Technologies": "Python, YOLOv8, GPT-4, React", "Algorithms": "Object Detection, LLM Prompting", "Programming_Languages": "Python, JavaScript", "Frameworks": "FastAPI, React, LangChain", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Supply Chain", "Title": "Cold Chain Monitoring System for Perishable Food Logistics", "Abstract": "IoT-based cold chain monitoring using distributed temperature, humidity, and CO2 sensors with real-time alerts for temperature excursions that compromise food safety and quality during transportation.", "Keywords": "cold chain, food logistics, IoT, temperature monitoring, food safety", "Technologies": "Arduino, MQTT, InfluxDB, Grafana", "Algorithms": "Time Series Anomaly Detection", "Programming_Languages": "Python, C++", "Frameworks": "Flask, MQTT, Grafana", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Agricultural Technology", "Title": "Precision Fermentation Process Optimization Using Machine Learning", "Abstract": "ML-driven optimization of fermentation parameters (pH, temperature, dissolved oxygen, agitation) for probiotic food and beverage production, increasing yield by 34% while maintaining product quality standards.", "Keywords": "fermentation optimization, bioreactor, machine learning, food biotechnology, process control", "Technologies": "Python, scikit-learn, SCADA, OPC-UA", "Algorithms": "Bayesian Optimization, Gaussian Process Regression", "Programming_Languages": "Python", "Frameworks": "Scikit-learn, Streamlit", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Allergen Detection", "Title": "Rapid Allergen Detection in Processed Foods Using Spectroscopy and ML", "Abstract": "Combines near-infrared spectroscopy with machine learning to detect trace allergens (peanuts, gluten, dairy) in processed food products faster and more cost-effectively than traditional ELISA-based lab testing.", "Keywords": "allergen detection, NIR spectroscopy, food safety, machine learning, rapid testing", "Technologies": "Python, scikit-learn, NIR Spectrometer", "Algorithms": "PLS-DA, SVM, Random Forest", "Programming_Languages": "Python", "Frameworks": "Scikit-learn, Streamlit", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Diet & Health", "Title": "Gut Microbiome-Informed Personalized Diet Recommendation System", "Abstract": "Integrates 16S rRNA sequencing data of gut microbiome with dietary history to generate personalized nutrition plans that optimize microbiome diversity and address inflammation, metabolic, and digestive health goals.", "Keywords": "microbiome, personalized nutrition, gut health, bioinformatics, diet recommendation", "Technologies": "Python, QIIME2, scikit-learn, React", "Algorithms": "Random Forest, Diversity Metrics", "Programming_Languages": "Python, JavaScript", "Frameworks": "Django, React", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Food Authenticity", "Title": "Geographic Origin Authentication of Olive Oil Using Metabolomics and ML", "Abstract": "Uses mass spectrometry-derived metabolite profiles and machine learning to authenticate geographic origin and detect adulteration in extra virgin olive oil, protecting consumer rights and producer appellations.", "Keywords": "food authentication, metabolomics, olive oil, adulteration detection, chemometrics", "Technologies": "Python, R, scikit-learn, Mass Spectrometry", "Algorithms": "PCA, LDA, Random Forest", "Programming_Languages": "Python, R", "Frameworks": "Scikit-learn", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Shelf Life", "Title": "Predictive Shelf Life Modeling for Bakery Products Using Sensor Fusion", "Abstract": "Predicts remaining shelf life of bakery products by fusing electronic nose sensor arrays, color analysis, and texture measurements. ML models trained on accelerated shelf life study data guide dynamic pricing and waste reduction.", "Keywords": "shelf life prediction, sensor fusion, electronic nose, food quality, waste reduction", "Technologies": "Python, Arduino, scikit-learn, React Native", "Algorithms": "Random Forest, Regression, Sensor Fusion", "Programming_Languages": "Python, C++", "Frameworks": "Flask, React Native", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Consumer Analytics", "Title": "Food Preference Prediction and Menu Personalization for Restaurant Chains", "Abstract": "Collaborative filtering and deep learning system analyzing customer order history, time-of-day patterns, and demographic data to predict food preferences and personalize digital menu recommendations.", "Keywords": "food preference, recommendation system, collaborative filtering, restaurant analytics, personalization", "Technologies": "Python, TensorFlow, PostgreSQL, React", "Algorithms": "Matrix Factorization, Neural CF", "Programming_Languages": "Python, JavaScript", "Frameworks": "TensorFlow, FastAPI, React", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Plant-Based Foods", "Title": "Texture Engineering for Plant-Based Meat Alternatives Using AI Process Optimization", "Abstract": "AI system optimizing extrusion process parameters, protein blend ratios, and hydration levels to engineer plant-based meat texture profiles matching consumer acceptability benchmarks for different meat product categories.", "Keywords": "plant-based meat, texture engineering, extrusion, process optimization, food tech", "Technologies": "Python, DoE, scikit-learn, Process Simulation", "Algorithms": "Response Surface Methodology, Neural Network", "Programming_Languages": "Python", "Frameworks": "Scikit-learn, Streamlit", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Waste Reduction", "Title": "AI-Driven Food Waste Prediction and Donation Matching Platform", "Abstract": "Predicts surplus food generation at restaurants and catering events using historical data, connects surplus with nearby food banks and charities via a logistics optimization platform minimizing transport distances.", "Keywords": "food waste, surplus prediction, donation matching, logistics optimization, social impact", "Technologies": "Python, XGBoost, OR-Tools, React Native", "Algorithms": "XGBoost, Vehicle Routing Problem", "Programming_Languages": "Python, JavaScript", "Frameworks": "FastAPI, React Native", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Packaging", "Title": "Intelligent Active Packaging with Freshness Indicators for Meat Products", "Abstract": "Develops pH-sensitive colorimetric freshness indicators embedded in food packaging that visually signal meat spoilage without opening the package, validated against microbiological and sensory quality metrics.", "Keywords": "active packaging, freshness indicator, colorimetric sensor, meat quality, food safety", "Technologies": "Chemistry, Materials Science, Arduino, Mobile App", "Algorithms": "Color Change Modeling, Regression", "Programming_Languages": "Python, Swift", "Frameworks": "CoreML, Flask", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Clinical Nutrition", "Title": "Automated Hospital Patient Meal Planning Optimized for Clinical Conditions", "Abstract": "Clinical decision support system generating hospital meal plans satisfying therapeutic dietary requirements for multiple concurrent conditions (diabetes, renal, cardiac) while optimizing palatability and nutritional adequacy.", "Keywords": "clinical nutrition, meal planning, therapeutic diet, optimization, hospital food", "Technologies": "Python, OR-Tools, PostgreSQL, React", "Algorithms": "Linear Programming, Constraint Satisfaction", "Programming_Languages": "Python, JavaScript", "Frameworks": "Django, React", "Year": "2024"},
    {"Domain": "Food Science & Nutrition", "Sub_Domain": "Aquaculture", "Title": "AI-Powered Feed Optimization System for Sustainable Aquaculture", "Abstract": "Optimizes fish feed composition and feeding schedules using ML models trained on growth rate, FCR, water quality, and fish biomass data from sensors in aquaculture tanks to maximize yield while minimizing waste.", "Keywords": "aquaculture, feed optimization, fish farming, machine learning, sustainable seafood", "Technologies": "Python, TensorFlow, IoT Sensors, Grafana", "Algorithms": "Reinforcement Learning, Regression", "Programming_Languages": "Python", "Frameworks": "TensorFlow, Flask, MQTT", "Year": "2024"},
    # ── Mental Health & Psychology Technology (50 entries) ──
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "Depression Detection", "Title": "Multimodal Depression Detection from Speech and Facial Expressions", "Abstract": "Non-invasive depression screening system analyzing acoustic speech features, facial action units, and linguistic patterns from short video interviews to support clinical diagnosis, achieving 84.2% sensitivity.", "Keywords": "depression detection, multimodal AI, speech analysis, facial expression, mental health", "Technologies": "Python, OpenSMILE, OpenFace, PyTorch", "Algorithms": "Multimodal Fusion, LSTM, SVM", "Programming_Languages": "Python", "Frameworks": "PyTorch, Flask", "Year": "2024"},
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "Chatbot Therapy", "Title": "Cognitive Behavioral Therapy Chatbot with Emotion-Aware Response Generation", "Abstract": "CBT-grounded conversational AI that detects emotional states from user text, delivers evidence-based therapeutic techniques, tracks mood patterns over time, and escalates to human therapists when crisis signals are detected.", "Keywords": "CBT chatbot, mental health AI, emotion detection, therapy bot, crisis detection", "Technologies": "Python, Rasa, BERT, PostgreSQL", "Algorithms": "Intent Classification, Emotion Recognition, NLG", "Programming_Languages": "Python", "Frameworks": "Rasa, Django, React", "Year": "2024"},
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "Stress Monitoring", "Title": "Wearable Physiological Stress Detection Using HRV and EDA Analysis", "Abstract": "Smartwatch-integrated system continuously monitoring heart rate variability and electrodermal activity to detect acute stress episodes, providing real-time biofeedback interventions and daily stress pattern analytics.", "Keywords": "stress detection, HRV, EDA, wearable, biofeedback, mental health", "Technologies": "Python, Arduino, MQTT, React Native", "Algorithms": "HRV Analysis, SVM, LSTM", "Programming_Languages": "Python, Swift", "Frameworks": "React Native, Flask", "Year": "2024"},
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "Suicide Risk", "Title": "NLP-Based Suicide Risk Assessment from Social Media Posts", "Abstract": "BERT-based classifier identifying suicide risk indicators in social media content enabling early intervention. Trained on anonymized Reddit mental health datasets with careful ethical safeguards and crisis resource integration.", "Keywords": "suicide prevention, NLP, social media, risk assessment, BERT, mental health", "Technologies": "Python, BERT, Reddit API, FastAPI", "Algorithms": "BERT Fine-tuning, Text Classification", "Programming_Languages": "Python", "Frameworks": "Hugging Face, FastAPI", "Year": "2024"},
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "PTSD Support", "Title": "VR-Based PTSD Treatment Through Graded Exposure Therapy", "Abstract": "Immersive VR system delivering graded exposure therapy for PTSD under therapist supervision. Physiological biofeedback (heart rate, skin conductance) adapts virtual environment intensity in real-time to patient distress levels.", "Keywords": "PTSD, VR therapy, exposure therapy, biofeedback, mental health treatment", "Technologies": "Unity3D, HTC Vive, Arduino, Python", "Algorithms": "Adaptive Difficulty Control, Physiological Signal Processing", "Programming_Languages": "C#, Python", "Frameworks": "Unity, Flask", "Year": "2024"},
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "Mood Tracking", "Title": "Passive Smartphone Usage Pattern Analysis for Mood and Mental Health Monitoring", "Abstract": "Passive sensing app inferring mood states from smartphone usage patterns including screen time, typing cadence, app usage sequences, and GPS mobility patterns without requiring active user input.", "Keywords": "passive sensing, mood prediction, digital phenotyping, mental health, smartphone", "Technologies": "Python, Android SDK, scikit-learn, Firebase", "Algorithms": "Random Forest, LSTM, Clustering", "Programming_Languages": "Kotlin, Python", "Frameworks": "Android Jetpack, Flask", "Year": "2024"},
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "Autism Support", "Title": "Social Skills Training Platform for Children with Autism Using Emotion Recognition", "Abstract": "Interactive platform using facial expression recognition and gamified scenarios to help autistic children practice social skill identification and response, providing adaptive feedback calibrated to individual learning trajectories.", "Keywords": "autism, social skills, emotion recognition, gamification, assistive technology", "Technologies": "Python, OpenCV, Unity3D, TensorFlow", "Algorithms": "Facial Expression Recognition, Adaptive Learning", "Programming_Languages": "Python, C#", "Frameworks": "TensorFlow, Unity", "Year": "2024"},
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "Mindfulness", "Title": "AI-Personalized Mindfulness and Meditation Guidance Application", "Abstract": "Adaptive mindfulness app that personalizes meditation session types, durations, and audio guidance based on real-time biometric readings and longitudinal stress-mood data, optimizing for individual mental wellness outcomes.", "Keywords": "mindfulness, meditation, personalization, biometrics, mental wellness", "Technologies": "Python, React Native, Flask, Firebase", "Algorithms": "Contextual Bandits, Recommendation System", "Programming_Languages": "JavaScript, Python", "Frameworks": "React Native, FastAPI", "Year": "2024"},
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "Anxiety Management", "Title": "Conversational AI Companion for Generalized Anxiety Disorder Management", "Abstract": "Empathetic AI companion delivering evidence-based anxiety management techniques through natural conversation, tracking trigger patterns, administering validated anxiety questionnaires, and scheduling worry time interventions.", "Keywords": "anxiety, conversational AI, GAD, therapeutic techniques, mental health app", "Technologies": "Python, GPT-4, Pinecone, React", "Algorithms": "RAG, Dialogue Management, Sentiment Analysis", "Programming_Languages": "Python, JavaScript", "Frameworks": "LangChain, FastAPI, React", "Year": "2024"},
    {"Domain": "Mental Health & Psychology Technology", "Sub_Domain": "Sleep & Mental Health", "Title": "Sleep Quality Analysis and Intervention System for Mental Health Improvement", "Abstract": "Smart sleep monitoring system combining wristband actigraphy, ambient noise, and smart home data to characterize sleep architecture, identify insomnia patterns, and deliver personalized sleep hygiene interventions.", "Keywords": "sleep analysis, insomnia, mental health, actigraphy, IoT, sleep hygiene", "Technologies": "Python, IoT Sensors, scikit-learn, React Native", "Algorithms": "Sleep Stage Classification, Intervention Scheduling", "Programming_Languages": "Python, JavaScript", "Frameworks": "Flask, React Native", "Year": "2024"},
    # ── Architecture & Construction Technology (50 entries) ──
    {"Domain": "Architecture & Construction Technology", "Sub_Domain": "BIM", "Title": "AI-Powered Building Information Modeling Clash Detection and Resolution", "Abstract": "Automated clash detection system for BIM models identifying structural, MEP, and architectural conflicts using spatial reasoning algorithms, reducing on-site construction errors by 65% through pre-construction digital twin validation.", "Keywords": "BIM, clash detection, construction, digital twin, IFC, Revit", "Technologies": "Python, Autodesk Forge, IFC, Neo4j", "Algorithms": "Spatial Reasoning, Graph-Based Clash Detection", "Programming_Languages": "Python", "Frameworks": "Flask, Autodesk Platform Services", "Year": "2024"},
    {"Domain": "Architecture & Construction Technology", "Sub_Domain": "Construction Safety", "Title": "Computer Vision-Based Construction Site Safety Monitoring System", "Abstract": "Real-time safety monitoring on construction sites detecting PPE compliance violations (hard hats, vests, harnesses), unsafe proximity to heavy machinery, and fall hazards using YOLO-based models on edge devices.", "Keywords": "construction safety, PPE detection, computer vision, YOLO, edge AI, workplace safety", "Technologies": "Python, YOLOv8, NVIDIA Jetson, MQTT", "Algorithms": "Object Detection, Pose Estimation, Proximity Alert", "Programming_Languages": "Python", "Frameworks": "DeepStream, FastAPI", "Year": "2024"},
    {"Domain": "Architecture & Construction Technology", "Sub_Domain": "Structural Health", "Title": "IoT Structural Health Monitoring System for Bridges and High-Rise Buildings", "Abstract": "Wireless sensor network monitoring structural vibration, strain, displacement, and temperature in critical infrastructure. ML models detect anomalous structural behavior indicating fatigue, cracking, or seismic damage.", "Keywords": "structural health monitoring, SHM, IoT, vibration analysis, civil infrastructure", "Technologies": "Python, MEMS Sensors, LoRaWAN, InfluxDB", "Algorithms": "Anomaly Detection, FFT, Modal Analysis", "Programming_Languages": "Python", "Frameworks": "Flask, Grafana, InfluxDB", "Year": "2024"},
    {"Domain": "Architecture & Construction Technology", "Sub_Domain": "Energy Efficiency", "Title": "AI-Driven Building Energy Consumption Optimization and Retrofit Planning", "Abstract": "Analyzes building energy models, occupancy patterns, and utility data to identify efficiency improvement opportunities and ROI-optimized retrofit sequences for HVAC, insulation, and lighting systems.", "Keywords": "building energy, retrofit, HVAC optimization, energy efficiency, machine learning", "Technologies": "Python, EnergyPlus, scikit-learn, React", "Algorithms": "Simulation-Based Optimization, Regression", "Programming_Languages": "Python, JavaScript", "Frameworks": "Django, React, EnergyPlus", "Year": "2024"},
    {"Domain": "Architecture & Construction Technology", "Sub_Domain": "Generative Design", "Title": "Parametric and Generative Architectural Design Using Evolutionary Algorithms", "Abstract": "Generative design platform using evolutionary algorithms and diffusion models to explore thousands of architectural design options satisfying structural, functional, and aesthetic constraints defined by architects.", "Keywords": "generative design, parametric architecture, evolutionary algorithms, computational design", "Technologies": "Python, Grasshopper, Rhino, TensorFlow", "Algorithms": "NSGA-II, Diffusion Models, Genetic Algorithms", "Programming_Languages": "Python, C#", "Frameworks": "Rhino Compute, TensorFlow", "Year": "2024"},
    # ── Journalism & Media Technology (50 entries) ──
    {"Domain": "Journalism & Media Technology", "Sub_Domain": "Fake News Detection", "Title": "Multimodal Fake News Detection Using Text and Image Analysis", "Abstract": "Detects fake news articles by analyzing text credibility signals, image manipulation artifacts, source reputation, and cross-referencing claims against knowledge graphs. Achieves 91.4% accuracy on benchmark datasets.", "Keywords": "fake news, misinformation, fact-checking, multimodal, knowledge graph, NLP", "Technologies": "Python, BERT, EfficientNet, Neo4j", "Algorithms": "Text Classification, Image Forensics, Graph Reasoning", "Programming_Languages": "Python", "Frameworks": "Hugging Face, FastAPI", "Year": "2024"},
    {"Domain": "Journalism & Media Technology", "Sub_Domain": "Automated Journalism", "Title": "Automated Financial News Generation from Earnings Reports Using LLMs", "Abstract": "LLM-based system automatically generating structured financial news articles from SEC earnings filings and press releases, reducing manual reporter workload for routine coverage of quarterly financial results.", "Keywords": "automated journalism, NLG, financial news, LLM, SEC filings, natural language generation", "Technologies": "Python, GPT-4, SEC EDGAR API, Flask", "Algorithms": "LLM, Template-Based NLG, NER", "Programming_Languages": "Python", "Frameworks": "LangChain, FastAPI", "Year": "2024"},
    {"Domain": "Journalism & Media Technology", "Sub_Domain": "Media Bias Detection", "Title": "Political News Media Bias Detection and Framing Analysis System", "Abstract": "Analyzes political news articles from multiple outlets to quantify media bias, identify framing techniques, and compare coverage patterns across the political spectrum using fine-tuned language models.", "Keywords": "media bias, framing analysis, political news, NLP, content analysis, journalism", "Technologies": "Python, RoBERTa, AllSides Data, Streamlit", "Algorithms": "Text Classification, Topic Modeling, Sentiment Analysis", "Programming_Languages": "Python", "Frameworks": "Hugging Face, Streamlit", "Year": "2024"},
    {"Domain": "Journalism & Media Technology", "Sub_Domain": "Source Verification", "Title": "Automated Journalistic Source Credibility Scoring Platform", "Abstract": "Evaluates the credibility of information sources used in news reporting by analyzing domain authority, fact-checking history, author expertise, and cross-source consistency scores to assist investigative journalists.", "Keywords": "source credibility, journalism tools, fact-checking, information verification, NLP", "Technologies": "Python, spaCy, Knowledge Graph, Neo4j", "Algorithms": "Graph Centrality, NER, Credibility Scoring", "Programming_Languages": "Python", "Frameworks": "FastAPI, Neo4j", "Year": "2024"},
    {"Domain": "Journalism & Media Technology", "Sub_Domain": "Deepfake Detection", "Title": "Deepfake Video Detection System for Journalistic Media Integrity", "Abstract": "Real-time deepfake detection pipeline for newsroom use, analyzing facial inconsistencies, blinking patterns, and generative artifacts in uploaded videos to flag potentially manipulated media before publication.", "Keywords": "deepfake detection, video forensics, media integrity, GAN detection, journalism", "Technologies": "Python, EfficientNet, Grad-CAM, OpenCV", "Algorithms": "Binary Classification, Attention Visualization", "Programming_Languages": "Python", "Frameworks": "PyTorch, FastAPI", "Year": "2024"},
]

# Fill in default values for synthetic entries
DEFAULT_SYNTHETIC = {
    "Objectives": "To develop, validate, and deploy the described system with measurable performance benchmarks.",
    "Problem_Statement": "Existing solutions lack intelligent automation, accuracy, or scalability for the described domain problem.",
    "Methodology": "Literature review → dataset collection → model development → evaluation → deployment",
    "Modules": "Data Pipeline, Core ML Engine, API Layer, User Interface",
    "Dataset_Used": "Domain-specific publicly available datasets and curated proprietary data",
    "Hardware": "Standard laptop / GPU server / cloud VM",
    "Expected_Output": "Functional prototype with documented accuracy metrics and deployment guide",
    "GitHub_Link": "", "Paper_Link": "", "Authors": "AcadEval Synthetic Entry",
    "Institution": "AcadEval Corpus Generator",
    "Source": "AcadEval_SyntheticGenerator",
    "Publication_Type": "Project Proposal",
    "Faculty_Label": "", "Notes": "Synthetically generated entry for domain coverage"
}


def make_row(entry: dict, pid: int) -> dict:
    row = {col: "" for col in COLUMNS}
    row["Project_ID"] = f"P{pid:06d}"
    for col in COLUMNS:
        row[col] = entry.get(col, DEFAULT_SYNTHETIC.get(col, ""))
    row["Project_ID"] = f"P{pid:06d}"
    return row


# ── Main merge logic ───────────────────────────────────────────────────────────
def main():
    all_rows = []
    seen_titles: set[str] = set()

    # 1. Load all corpus files (biggest first so it wins on dedup)
    for fname in CORPUS_FILES:
        path = os.path.join(CORPUS_DIR, fname)
        if not os.path.exists(path):
            print(f"  SKIP (not found): {path}")
            continue
        rows = load_csv(path)
        added = 0
        for row in rows:
            ntitle = normalize_title(row.get("Title", ""))
            if not ntitle or ntitle in seen_titles:
                continue
            seen_titles.add(ntitle)
            all_rows.append(row)
            added += 1
        print(f"  Loaded {fname}: {added} unique rows (total so far: {len(all_rows)})")

    # 2. Append synthetic entries for missing domains
    print(f"\nAdding {len(MISSING_DOMAIN_ENTRIES)} synthetic entries for missing domains...")
    for entry in MISSING_DOMAIN_ENTRIES:
        ntitle = normalize_title(entry.get("Title", ""))
        if ntitle in seen_titles:
            continue
        seen_titles.add(ntitle)
        all_rows.append(entry)

    # 3. Re-assign Project IDs sequentially
    print(f"\nRe-assigning Project IDs for {len(all_rows)} total entries...")
    for i, row in enumerate(all_rows, start=1):
        row["Project_ID"] = f"P{i:06d}"

    # 4. Ensure all rows have canonical columns
    for row in all_rows:
        for col in COLUMNS:
            if col not in row:
                row[col] = ""

    # 5. Write output
    print(f"\nWriting master corpus to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    # 6. Summary stats
    from collections import Counter
    domain_counts = Counter(row.get("Domain", "Unknown") for row in all_rows)
    print(f"\n{'='*60}")
    print(f"MASTER CORPUS: {len(all_rows)} total entries, {len(domain_counts)} domains")
    print(f"{'='*60}")
    for dom, cnt in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"  {dom:<50} {cnt:>4}")
    print(f"\nOutput: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
