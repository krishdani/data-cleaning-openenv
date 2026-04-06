#!/bin/bash

# Data Cleaning OpenEnv - Complete Setup Guide

echo "🚀 Setting up Data Cleaning OpenEnv environment..."

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment (optional but recommended)
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
fi

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Verify environment
echo "✓ Dependencies installed"

# Check OpenAI API setup
if [ -z "$HF_TOKEN" ]; then
    echo "⚠️  HF_TOKEN not set. Set it before running inference:"
    echo "   export HF_TOKEN='your_token'"
fi

# Create directories
mkdir -p env/__pycache__

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎮 To run Streamlit UI:"
echo "   streamlit run app.py"
echo ""
echo "🤖 To run inference agent:"
echo "   export HF_TOKEN='your_token'"
echo "   python inference.py hard"
echo ""
echo "🐳 To run with Docker:"
echo "   docker build -t data-cleaning-openenv ."
echo "   docker run -p 8501:8501 data-cleaning-openenv"
echo ""
