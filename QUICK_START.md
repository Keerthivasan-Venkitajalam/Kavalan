# 🚀 Kavalan Lite - Quick Start Guide

## Option 1: Automated Installation (Recommended)

```bash
cd "Our App"
python install_dependencies.py
```

This script will install dependencies with proper error handling and fallbacks.

## Option 2: Manual Installation

### Step 1: Install Essential Dependencies
```bash
pip install -r requirements_minimal.txt
```

### Step 2: Install Optional Dependencies (for full functionality)
```bash
# For computer vision (liveness detection)
pip install mediapipe>=0.10.13

# For AI analysis (visual analysis)  
pip install google-generativeai>=0.3.2

# For audio processing (transcription)
pip install torch>=2.0.0 openai-whisper>=20231117
```

## Option 3: Troubleshooting Installation

If you encounter dependency conflicts:

```bash
# Create a fresh virtual environment
python -m venv kavalan_env
kavalan_env\Scripts\activate  # Windows
# source kavalan_env/bin/activate  # Linux/Mac

# Install minimal dependencies
pip install --upgrade pip
pip install streamlit streamlit-webrtc typing-extensions numpy pillow python-dotenv pandas opencv-python-headless
```

## 🏃‍♂️ Running the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 🔧 Configuration

1. **API Key**: Ensure your `.env` file has a valid `GOOGLE_API_KEY` for Gemini
2. **Permissions**: Allow camera and microphone access when prompted
3. **Testing**: Run `python -m pytest` to verify all components work

## 🎯 Mock Mode

The system is designed to work even without optional dependencies:
- **No MediaPipe**: Liveness detection uses mock data
- **No Gemini API**: Visual analysis uses mock responses  
- **No Whisper**: Audio transcription uses mock data

This ensures the app always runs for demonstration purposes.

## 🆘 Common Issues

### "No module named 'typing_extensions'"
```bash
pip install typing-extensions>=4.0.0
```

### "Could not find a version that satisfies the requirement mediapipe==0.10.8"
```bash
pip install mediapipe>=0.10.13  # Use newer version
```

### Streamlit won't start
```bash
pip install --upgrade streamlit streamlit-webrtc
```

## ✅ Verification

After installation, verify everything works:
```bash
python -c "from app import KavalanApp; print('✅ App ready!')"
```