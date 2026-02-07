#!/bin/bash

# Face Recognition Dashboard Launcher
echo "============================================================"
echo "🎓 FACE RECOGNITION WEB DASHBOARD"
echo "============================================================"
echo ""
echo "Starting the web server..."
echo ""

cd /Users/macbook/face_recognition_system
/usr/local/bin/conda run --no-capture-output -n face_rec python app.py
