#!/bin/bash

# Quick Test Launcher
echo "============================================================"
echo "🎥 FACE RECOGNITION - QUICK TEST"
echo "============================================================"
echo ""
echo "This will open your webcam and recognize your face!"
echo ""
echo "Steps:"
echo "1. Enter your name when asked"
echo "2. Press SPACE to capture 3-5 photos of your face"
echo "3. Press 'q' when done capturing"
echo "4. Face recognition will start automatically"
echo "5. See your name appear on screen!"
echo "6. Press 'q' to exit"
echo ""
echo "============================================================"
echo "Starting in 3 seconds..."
echo "============================================================"
sleep 3

/usr/local/bin/conda run -n face_rec python /Users/macbook/face_recognition_system/quick_test.py
