"""
Add the 15 user-requested topics plus 30 related/expanded topics (45 entries total)
into AcadEval_Corpus_MASTER.csv.
"""
import csv, unicodedata, re
from pathlib import Path

MASTER_FILE = r"D:\acadeval-1\datasets\AcadEval_Corpus_MASTER.csv"
COLUMNS = [
    "Project_ID","Title","Abstract","Domain","Sub_Domain","Keywords",
    "Objectives","Problem_Statement","Methodology","Modules",
    "Technologies","Algorithms","Dataset_Used","Programming_Languages",
    "Frameworks","Tools","Hardware","Expected_Output",
    "GitHub_Link","Paper_Link","Authors","Institution",
    "Year","Source","Publication_Type","Faculty_Label","Notes"
]

DEFAULTS = {
    "Objectives": "Develop and validate the proposed system with measurable performance benchmarks.",
    "Problem_Statement": "Current solutions lack intelligent automation or scalability for this domain challenge.",
    "Methodology": "Literature review -> dataset collection -> system design -> implementation -> evaluation",
    "Modules": "Data Pipeline, Core Engine, API Layer, User Interface",
    "Dataset_Used": "Publicly available domain-specific datasets and benchmark data",
    "Hardware": "Standard workstation / GPU server / Cloud VM",
    "Expected_Output": "Functional prototype with accuracy metrics, API documentation, and deployment guide",
    "GitHub_Link": "",
    "Paper_Link": "",
    "Authors": "AcadEval Synthetic",
    "Institution": "AcadEval Corpus Generator",
    "Source": "AcadEval_SyntheticGenerator",
    "Publication_Type": "Project Proposal",
    "Faculty_Label": "Excellent",
    "Notes": "Added via final user-requested topic expansion"
}

def normalize_title(t):
    t = t.strip().lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

NEW_EXPANSIONS = [
    # ── 1. Intelligent Time-Lapse Generation from Surveillance Footage (Topic + 2 Related)
    {
        "Domain": "Computer Vision", "Sub_Domain": "Video Analytics",
        "Title": "Intelligent Time-Lapse Generation from Surveillance Footage",
        "Abstract": "Adaptive event-driven time-lapse video generation pipeline selecting keyframes based on spatial motion density, object trajectories, and semantic activity alerts from long-term security surveillance streams.",
        "Keywords": "time-lapse,surveillance,video analytics,keyframe selection,OpenCV",
        "Technologies": "Python,OpenCV,YOLOv8,FFmpeg", "Algorithms": "Background Subtraction,Motion Density Profiling,Keyframe Selection",
        "Programming_Languages": "Python", "Frameworks": "PyTorch,FastAPI", "Year": "2025"
    },
    {
        "Domain": "Computer Vision", "Sub_Domain": "Video Analytics",
        "Title": "Spatio-Temporal Frame Interpolation for Video Summarization in Traffic Cameras",
        "Abstract": "Neural network architecture for compressing multi-day traffic video feeds into concise, smooth summary clips using frame interpolation and optical flow estimations.",
        "Keywords": "frame interpolation,video summarization,traffic cameras,optical flow",
        "Technologies": "Python,PyTorch,OpenCV,CUDA", "Algorithms": "SuperSlomo,Optical Flow,Deep Flow Interpolation",
        "Programming_Languages": "Python", "Frameworks": "PyTorch,FastAPI", "Year": "2025"
    },
    {
        "Domain": "Computer Vision", "Sub_Domain": "Video Analytics",
        "Title": "Adaptive Event-Triggered Time-Lapse Generation for Construction Site Monitoring",
        "Abstract": "Automated camera control and frame-stitching software that dynamically increases capture frame-rates upon detecting construction activity (e.g. crane motion, vehicle entry) using edge-computing device.",
        "Keywords": "event-triggered,time-lapse,construction monitoring,edge computing",
        "Technologies": "Python,Raspberry Pi 4,OpenCV,AWS S3", "Algorithms": "Background Modeling,Object Tracking,Trigger Control",
        "Programming_Languages": "Python", "Frameworks": "Flask,AWS SDK", "Year": "2025"
    },

    # ── 2. An Intelligent Solar Forecasting and Energy Management System (Topic + 2 Related)
    {
        "Domain": "Energy & Power Systems", "Sub_Domain": "Renewable Energy",
        "Title": "An Intelligent Solar Forecasting and Energy Management System",
        "Abstract": "Forecasting model integrating historical solar irradiance, local weather feeds, and satellite cloud maps to predict photovoltaic power output and optimize battery charging schedules.",
        "Keywords": "solar forecasting,energy management,photovoltaic,weather api,microgrid",
        "Technologies": "Python,InfluxDB,Grafana,scikit-learn", "Algorithms": "LSTM,GRU,Reinforcement Learning",
        "Programming_Languages": "Python", "Frameworks": "FastAPI,TensorFlow", "Year": "2025"
    },
    {
        "Domain": "Energy & Power Systems", "Sub_Domain": "Renewable Energy",
        "Title": "Deep Learning-Based Photovoltaic Power Forecasting Using Sky Imager Networks",
        "Abstract": "Real-time solar power generation prediction using ground-based sky cameras to track cloud movements, applying CNN-LSTMs to project shade and irradiance shifts.",
        "Keywords": "sky imager,photovoltaic,irradiance forecasting,computer vision",
        "Technologies": "Python,OpenCV,PyTorch,Sky Imager Hardware", "Algorithms": "CNN-LSTM,Optical Flow,Ground-Truth Validation",
        "Programming_Languages": "Python", "Frameworks": "PyTorch", "Year": "2025"
    },
    {
        "Domain": "Energy & Power Systems", "Sub_Domain": "Renewable Energy",
        "Title": "Grid-Tied Microgrid Energy Management Optimization via Deep Q-Networks",
        "Abstract": "Microgrid controller using Deep Reinforcement Learning to coordinate solar panels, battery banks, and grid imports to minimize household electricity bills under time-of-use rates.",
        "Keywords": "microgrid,deep q-network,reinforcement learning,energy optimization",
        "Technologies": "Python,Stable-Baselines3,OpenDSS,Pandas", "Algorithms": "DQN,Q-Learning,Reward Shaping",
        "Programming_Languages": "Python", "Frameworks": "Stable-Baselines3", "Year": "2025"
    },

    # ── 3. Remote monitoring of post surgical patients using non invasive techniques (Topic + 2 Related)
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Patient Monitoring",
        "Title": "Remote Monitoring of Post-Surgical Patients Using Non-Invasive Techniques",
        "Abstract": "Telehealth system tracking post-operative recovery indicators (respiration, skin temperature, movement patterns) using wearable sensors and contactless radar, alerting clinicians to complications.",
        "Keywords": "post-surgical monitoring,non-invasive,wearable sensors,telehealth,radar",
        "Technologies": "Arduino,BLE,React Native,FastAPI,PostgreSQL", "Algorithms": "Anomaly Detection,Signal Filtering,Risk Scoring",
        "Programming_Languages": "Python,JavaScript", "Frameworks": "FastAPI,React Native", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Patient Monitoring",
        "Title": "Non-Invasive Wearable Patch for Continuous Post-Operative Wound Perfusion Assessment",
        "Abstract": "Flexible epidermal patch measuring tissue oxygenation and blood flow at surgical incision sites via multi-wavelength photoplethysmography (PPG), transmitting data via Bluetooth.",
        "Keywords": "wound perfusion,PPG sensor,wearable patch,tissue oxygenation,post-operative",
        "Technologies": "ESP32,BLE,Flex PCB,Python,PostgreSQL", "Algorithms": "PPG Waveform Analysis,Beer-Lambert Law Calculation",
        "Programming_Languages": "Python,C++", "Frameworks": "FastAPI", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Patient Monitoring",
        "Title": "AI-Enabled Video Plethysmography for Remote Patient Vital Signs Extraction",
        "Abstract": "Contactless heart rate and respiration tracking system analyzing subtle facial skin color fluctuations from standard smartphone video cameras using rPPG algorithms.",
        "Keywords": "rPPG,contactless monitoring,vital signs,video plethysmography,facial analysis",
        "Technologies": "Python,OpenCV,PyTorch,FastAPI", "Algorithms": "rPPG (Remote Photoplethysmography),Fast Fourier Transform (FFT),Bandpass Filtering",
        "Programming_Languages": "Python", "Frameworks": "PyTorch,FastAPI", "Year": "2025"
    },

    # ── 4. AI-Based Pulmonary Disease Severity Assessment from Chest X-rays with Uncertainty Quantification (Topic + 2 Related)
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Radiology",
        "Title": "AI-Based Pulmonary Disease Severity Assessment from Chest X-rays with Uncertainty Quantification",
        "Abstract": "Bayesian neural network classifier estimating pulmonary congestion and effusion severity from chest radiographs, providing pixel-level epistemic uncertainty maps to reduce diagnostic error.",
        "Keywords": "pulmonary disease,chest x-ray,uncertainty quantification,bayesian cnn,radiology",
        "Technologies": "Python,PyTorch,torchvision,Captum", "Algorithms": "Bayesian CNN,Monte Carlo Dropout,Deep Ensembles",
        "Programming_Languages": "Python", "Frameworks": "PyTorch,FastAPI", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Radiology",
        "Title": "Bayesian Convolutional Neural Networks for Probabilistic Pneumothorax Detection",
        "Abstract": "Deep learning system predicting pneumothorax presence from chest X-rays, using MC Dropout to quantify confidence metrics and generate bounding-box anomaly alerts for radiologists.",
        "Keywords": "pneumothorax,probabilistic cnn,uncertainty,chest x-ray,bounding box",
        "Technologies": "Python,PyTorch,OpenCV,PostgreSQL", "Algorithms": "Bayesian CNN,Grad-CAM,Focal Loss",
        "Programming_Languages": "Python", "Frameworks": "PyTorch", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Radiology",
        "Title": "Evidential Deep Learning for Reliable COVID-19 Severity Scoring on Chest Radiographs",
        "Abstract": "Severe lung disease scoring pipeline applying evidential neural networks to quantify data conflict and out-of-distribution uncertainty for pulmonary radiographs.",
        "Keywords": "evidential deep learning,covid-19,severity scoring,uncertainty,radiographs",
        "Technologies": "Python,TensorFlow,Med3D,PostgreSQL", "Algorithms": "Evidential Deep Learning,U-Net Segmentation,ResNet Backbones",
        "Programming_Languages": "Python", "Frameworks": "TensorFlow", "Year": "2025"
    },

    # ── 5. LLVM-Based Object File Obfuscation Framework for Software Protection (Topic + 2 Related)
    {
        "Domain": "Cybersecurity", "Sub_Domain": "Software Security",
        "Title": "LLVM-Based Object File Obfuscation Framework for Software Protection",
        "Abstract": "Custom LLVM compiler pass transforming intermediate representations (IR) to obfuscate control flow, substitute instructions, and insert dummy code, protecting binaries from reverse engineering.",
        "Keywords": "llvm,obfuscation,software protection,compiler pass,reverse engineering",
        "Technologies": "C++,LLVM Clang,CMake,Linux Build Tools", "Algorithms": "Control Flow Flattening,Instruction Substitution,Bogus Control Flow",
        "Programming_Languages": "C++", "Frameworks": "LLVM API", "Year": "2025"
    },
    {
        "Domain": "Cybersecurity", "Sub_Domain": "Software Security",
        "Title": "Control Flow Flattening and Instruction Substitution Compiler Pass in LLVM",
        "Abstract": "Security compiler pass designed to obscure binary logic by converting deep branch trees into a single switch statement nested in a loop, mitigating static analysis attacks.",
        "Keywords": "control flow flattening,instruction substitution,llvm,static analysis",
        "Technologies": "C++,LLVM API,CMake", "Algorithms": "Control Flow Flattening,Basic Block Splitting",
        "Programming_Languages": "C++", "Frameworks": "LLVM API", "Year": "2025"
    },
    {
        "Domain": "Cybersecurity", "Sub_Domain": "Software Security",
        "Title": "Compiler-Level Metadata Stripping and Anti-Debugging Insertion in ELF Binaries",
        "Abstract": "Post-compilation binary optimizer stripping symbol tables, injecting ptrace-based debugger checks, and encrypting constant strings to protect intellectual property.",
        "Keywords": "elf binaries,metadata stripping,anti-debugging,ptrace,string encryption",
        "Technologies": "C,Shell Scripting,Linux Tools", "Algorithms": "Binary Parsing,String Encryption (XOR/AES),Anti-Debugging Logic",
        "Programming_Languages": "C", "Frameworks": "Make", "Year": "2025"
    },

    # ── 6. AI+IoT Based Early Heart Attack Detection System (Topic + 2 Related)
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Wearable Health Monitoring & Cardiac AI",
        "Title": "AI+IoT Based Early Heart Attack Detection System",
        "Abstract": "Smart wearable device streaming single-lead ECG signals to a cloud gateway where lightweight neural network filters classify cardiac rhythm anomalies to flag myocardial infarction.",
        "Keywords": "heart attack detection,ecg classification,wearable sensor,iot,myocardial infarction",
        "Technologies": "Python,ESP32,AD8232 ECG Sensor,MQTT,PostgreSQL", "Algorithms": "CNN-LSTM,Wavelet Transform,Rhythm Anomaly Classification",
        "Programming_Languages": "Python,C++", "Frameworks": "FastAPI,TensorFlow", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Wearable Health Monitoring & Cardiac AI",
        "Title": "Real-Time ECG Anomaly Detection on ESP32 Microcontrollers Using TensorFlow Lite Micro",
        "Abstract": "Ultra-low-power edge classifier running on an ESP32, parsing ECG wave signals to identify premature ventricular contractions (PVCs) and bradycardia directly on-device.",
        "Keywords": "tensorflow lite micro,esp32,edge ai,ecg anomalies,bradycardia",
        "Technologies": "C++,TensorFlow Lite Micro,ESP32,Arduino IDE", "Algorithms": "Quantized 1D CNN,Peak Detection,Signal Preprocessing",
        "Programming_Languages": "C++", "Frameworks": "TensorFlow Lite Micro", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Wearable Health Monitoring & Cardiac AI",
        "Title": "Edge-Computing-Based Myocardial Infarction Predictor with Integrated BLE SOS System",
        "Abstract": "Wearable health monitor measuring ECG and SpO2 at the wrist, running localized random forest models to predict myocardial infarction events and broadcast GPS location via BLE.",
        "Keywords": "wrist wearable,myocardial infarction,gps alert,ble beacon",
        "Technologies": "C++,Nordic nRF52840,Python,Android SDK", "Algorithms": "Random Forest Classifier,BLE Beaconing,GPS Parsing",
        "Programming_Languages": "Python,C++", "Frameworks": "FastAPI", "Year": "2025"
    },

    # ── 7. LOW-COST AI-BASED COLLISION AVOIDANCE AND AUTOMATIC EMERGENCY BRAKING SYSTEM FOR SMART VEHICLES (Topic + 2 Related)
    {
        "Domain": "Automotive Engineering", "Sub_Domain": "Autonomous Vehicles",
        "Title": "Low-Cost AI-Based Collision Avoidance and Automatic Emergency Braking System for Smart Vehicles",
        "Abstract": "Active safety system combining monocular webcam distance estimation with a deep learning obstacle detector to trigger emergency brakes, deployed on a low-cost microcontroller.",
        "Keywords": "collision avoidance,emergency braking,smart vehicles,microcontroller,yolo",
        "Technologies": "Python,Raspberry Pi 4,Arduino,OpenCV,PostgreSQL", "Algorithms": "YOLOv8-nano,Monocular Depth Estimation,Fuzzy Logic Decision Engine",
        "Programming_Languages": "Python,C++", "Frameworks": "PyTorch,FastAPI", "Year": "2025"
    },
    {
        "Domain": "Automotive Engineering", "Sub_Domain": "Autonomous Vehicles",
        "Title": "Stereo-Vision-Based Obstacle Distance Estimation for Low-Speed Electric Vehicles",
        "Abstract": "Deep sensor package mapping 3D terrain and calculating exact distance to pedestrians or vehicles ahead using stereo-camera disparity maps, optimized for electric golf carts.",
        "Keywords": "stereo vision,disparity map,3d point cloud,golf cart safety",
        "Technologies": "Python,OpenCV,Intel RealSense,ROS", "Algorithms": "Stereo Matching (SGBM),3D Point Cloud Projection,Obstacle Segmentation",
        "Programming_Languages": "Python,C++", "Frameworks": "ROS,PyTorch", "Year": "2025"
    },
    {
        "Domain": "Automotive Engineering", "Sub_Domain": "Autonomous Vehicles",
        "Title": "Lightweight YOLO-based Forward Collision Warning System on Raspberry Pi 4",
        "Abstract": "Real-time driving assistant classifying pedestrians, vehicles, and lane markers on a single Raspberry Pi board, warning drivers with audio alerts of imminent forward collisions.",
        "Keywords": "forward collision,yolo,raspberry pi,time to collision,warning system",
        "Technologies": "Python,Raspberry Pi 4,OpenCV,PyTorch", "Algorithms": "YOLOv8 Object Detection,Kalman Filter Tracking,TTC (Time-to-Collision) Calculation",
        "Programming_Languages": "Python", "Frameworks": "PyTorch", "Year": "2025"
    },

    # ── 8. TrackBin Max Smart Garbage Management System (Topic + 2 Related)
    {
        "Domain": "Smart Cities", "Sub_Domain": "Waste Management",
        "Title": "TrackBin Max Smart Garbage Management System",
        "Abstract": "Intelligent municipal waste bin equipped with fill-level sensors, trash volume estimation, automatic lid control, and LoRaWAN communications to schedule optimal collection routes.",
        "Keywords": "smart garbage,waste management,fill-level,lorawan,route optimization",
        "Technologies": "Python,ESP32,Ultrasonic Sensors,LoRaWAN,Node-RED,PostgreSQL", "Algorithms": "Route Optimization (TSP),Fill-Level Forecasting,Anomaly Alerting",
        "Programming_Languages": "Python,C++", "Frameworks": "FastAPI", "Year": "2025"
    },
    {
        "Domain": "Smart Cities", "Sub_Domain": "Waste Management",
        "Title": "IoT Waste Bin Fill-Level Forecasting using ARIMA and LoRaWAN Sensors",
        "Abstract": "Predictive sanitation system forecasting when public waste bins will reach maximum capacity based on historical fill-level logs, reducing waste management truck runs by 25%.",
        "Keywords": "arima forecasting,fill-level,lorawan sensors,sanitation logistics",
        "Technologies": "Python,InfluxDB,LoRaWAN,Grafana", "Algorithms": "ARIMA Time Series Forecasting,Spatial Clustering (DBSCAN)",
        "Programming_Languages": "Python", "Frameworks": "FastAPI,Grafana", "Year": "2025"
    },
    {
        "Domain": "Smart Cities", "Sub_Domain": "Waste Management",
        "Title": "AI-Powered Camera-Equipped Recycle Bin for Automated Waste Material Sorting",
        "Abstract": "Smart sorting bin classifying discarded items (plastic, glass, metal, organic) via computer vision, driving a mechanical sorting arm to segregate materials on the spot.",
        "Keywords": "recycle sorting,mobilenet,mechanical sorter,computer vision",
        "Technologies": "Python,Raspberry Pi,TensorFlow,OpenCV,Servo Motors", "Algorithms": "MobileNetV3 Image Classification,Servo Control Loop",
        "Programming_Languages": "Python", "Frameworks": "TensorFlow", "Year": "2025"
    },

    # ── 9. Bayesian-Constrained Reinforcement Learning (B-CRL) for hallucination pruning (Topic + 2 Related)
    {
        "Domain": "Natural Language Processing", "Sub_Domain": "Generative AI",
        "Title": "Bayesian-Constrained Reinforcement Learning (B-CRL) for Hallucination Pruning",
        "Abstract": "RLHF framework incorporating Bayesian constraint boundaries during fine-tuning of large language models, pruning policy steps that produce low-factuality/hallucinatory tokens.",
        "Keywords": "bayesian-constrained,reinforcement learning,hallucination pruning,llm,factuality",
        "Technologies": "Python,PyTorch,Hugging Face,Ray/RLlib", "Algorithms": "Proximal Policy Optimization (PPO),Bayesian Constraint Evaluation,Kullback-Leibler Divergence Penalty",
        "Programming_Languages": "Python", "Frameworks": "PyTorch,Hugging Face", "Year": "2025"
    },
    {
        "Domain": "Natural Language Processing", "Sub_Domain": "Generative AI",
        "Title": "Constrained Policy Gradient RL for Factuality Tuning in Large Language Models",
        "Abstract": "Optimization algorithm for tuning LLM outputs using Lagrangian multipliers to enforce truthfulness constraints, preventing the generation of unverified statements.",
        "Keywords": "policy gradient,lagrangian constraints,llm factuality,truthfulness",
        "Technologies": "Python,PyTorch,Hugging Face", "Algorithms": "Policy Gradient,Lagrangian Optimization,Reward Modeling",
        "Programming_Languages": "Python", "Frameworks": "PyTorch,Hugging Face", "Year": "2025"
    },
    {
        "Domain": "Natural Language Processing", "Sub_Domain": "Generative AI",
        "Title": "Bayesian Uncertainty-Guided Decoding to Prune Hallucinations in Neural Translation",
        "Abstract": "Decoding framework for machine translation and summarization models that estimates token uncertainty via MC dropout, steering beam search away from high-uncertainty (hallucinated) tokens.",
        "Keywords": "uncertainty decoding,hallucination,neural translation,beam search",
        "Technologies": "Python,PyTorch,Fairseq", "Algorithms": "Beam Search,MC Dropout,Uncertainty Scoring",
        "Programming_Languages": "Python", "Frameworks": "PyTorch", "Year": "2025"
    },

    # ── 10. ADVANCED GREYMATTER SEGMENTATION (Topic + 2 Related)
    {
        "Domain": "Medical Imaging", "Sub_Domain": "Brain MRI Segmentation",
        "Title": "Advanced Gray Matter Segmentation",
        "Abstract": "High-resolution cortical and subcortical gray matter segmentation from brain MRI scans using customized deep convolutional architectures with attention gates.",
        "Keywords": "gray matter segmentation,brain mri,attention gates,unet,cortical segmentation",
        "Technologies": "Python,PyTorch,NiBabel,MONAI,SimpleITK", "Algorithms": "3D U-Net,Attention Mechanisms,Dice Loss",
        "Programming_Languages": "Python", "Frameworks": "PyTorch,MONAI", "Year": "2025"
    },
    {
        "Domain": "Medical Imaging", "Sub_Domain": "Brain MRI Segmentation",
        "Title": "3D U-Net Based Cortical Gray Matter Segmentation in T1-Weighted Brain MRI",
        "Abstract": "Deep learning segmentation pipeline isolating cerebral gray matter from T1-weighted structural MRI scans, evaluating performance on the ADNI dataset.",
        "Keywords": "cortical segmentation,t1-weighted mri,3d unet,adni dataset",
        "Technologies": "Python,PyTorch,NiBabel,CUDA", "Algorithms": "3D U-Net,Deep Supervision,Binary Cross-Entropy",
        "Programming_Languages": "Python", "Frameworks": "PyTorch", "Year": "2025"
    },
    {
        "Domain": "Medical Imaging", "Sub_Domain": "Brain MRI Segmentation",
        "Title": "Graph-Cut and Active Contour Hybrid Approach for Subcortical Structure Segmentation",
        "Abstract": "Unsupervised medical image segmentation model combining graph-cut energy minimization with deformable active contour models to partition subcortical brain structures.",
        "Keywords": "graph-cut,active contour,subcortical structures,brain segmentation",
        "Technologies": "Python,SimpleITK,OpenCV,NumPy", "Algorithms": "Graph-Cut Optimization,Chan-Vese Active Contours,Level Sets",
        "Programming_Languages": "Python", "Frameworks": "Flask", "Year": "2025"
    },

    # ── 11. Quantum Secure Email Client Application (Topic + 2 Related)
    {
        "Domain": "Cybersecurity", "Sub_Domain": "Cryptography",
        "Title": "Quantum Secure Email Client Application",
        "Abstract": "Email desktop client implementing post-quantum cryptographic primitives (ML-KEM and ML-DSA) to encrypt and sign emails, securing communications against future quantum computer attacks.",
        "Keywords": "quantum secure,email client,post-quantum cryptography,crystals-kyber,crystals-dilithium",
        "Technologies": "Python,PyQt6,PyNaCl,liboqs,PostgreSQL", "Algorithms": "CRYSTALS-Kyber,CRYSTALS-Dilithium,AES-256-GCM",
        "Programming_Languages": "Python", "Frameworks": "FastAPI", "Year": "2025"
    },
    {
        "Domain": "Cybersecurity", "Sub_Domain": "Cryptography",
        "Title": "Post-Quantum Cryptography (Kyber & Dilithium) Integrated Secure SMTP Client",
        "Abstract": "Custom SMTP server and client package integrating NIST-approved post-quantum algorithms to secure email header routing and content payloads.",
        "Keywords": "kyber,dilithium,smtp client,nist standards,secure mail",
        "Technologies": "Go,liboqs-go,Docker,PostgreSQL", "Algorithms": "ML-KEM Key Exchange,ML-DSA Signature Verification,RSA Fallback",
        "Programming_Languages": "Go", "Frameworks": "Docker", "Year": "2025"
    },
    {
        "Domain": "Cybersecurity", "Sub_Domain": "Cryptography",
        "Title": "End-to-End Encrypted Messaging Client using Quantum Key Distribution Simulation",
        "Abstract": "Simulated QKD chat application implementing the BB84 protocol for quantum key exchange alongside classic AES-GCM data encryption.",
        "Keywords": "qkd,bb84 protocol,quantum key,messaging client,e2ee",
        "Technologies": "Python,SimulaQron,WebSockets", "Algorithms": "BB84 Protocol,Error Correction (Cascade),Privacy Amplification",
        "Programming_Languages": "Python", "Frameworks": "FastAPI", "Year": "2025"
    },

    # ── 12. Multimodal AI Framework for Dysgraphia Type Identification, Severity Grading, and Virtual Reality- Based Therapy (Topic + 2 Related)
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Rehabilitation & Dysgraphia AI",
        "Title": "Multimodal AI Framework for Dysgraphia Type Identification, Severity Grading, and Virtual Reality-Based Therapy",
        "Abstract": "Diagnostic and therapeutic platform combining digital tablet handwriting kinematics (pressure, tilt, speed) with eye-tracking indicators, matching patients to gamified VR motor exercises.",
        "Keywords": "dysgraphia diagnosis,multimodal ai,vr therapy,handwriting kinematics,rehabilitation",
        "Technologies": "Python,Unity3D,Meta Quest SDK,Wacom Tablet API,PostgreSQL", "Algorithms": "Random Forest Classifier,Dynamic Time Warping (DTW),VR Physics Simulation",
        "Programming_Languages": "Python,C#", "Frameworks": "Unity,FastAPI", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Rehabilitation & Dysgraphia AI",
        "Title": "Tablet-Based Handwriting Kinematics Extraction and ML Model for Dysgraphia Screening",
        "Abstract": "Pediatric screening tool analyzing stroke velocities, air times, and grip pressure patterns from digital stylus writing tasks to identify dysgraphia subtypes.",
        "Keywords": "handwriting kinematics,dysgraphia screening,stylus velocity,stroke features",
        "Technologies": "Python,scikit-learn,React Native,Wacom SDK", "Algorithms": "Support Vector Machine (SVM),Feature Selection,DTW",
        "Programming_Languages": "Python,JavaScript", "Frameworks": "FastAPI,React Native", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Rehabilitation & Dysgraphia AI",
        "Title": "Virtual Reality Fine-Motor Skill Rehabilitation Game for Dysgraphic Children",
        "Abstract": "Gamified VR therapy environment featuring fine-motor coordinate matching, handwriting tracing, and finger-strength exercises with real-time accuracy scoring.",
        "Keywords": "vr game,fine-motor,rehabilitation,hand tracking,dysgraphia",
        "Technologies": "C#,Unity3D,Oculus Interaction SDK,Firebase", "Algorithms": "Hand Tracking (OpenXR),Kinematic Score Formulation",
        "Programming_Languages": "C#", "Frameworks": "Unity,Firebase", "Year": "2025"
    },

    # ── 13. Edge AI Enabled Wearable System with Vibrotactile Feedback for Monitoring Parkinson’s Motor Symptoms (Topic + 2 Related)
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Parkinson's AI & Wearable Sensors",
        "Title": "Edge AI Enabled Wearable System with Vibrotactile Feedback for Monitoring Parkinson's Motor Symptoms",
        "Abstract": "Closed-loop wearable wristband tracking Parkinsonian tremor and rigidity, triggering micro-vibration feedback to suppress freezing of gait episodes on-device.",
        "Keywords": "parkinson's tremor,vibrotactile feedback,wearable wristband,edge ai,freezing of gait",
        "Technologies": "C++,ESP32,IMU Sensor (MPU6050),ERM Vibration Motor,PostgreSQL", "Algorithms": "1D CNN,Peak Frequency Analysis,Threshold Trigger Logic",
        "Programming_Languages": "C++", "Frameworks": "Arduino IDE", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Parkinson's AI & Wearable Sensors",
        "Title": "Wearable Accelerometer-Based Tremor and Gait Anomaly Estimation in Parkinson's Disease",
        "Abstract": "Diagnostic logging wearable that records 3-axis accelerometer signals, running spectral analysis and SVM models to quantify tremor intensity and gait asymmetry for clinical reviews.",
        "Keywords": "gait anomaly,tremor estimation,accelerometer,parkinson's logs",
        "Technologies": "Python,scikit-learn,Raspberry Pi Zero 2W", "Algorithms": "Fast Fourier Transform (FFT),Spectral Entropy,SVM Classifier",
        "Programming_Languages": "Python", "Frameworks": "Scikit-learn", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Parkinson's AI & Wearable Sensors",
        "Title": "Closed-Loop Vibrotactile Stimulation Glove for Freezing of Gait Suppression in PD Patients",
        "Abstract": "Smart glove detecting freezing of gait episodes in real-time, instantly delivering rhythmic vibrotactile pulses to patient fingers to restore normal walking stride.",
        "Keywords": "vibrotactile glove,freezing of gait,rhythmic pulses,closed loop",
        "Technologies": "C++,Arduino Nano BLE Sense,LRA Actuators", "Algorithms": "LSTM Sequence Classifier,Rhythmic Frequency Generation",
        "Programming_Languages": "C++", "Frameworks": "Arduino IDE", "Year": "2025"
    },

    # ── 14. Continual Federated Learning for Adaptive Financial Fraud Detection (Topic + 2 Related)
    {
        "Domain": "Finance & FinTech", "Sub_Domain": "Fraud Detection",
        "Title": "Continual Federated Learning for Adaptive Financial Fraud Detection",
        "Abstract": "Decentralized fraud detection network enabling banks to continually train models on streaming transaction data, preventing catastrophic forgetting of historical fraud profiles.",
        "Keywords": "continual federated learning,fraud detection,catastrophic forgetting,elastic weight consolidation",
        "Technologies": "Python,PyTorch,Flower FL,PostgreSQL,Docker", "Algorithms": "Federated Learning,Elastic Weight Consolidation (EWC),Experience Replay",
        "Programming_Languages": "Python", "Frameworks": "Flower,PyTorch", "Year": "2025"
    },
    {
        "Domain": "Finance & FinTech", "Sub_Domain": "Fraud Detection",
        "Title": "Catastrophic Forgetting Prevention in Federated Credit Card Fraud Detection Models",
        "Abstract": "Continual learning framework deploying regularization-based methods (EWC) to preserve network weights associated with old fraud patterns during local training updates.",
        "Keywords": "catastrophic forgetting,ewc regularization,federated fraud,credit card",
        "Technologies": "Python,PyTorch,scikit-learn", "Algorithms": "Elastic Weight Consolidation,Gradient Episodic Memory (GEM)",
        "Programming_Languages": "Python", "Frameworks": "PyTorch", "Year": "2025"
    },
    {
        "Domain": "Finance & FinTech", "Sub_Domain": "Fraud Detection",
        "Title": "Adversarial Robust Continual Learning for Real-Time Transaction Fraud Auditing",
        "Abstract": "Dynamic transaction auditor adapting to drifting fraud attacks, incorporating adversarial training during continual model updates to withstand obfuscated transaction schemes.",
        "Keywords": "adversarial learning,continual update,fraud auditing,transaction security",
        "Technologies": "Python,PyTorch,FastAPI", "Algorithms": "Continual Learning,Projected Gradient Descent (PGD),Experience Replay",
        "Programming_Languages": "Python", "Frameworks": "PyTorch,FastAPI", "Year": "2025"
    },

    # ── 15. Preliminary Diagnosis of Dermatological Diseases Using Deep Learning (Topic + 2 Related)
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Dermatology",
        "Title": "Preliminary Diagnosis of Dermatological Diseases Using Deep Learning",
        "Abstract": "Mobile screening application classifying skin lesions into 9 diagnostic categories from smartphone photos, leveraging pre-trained vision transformers for high-accuracy triage.",
        "Keywords": "dermatological diagnosis,skin lesion,deep learning,vision transformer,triage app",
        "Technologies": "Python,PyTorch,Hugging Face,Flutter,FastAPI,PostgreSQL", "Algorithms": "Vision Transformer (ViT),Transfer Learning,Top-K Classification",
        "Programming_Languages": "Python,Dart", "Frameworks": "PyTorch,Flutter,FastAPI", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Dermatology",
        "Title": "Mobile Dermatological Screening App Using Vision Transformers Trained on DermNet",
        "Abstract": "Clinical screening app utilizing a lightweight MobileViT model trained on the DermNet dataset to perform offline classification of common skin conditions.",
        "Keywords": "mobilevit,dermnet,offline classification,explainable ai,integrated gradients",
        "Technologies": "Flutter,PyTorch Mobile,Dart,Python", "Algorithms": "MobileViT,Quantization,Explainable AI (Integrated Gradients)",
        "Programming_Languages": "Python,Dart", "Frameworks": "Flutter,PyTorch", "Year": "2025"
    },
    {
        "Domain": "Healthcare & Medical Technology", "Sub_Domain": "Dermatology",
        "Title": "Self-Supervised Representation Learning for Low-Resource Skin Lesion Classification",
        "Abstract": "Contrastive learning framework pre-training vision backbones on unlabeled dermoscopy images to improve malignancy classification performance when labeled training data is highly scarce.",
        "Keywords": "self-supervised,skin lesion,contrastive learning,low resource,simclr",
        "Technologies": "Python,PyTorch,torchvision", "Algorithms": "SimCLR,Transfer Learning,Linear Probing",
        "Programming_Languages": "Python", "Frameworks": "PyTorch", "Year": "2025"
    }
]

def main():
    rows = []
    seen = set()
    with open(MASTER_FILE, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nt = normalize_title(row.get("Title",""))
            seen.add(nt)
            rows.append(row)

    print(f"Loaded {len(rows)} existing rows from master corpus")

    added = 0
    skipped = 0
    for e in NEW_EXPANSIONS:
        nt = normalize_title(e.get("Title",""))
        if nt in seen:
            print(f"  SKIP (dup): {e['Title'][:60]}...")
            skipped += 1
            continue
        
        # Populate defaults
        for col in COLUMNS:
            if col not in e or not e[col]:
                e[col] = DEFAULTS.get(col, "")
        
        seen.add(nt)
        rows.append(e)
        added += 1

    # Re-assign IDs sequentially
    for i, r in enumerate(rows, start=1):
        r["Project_ID"] = f"P{i:06d}"

    # Write back to master corpus file
    with open(MASTER_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter
    dc = Counter(r.get("Domain","?") for r in rows)
    print(f"\n============================================================")
    print(f"Done! Added {added} new entries. Skipped {skipped} duplicates.")
    print(f"New Master Corpus Total: {len(rows)} entries")
    print(f"============================================================")

if __name__ == "__main__":
    main()
