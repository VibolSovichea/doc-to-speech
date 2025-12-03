#!/bin/bash

# Setup script for Python AI Worker on macOS
echo "🔧 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# echo "📦 Installing system dependencies (Tesseract & Poppler)..."
# brew install tesseract poppler

echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Setup complete. Virtual environment is active."