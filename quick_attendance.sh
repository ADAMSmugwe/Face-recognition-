#!/bin/bash
# Quick Attendance Check - Auto-Close After Verification
# This script runs the attendance verification system

echo "============================================================"
echo "🎓 QUICK ATTENDANCE CHECK - AUTO-CLOSE MODE"
echo "============================================================"
echo ""
echo "Instructions:"
echo "  1. Stand in front of the camera"
echo "  2. Wait for recognition (about 1-2 seconds)"
echo "  3. Window will close automatically after verification"
echo ""
echo "Press Ctrl+C to cancel or wait for startup..."
echo ""

# Set database URL (modify if using PostgreSQL)
export DATABASE_URL="${DATABASE_URL:-sqlite:///faces.db}"

# Activate conda environment if available
if command -v conda &> /dev/null; then
    if conda env list | grep -q "face_rec"; then
        echo "Activating conda environment 'face_rec'..."
        eval "$(conda shell.bash hook)"
        conda activate face_rec
    fi
fi

# Run the quick attendance check
python3 attendance_quick_check.py

# Exit code handling
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ Session complete!"
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo "⚠️  Error occurred (exit code: $EXIT_CODE)"
    echo "============================================================"
fi

exit $EXIT_CODE
