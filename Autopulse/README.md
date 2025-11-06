# AutoPulse - OBD AI Assistant

AutoPulse is a mobile app that connects to your car's OBD-II system and helps you understand engine error codes in simple human language.  
It also includes an AI analyzer where you can type any OBD code (e.g., **P0300**) and get explanation, causes, and suggested fixes.

Built using:
- Flutter (App UI)
- FastAPI (Backend API for AI Analysis)

---

## 📂 Project Structure
```
Autopulse/
├─ obd_assistant/ (Flutter Frontend)
└─ server/ (FastAPI Backend)
```
---

## ▶️ How to Run the App

### 1) Start the Backend
```
cd server
pip install -r requirements.txt
uvicorn main:app –reload –port 8000
```
Backend will now run on:  
**http://127.0.0.1:8000**

---

### 2) Run the Flutter App
```
cd obd_assistant
flutter pub get
flutter run
```
