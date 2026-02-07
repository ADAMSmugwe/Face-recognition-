#!/bin/bash

# One-time setup: Initialize conda for your shell
echo "🔧 Initializing conda..."
/usr/local/bin/conda init zsh

echo ""
echo "✅ Conda initialized!"
echo ""
echo "⚠️  IMPORTANT: Close this terminal and open a NEW one, then run:"
echo ""
echo "    cd /Users/macbook/face_recognition_system"
echo "    conda activate face_rec"
echo "    python quick_test.py"
echo ""
echo "Or simply run: ./run_quick_test.sh"
echo ""
