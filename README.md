# Face Recognition System

A comprehensive Python-based face recognition system that can identify known individuals in real-time using a webcam. The system uses OpenCV for video processing and the `face_recognition` library for face detection and encoding.

## Features

- **Face Encoding**: Process a folder of known face images and create encodings
- **Real-time Recognition**: Identify faces from webcam feed in real-time
- **Bounding Boxes**: Draw boxes around detected faces with names and confidence scores
- **Performance Optimized**: Configurable processing models (HOG/CNN) and frame skipping
- **Screenshot Capture**: Save screenshots during recognition
- **Robust Error Handling**: Comprehensive validation and error reporting
- **Database Backend**: Store encodings in SQLite or PostgreSQL via SQLAlchemy
- **Web Uploader**: Upload photos via a simple Flask app to add faces to the DB
- **In-app Enrollment**: Press 'a' in recognizer to enroll and save to DB
- **Auto-refresh**: Recognizer periodically reloads encodings while running

## Project Structure

```
Face recognition/
├── encode_faces.py          # Script to encode known faces
├── recognize.py             # Real-time face recognition script
├── utils.py                 # Utility functions and helpers
├── requirements.txt         # Python dependencies
├── known_faces/             # Directory for known face images
│   └── README.txt          # Instructions for adding face images
├── encodings/              # Directory for storing face encodings
└── README.md               # This file
```

## Installation

1. **Clone or download** this project to your local machine

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **System Dependencies** (if needed):
   - **macOS**: `brew install cmake`
   - **Ubuntu/Debian**: `sudo apt-get install cmake libopenblas-dev liblapack-dev`
   - **Windows**: Install Visual Studio Build Tools

## Quick Start

### Step 1: Add Known Face Images

1. Place face images in the `known_faces/` directory
2. Name files with the person's name (e.g., `john_doe.jpg`, `jane_smith.png`)
3. Use clear, well-lit, front-facing photos
4. Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`

### Step 2: Encode Known Faces

Run the encoding script to process your images:

```bash
python encode_faces.py
```

This will:
- Process all images in `known_faces/`
- Extract face encodings
- Save encodings to `encodings/face_encodings.pkl`

### Step 3: Start Face Recognition

Run the recognition script:

```bash
python recognize.py
```

Controls:
- **'q'** or **ESC**: Quit the application
- **'s'**: Save a screenshot
- **'a'**: Enroll a new face (type name; auto-captures samples and saves)
## Database-backed Workflow

Use a database for scalable storage of encodings (SQLite for local, PostgreSQL for production).

SQLite (default local testing):
```bash
# Encode all images in known_faces/ into SQLite DB
python encode_faces.py --use-db --db-url "sqlite:///data/faces.db"

# Run recognition from DB (auto-refresh every 5s)
python recognize.py --use-db --db-url "sqlite:///data/faces.db" --refresh-interval 5

# List faces in DB
python list_faces.py --db-url "sqlite:///data/faces.db"
```

PostgreSQL (example):
```bash
python encode_faces.py --use-db --db-url "postgresql+psycopg2://USER:PASS@HOST:5432/face_db"
python recognize.py --use-db --db-url "postgresql+psycopg2://USER:PASS@HOST:5432/face_db" --refresh-interval 5
python list_faces.py --db-url "postgresql+psycopg2://USER:PASS@HOST:5432/face_db"
```

## Web Uploader

Run a simple web app to upload face photos and save them directly to the database.

```bash
python uploader.py
# Open http://127.0.0.1:5000 → Upload Face
```

Set a custom DB URL:
```bash
DB_URL="postgresql+psycopg2://USER:PASS@HOST:5432/face_db" python uploader.py
```

Uploaded images are encoded on the server and written to the `faces` table.


## Advanced Usage

### Encoding Options

```bash
# Use different input directory
python encode_faces.py --input my_faces/

# Use CNN model for better accuracy (requires GPU)
python encode_faces.py --model cnn

# Save encodings to custom location
python encode_faces.py --output my_encodings.pkl
```

### Recognition Options

```bash
# Use different camera (if multiple cameras available)
python recognize.py --camera 1

# Adjust recognition tolerance (lower = more strict)
python recognize.py --tolerance 0.5

# Use CNN model for better accuracy
python recognize.py --model cnn

# Use custom encodings file
python recognize.py --encodings my_encodings.pkl
```

### Performance Tuning

- **HOG Model**: Faster, CPU-friendly (default)
- **CNN Model**: More accurate, requires GPU
- **Tolerance**: 0.4-0.6 for strict matching, 0.6-0.8 for loose matching
- **Frame Processing**: System processes every other frame for better performance

## API Reference

### Core Classes

#### `FaceEncoder`
Handles processing known face images and creating encodings.

```python
encoder = FaceEncoder(
    input_dir="known_faces",
    output_file="encodings/face_encodings.pkl",
    model="hog"
)
encoder.run()
```

#### `FaceRecognizer`
Handles real-time face recognition from webcam.

```python
recognizer = FaceRecognizer(
    encodings_file="encodings/face_encodings.pkl",
    model="hog",
    tolerance=0.6
)
recognizer.run(camera_index=0)
```

### Utility Functions

Key functions in `utils.py`:

- `load_image_safely()`: Safe image loading with error handling
- `get_face_encodings_from_image()`: Extract face encodings from image
- `draw_face_box()`: Draw bounding boxes with labels
- `save_encodings()` / `load_encodings()`: Pickle file operations

## Scalability Improvements

### 1. Database Storage

Replace pickle files with a proper database:

```python
# Example with SQLite
import sqlite3

class FaceDatabase:
    def __init__(self, db_path="faces.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                encoding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def add_face(self, name, encoding):
        encoding_blob = encoding.tobytes()
        self.conn.execute(
            "INSERT INTO faces (name, encoding) VALUES (?, ?)",
            (name, encoding_blob)
        )
        self.conn.commit()
```

### 2. Web Interface

Create a web-based interface using Flask:

```python
from flask import Flask, render_template, request, jsonify
import cv2
import base64

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recognize', methods=['POST'])
def recognize_face():
    # Process uploaded image or webcam frame
    # Return recognition results as JSON
    pass

@app.route('/add_person', methods=['POST'])
def add_person():
    # Add new person to database
    pass
```

### 3. REST API

Build a REST API for integration with other systems:

```python
from flask_restful import Api, Resource

class FaceRecognitionAPI(Resource):
    def post(self):
        # Accept image data, return recognition results
        pass

class PersonManagementAPI(Resource):
    def get(self, person_id=None):
        # Get person information
        pass
    
    def post(self):
        # Add new person
        pass
    
    def delete(self, person_id):
        # Remove person
        pass
```

### 4. Distributed Processing

For high-volume scenarios, implement distributed processing:

```python
import redis
from celery import Celery

# Use Redis for job queue
app = Celery('face_recognition', broker='redis://localhost:6379')

@app.task
def process_face_recognition(image_data):
    # Process face recognition in background
    pass

@app.task
def batch_encode_faces(image_paths):
    # Process multiple face encodings in parallel
    pass
```

### 5. Cloud Storage Integration

Integrate with cloud storage services:

```python
import boto3

class CloudFaceStorage:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bucket = 'face-recognition-images'
    
    def upload_face_image(self, image_path, person_name):
        key = f"faces/{person_name}/{os.path.basename(image_path)}"
        self.s3.upload_file(image_path, self.bucket, key)
    
    def download_face_images(self, person_name):
        # Download all images for a person
        pass
```

### 6. Real-time Streaming

For multiple camera streams:

```python
import threading
from queue import Queue

class MultiCameraRecognizer:
    def __init__(self, camera_indices):
        self.cameras = camera_indices
        self.frame_queues = {i: Queue() for i in camera_indices}
        
    def start_camera_threads(self):
        for camera_idx in self.cameras:
            thread = threading.Thread(
                target=self.camera_worker, 
                args=(camera_idx,)
            )
            thread.daemon = True
            thread.start()
```

### 7. Performance Monitoring

Add monitoring and analytics:

```python
import time
import logging
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def record_processing_time(self, operation, duration):
        self.metrics[operation].append(duration)
    
    def get_average_time(self, operation):
        times = self.metrics[operation]
        return sum(times) / len(times) if times else 0
```

## Troubleshooting

### Common Issues

1. **Camera not detected**:
   - Check camera permissions
   - Try different camera indices (0, 1, 2...)
   - Ensure camera is not used by another application

2. **No faces detected**:
   - Ensure good lighting
   - Check image quality
   - Try different detection model (hog vs cnn)

3. **Poor recognition accuracy**:
   - Use higher quality training images
   - Add more images per person
   - Adjust tolerance parameter
   - Use CNN model for better accuracy

4. **Performance issues**:
   - Use HOG model for faster processing
   - Reduce video resolution
   - Process fewer frames per second

### System Requirements

- **Python**: 3.7 or higher
- **RAM**: 4GB minimum (8GB recommended)
- **CPU**: Multi-core processor recommended
- **GPU**: Optional (for CNN model)
- **Camera**: USB webcam or built-in camera

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments

- [face_recognition](https://github.com/ageitgey/face_recognition) library by Adam Geitgey
- [OpenCV](https://opencv.org/) for computer vision capabilities
- [dlib](http://dlib.net/) for machine learning algorithms

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review existing issues on GitHub
3. Create a new issue with detailed information

---

**Note**: This system is designed for educational and development purposes. For production use, consider additional security measures, privacy compliance, and performance optimizations.

## Attendance Register (New)

This project now includes a class Attendance Register built on top of the face recognition system.

- Students and attendance are stored in the database (SQLite by default; PostgreSQL supported)
- Real-time attendance marking: recognized students are marked Present once per day
- Absent list: a daily finalize step marks all not-seen students as Absent
- Web dashboard to view/download attendance

### Quick Start (Attendance)

1) Start the web UI and upload students:
```bash
python3 uploader.py
# Open http://127.0.0.1:5000/upload
# Enter Name, optional Student ID, check "Save as Student", choose face photo, submit
```

2) Run attendance-mode recognition (marks Present in real time):
```bash
python3 recognize.py --db-url "sqlite:///data/faces.db" --attendance-mode --refresh-interval 5
```

3) View attendance (filter and export):
```text
http://127.0.0.1:5000/attendance
```
Click "Download CSV" to export for a date range.

4) Finalize Absent list (end of day):
```bash
python3 finalize_attendance.py --db-url "sqlite:///data/faces.db" --date YYYY-MM-DD
```

Optional scheduled finalize via Celery Beat (daily):
```bash
# Requirements: Redis running (redis-server)
celery -A celery_app.celery worker --loglevel=INFO
celery -A celery_app.celery beat --loglevel=INFO
# Configure run time with env vars FINALIZE_HOUR and FINALIZE_MINUTE
```

### Convert existing Faces to Students

If you previously uploaded faces (Faces table) and want to use attendance-mode immediately:
```bash
python3 migrate_faces_to_students.py --db-url "sqlite:///data/faces.db"
```

### Web Uploader (Student mode)

On the Upload page, you can save directly as Students by:
- Checking "Save as Student" and optionally providing a Student ID (auto-generated if omitted)

### Multi-camera Recognition

Run with multiple webcams:
```bash
python3 multi_recognize.py --cameras 0 1 --db-url "sqlite:///data/faces.db" --refresh-interval 5 --tolerance 0.6 --model hog
```

### REST API (selected)

- Health: `GET /api/health`
- Metrics: `GET /api/metrics`
- Recognize: `POST /api/recognize` (multipart `file` or JSON `{image_b64}`; optional `tolerance`)
- Faces: `GET /api/faces`, `GET /api/faces/<id>`, `POST /api/faces`, `DELETE /api/faces/<id>`
- Attendance: `GET /api/attendance?start=YYYY-MM-DD&end=YYYY-MM-DD`, `GET /api/attendance.csv?...`
- Jobs (async, requires Celery/Redis): `POST /api/jobs/batch_encode`, `POST /api/jobs/recognize`, `GET /api/jobs/<task_id>`, `POST /api/jobs/finalize_absentees`

### Cloud Storage (optional)

If you set `S3_BUCKET`, uploaded images are saved to S3 and the DB stores the `s3://bucket/key` path. Presigned URLs can be fetched via `GET /api/faces/<id>/presigned`.

### Configuration Summary

- Database URL: `--db-url` flags or `DB_URL` env for web app
- Attendance finalize schedule: `FINALIZE_HOUR`, `FINALIZE_MINUTE`
- S3: `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
