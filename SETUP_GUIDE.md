# Face Recognition System - Setup Guide

## ✅ What Was Fixed

I've added a complete **Student Management System** (`manage_students.py`) that allows you to:

1. **📋 View all students** - See a list of all registered students
2. **➕ Add new students** - Add students using:
   - Webcam capture (takes multiple photos)
   - Copy from existing folder
3. **🗑️ Delete students** - Remove students and their data
4. **✏️ Rename students** - Change student names
5. **🔄 Re-encode all faces** - Update the face encodings after changes
6. **🎥 Run face recognition** - Launch the recognition system

## 🚨 Python Version Issue

**The face-recognition library is not compatible with Python 3.13!**

### Solution Options:

#### Option 1: Use Python 3.11 or 3.12 (RECOMMENDED)

```bash
# Install Python 3.12 using Homebrew
brew install python@3.12

# Create a new virtual environment with Python 3.12
/usr/local/bin/python3.12 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install opencv-python face-recognition numpy
```

#### Option 2: Use a pre-built binary (if available)

```bash
# Try installing with pre-built wheels
pip install dlib-binary face-recognition opencv-python numpy
```

## 📁 Folder Structure

The system now supports **folder-based organization**:

```
face_recognition_system/
├── images/                    # Student images folder
│   ├── John_Doe/             # Each student has their own folder
│   │   ├── John_Doe_001.jpg
│   │   ├── John_Doe_002.jpg
│   │   └── John_Doe_003.jpg
│   ├── Jane_Smith/
│   │   ├── Jane_Smith_001.jpg
│   │   └── Jane_Smith_002.jpg
│   └── ...
├── encodings/                 # Face encodings (auto-generated)
│   └── known_faces.pkl
├── manage_students.py         # NEW: Student management system
├── encode_faces.py            # Updated: Now supports folders
├── recognize.py               # Face recognition script
└── utils.py                   # Utility functions
```

## 🎯 How to Use the Management System

### Step 1: Setup Python Environment

```bash
# Make sure you're using Python 3.11 or 3.12
python3.12 --version

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install opencv-python face-recognition numpy
```

### Step 2: Run the Management System

```bash
python manage_students.py
```

### Step 3: Add Students

From the menu, select option **2** to add a new student:

**Method 1: Webcam Capture**
- Enter student name
- Choose option 1 (Capture from webcam)
- Press SPACE to capture images (capture 3-5 from different angles)
- Press 'q' when done

**Method 2: Copy from Folder**
- Enter student name
- Choose option 2 (Copy from existing folder)
- Enter the path to a folder containing the student's photos

### Step 4: Re-encode Faces

After adding/deleting/renaming students, select option **5** to regenerate the face encodings.

### Step 5: Run Recognition

Select option **6** or run directly:
```bash
python recognize.py
```

## 🔧 Updated Features

### encode_faces.py
- ✅ Now supports multiple images per student
- ✅ Works with folder-based organization
- ✅ Better error messages
- ✅ Progress indicators

### manage_students.py (NEW)
- ✅ Interactive menu system
- ✅ Webcam capture for adding students
- ✅ Import from existing folders
- ✅ Delete students
- ✅ Rename students
- ✅ Auto re-encoding

## 🎮 Controls

### In Management Menu:
- **1** - View all students
- **2** - Add new student
- **3** - Delete student
- **4** - Rename student
- **5** - Re-encode all faces
- **6** - Run face recognition
- **7** - Exit

### In Webcam Capture:
- **SPACE** - Capture image
- **Q** - Done capturing

### In Recognition Mode:
- **Q** - Quit
- **S** - Save current frame
- **C** - Clear console
- **H** - Toggle help display

## ⚠️ Common Issues

### "ModuleNotFoundError: No module named 'cv2'"
- Install opencv-python: `pip install opencv-python`

### "ModuleNotFoundError: No module named 'face_recognition'"
- Make sure you're using Python 3.11 or 3.12 (NOT 3.13)
- Install face-recognition: `pip install face-recognition`

### "dlib compilation failed"
- This happens with Python 3.13
- Switch to Python 3.12 or 3.11
- Or try: `pip install dlib-binary`

### "No encodings found"
- Run option 5 (Re-encode all faces) from the management menu
- Or run: `python encode_faces.py`

### "Could not open camera"
- Make sure your webcam is not being used by another application
- Check webcam permissions in System Preferences

## 📝 Example Workflow

1. Start the management system: `python manage_students.py`
2. Add a new student (option 2)
3. Capture 3-5 photos from different angles
4. Re-encode faces (option 5)
5. Run face recognition (option 6)
6. The system will now recognize the student!

## 🎓 Tips for Best Results

- Capture at least 3-5 images per student from different angles
- Ensure good lighting
- Look directly at the camera for at least one image
- Avoid blurry images
- One face per image works best

## 📞 Support

If you continue having issues:
1. Check Python version: `python --version` (should be 3.11 or 3.12)
2. Check installed packages: `pip list | grep -E "face|opencv|numpy"`
3. Verify the images folder has student folders with images
4. Run encode_faces.py manually to see detailed error messages
