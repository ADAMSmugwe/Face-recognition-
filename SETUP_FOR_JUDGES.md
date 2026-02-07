# 🎓 Quick Setup Guide for Judges - Kenya Science Fair 2026

## ⏱️ 5-Minute Setup

### For macOS/Linux:

**1. Copy and paste this into Terminal:**
```bash
# Clone the project
git clone https://github.com/ADAMSmugwe/Face-recognition-.git
cd Face-recognition-

# Install dependencies
pip3 install -r requirements.txt

# Run the application
python3 app.py
```

**2. Open your browser:**
```
http://localhost:5001
```

**3. Allow webcam access when prompted**

---

### For Windows:

**1. Copy and paste this into Command Prompt:**
```batch
git clone https://github.com/ADAMSmugwe/Face-recognition-.git
cd Face-recognition-
pip install -r requirements.txt
python app.py
```

**2. Open your browser:**
```
http://localhost:5001
```

**3. Allow webcam access when prompted**

---

## 📋 Prerequisites

**Do you have Python installed?**

Check by running:
```bash
python --version
```

If not installed:
- **Download Python 3.10**: https://www.python.org/downloads/
- During installation, **check "Add Python to PATH"**

**Do you have Git installed?**

Check by running:
```bash
git --version
```

If not installed:
- **macOS**: Already included or install Xcode Command Line Tools
- **Windows**: Download from https://git-scm.com/downloads

---

## 🎬 What You'll See

1. **Dashboard with 4 tabs:**
   - Students (add/manage students)
   - Recognition (live face recognition)
   - Attendance (view records)
   - Settings (voice & system settings)

2. **Live Features:**
   - Real-time face detection
   - Voice announcements (199+ voices)
   - Attendance tracking
   - Multi-student recognition
   - Excel export

---

## 🔧 Troubleshooting

### "pip not found"
```bash
# Use pip3 instead
pip3 install -r requirements.txt
```

### "Permission denied"
```bash
# Use sudo (macOS/Linux)
sudo pip3 install -r requirements.txt
```

### "Webcam not working"
- Check browser permissions (Settings → Privacy → Camera)
- Try Chrome or Firefox
- Ensure no other app is using webcam

### "Port 5001 already in use"
```bash
# Kill the process
lsof -ti:5001 | xargs kill -9

# Or change port in app.py
PORT=5002 python app.py
```

---

## 📞 Contact

**Project by:** Adams Mugwe  
**For:** Kenya Science and Engineering Fair 2026  
**GitHub:** https://github.com/ADAMSmugwe/Face-recognition-

---

## ✅ System Requirements

- **OS**: Windows 10+, macOS 10.14+, Linux
- **Python**: 3.10 or higher
- **RAM**: 4GB minimum (8GB recommended)
- **Webcam**: Any USB or built-in camera
- **Browser**: Chrome, Firefox, or Safari

---

**Enjoy exploring the Face Recognition System! 🚀**
