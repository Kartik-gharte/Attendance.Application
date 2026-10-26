# 🎓 AI Attendance System

An AI-powered attendance management system that combines **face recognition, liveness detection, anti-spoofing, and automated attendance verification** to provide a secure and reliable way of marking student attendance.

> 🚧 This project is currently under active development.

---

## 📌 Overview

The AI Attendance System is designed to reduce manual attendance work while improving attendance security.

Instead of traditional attendance methods, the system verifies a student's identity using their face and performs a liveness check before marking attendance.

### Current Verification Flow

```text
Student opens camera
        ↓
Liveness session starts
        ↓
Face detected
        ↓
Blink / liveness verification
        ↓
Anti-spoofing checks
        ↓
Face recognition
        ↓
Compare with registered face
        ↓
Identity verified
        ↓
Attendance marked
✨ Current Features
👤 Face Recognition
Face registration
Face embedding generation
Registered student identification
InsightFace-based face recognition
Face similarity calculation
Student ID-based verification
🛡️ Liveness Detection
Live camera verification
Face landmark detection
Blink-based liveness verification
Session-based liveness flow
Prevention of simple static-image attacks
🔐 Anti-Spoofing
Anti-spoofing service
Integration with attendance verification pipeline
Security checks before attendance approval
📊 Attendance Verification

The system combines multiple verification results:

Liveness + Face Recognition + Anti-Spoofing
                     ↓
             Attendance Decision

A successful verification returns:

Liveness: VERIFIED
Face: MATCH
Attendance: VERIFIED
🗄️ Attendance Database

Currently uses SQLite for storing attendance records.

Stored information includes:

Student ID
Subject
Lecture ID
Attendance date
Attendance time
Liveness status
Face verification status
Similarity score
Attendance status
Creation timestamp
🏗️ Project Structure
ai-service/
│
├── app/
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── liveness_routes.py
│   │   └── routes.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   └── attendance_db.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── anti_spoofing.py
│   │   ├── attendance_verification.py
│   │   ├── face_recognition.py
│   │   ├── liveness.py
│   │   ├── register_face.py
│   │   └── recognize_face.py
│   │
│   ├── utils/
│   │   └── __init__.py
│   │
│   └── main.py
│
├── tests/
│
├── requirements.txt
├── .gitignore
└── README.md
🧠 Technology Stack
Backend
Python
FastAPI
Uvicorn
AI / Computer Vision
InsightFace
MediaPipe
ONNX Runtime
OpenCV
Database
SQLite
Development
Git
GitHub
VS Code
🔌 API Flow
Liveness
POST /liveness/start

Creates a liveness verification session.

POST /liveness/frame

Processes camera frames during the liveness session.

Attendance
POST /attendance/verify

Receives:

Student ID
Session ID
Camera image

and performs the final identity verification.

📈 Verification Result

Example successful response:

{
  "student_id": "STU001",
  "liveness": "VERIFIED",
  "face": "MATCH",
  "similarity": 0.653,
  "attendance": "VERIFIED"
}
🧪 Testing

The project contains multiple service-level tests for:

Face recognition
Face embeddings
Face landmarks
Liveness detection
Attendance verification
Anti-spoofing

Example:

python -m py_compile app\api\routes.py
🔒 Security & Privacy

Face embeddings, local databases, environment variables, images, and model files are intentionally excluded from Git using .gitignore.

The following types of files are not committed:

.env
.venv/
data/
models/
*.npy
*.db
*.sqlite
*.jpg
*.jpeg
*.png
*.exe

This prevents sensitive biometric data and local development files from being uploaded to the repository.

🚧 Roadmap
Phase 1 — Core Attendance
 Face registration
 Face recognition
 Liveness detection
 Blink verification
 Anti-spoofing service
 Attendance verification
 SQLite attendance storage
Phase 2 — Advanced Security
 Unknown face detection
 Multiple face detection
 Improved anti-spoofing
 Attendance session security
 Audit logging
 Suspicious activity detection
Phase 3 — Dashboard & Reports
 Admin dashboard
 Faculty dashboard
 Student dashboard
 Attendance analytics
 Attendance reports
 PDF export
 Excel export
Phase 4 — Production System
 Production database
 Authentication and authorization
 API security
 Deployment
 Production monitoring
 College ERP integration
🎯 Project Goal

The long-term goal is to build a secure AI-based attendance platform capable of:

Face Recognition
       +
Liveness Detection
       +
Anti-Spoofing
       +
Attendance Management
       +
Analytics
       +
Audit & Security

into one unified attendance system.

👨‍💻 Developer

Kartik Gharte

B.Tech —  Computer Science and engg

GitHub: Kartik-gharte

📄 License

This project is currently being developed as an academic and experimental project.
