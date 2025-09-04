# Setup Instructions for Face Recognition System

## Current Status
✅ Project files created  
⏳ Waiting for Xcode Command Line Tools to finish installing  
⏳ Need to add face images  

## Next Steps

### 1. Wait for Xcode Installation
The system is currently installing Xcode Command Line Tools. You should see a progress dialog. Wait for it to complete.

### 2. Test Python Installation
After Xcode installation completes, run:
```bash
python3 --version
```

### 3. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. Add Face Images
Add some face images to the `known_faces/` directory. For quick testing, you can:

- Take a selfie and save it as `your_name.jpg`
- Download a clear photo of a celebrity (for testing) and save as `celebrity_name.jpg`
- Use any clear, front-facing photos you have

**Important**: Name the files with the person's name (e.g., `john_doe.jpg`)

### 5. Run the System
```bash
# Step 1: Encode the faces
python3 encode_faces.py

# Step 2: Start recognition
python3 recognize.py
```

## Quick Test Images
For immediate testing, you can use these types of images:
- Profile photos from social media (for testing only)
- Passport/ID style photos
- Clear selfies
- Professional headshots

Just make sure they are:
- Well-lit
- Front-facing
- Clear and not blurry
- One person per image
- Common formats (.jpg, .png, etc.)
