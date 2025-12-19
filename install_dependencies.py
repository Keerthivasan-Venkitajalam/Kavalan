#!/usr/bin/env python3
"""
Kavalan Lite - Dependency Installation Script
Handles installation of all required dependencies with proper error handling
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def install_dependencies():
    """Install all dependencies for Kavalan Lite"""
    print("🛡️ Kavalan Lite - Installing Dependencies")
    print("=" * 50)
    
    # Update pip first
    if not run_command("python -m pip install --upgrade pip", "Updating pip"):
        print("⚠️ Pip update failed, continuing anyway...")
    
    # Install core dependencies first
    core_deps = [
        "typing-extensions>=4.0.0",
        "numpy>=1.24.0", 
        "pillow>=10.0.0",
        "python-dotenv>=1.0.0",
        "pandas>=2.0.0"
    ]
    
    for dep in core_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep.split('>=')[0]}"):
            print(f"⚠️ Failed to install {dep}, continuing...")
    
    # Install Streamlit and WebRTC
    streamlit_deps = [
        "streamlit>=1.29.0",
        "streamlit-webrtc>=0.47.1"
    ]
    
    for dep in streamlit_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep.split('>=')[0]}"):
            print(f"❌ Critical dependency {dep} failed to install")
            return False
    
    # Install computer vision dependencies
    cv_deps = [
        "opencv-python-headless>=4.8.0",
        "mediapipe>=0.10.13"
    ]
    
    for dep in cv_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep.split('>=')[0]}"):
            print(f"⚠️ {dep} failed - liveness detection will use mock mode")
    
    # Install AI dependencies
    ai_deps = [
        "google-generativeai>=0.3.2"
    ]
    
    for dep in ai_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep.split('>=')[0]}"):
            print(f"⚠️ {dep} failed - visual analysis will use mock mode")
    
    # Install testing dependencies
    test_deps = [
        "pytest>=7.4.0",
        "hypothesis>=6.88.0"
    ]
    
    for dep in test_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep.split('>=')[0]}"):
            print(f"⚠️ {dep} failed - testing may not work")
    
    # Install audio dependencies (optional)
    print("\n🎵 Installing audio dependencies (optional)...")
    audio_deps = [
        "torch>=2.0.0",
        "torchvision>=0.15.0", 
        "openai-whisper>=20231117"
    ]
    
    for dep in audio_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep.split('>=')[0]}"):
            print(f"⚠️ {dep} failed - audio analysis will use mock mode")
    
    print("\n" + "=" * 50)
    print("🎉 Installation completed!")
    print("\n📋 Next steps:")
    print("1. Ensure your .env file has a valid GOOGLE_API_KEY")
    print("2. Run: streamlit run app.py")
    print("3. Open your browser to the displayed URL")
    
    return True

if __name__ == "__main__":
    try:
        install_dependencies()
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)