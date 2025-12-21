# Kavalan Lite

**Real-time AI-powered Digital Arrest Scam Detection System**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.29+-red.svg)](https://streamlit.io)
[![Google Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange.svg)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Solution Architecture](#solution-architecture)
- [Core Features](#core-features)
- [Technical Implementation](#technical-implementation)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Privacy & Security](#privacy--security)
- [Contributing](#contributing)
- [License](#license)
- [Support Resources](#support-resources)

---

## Overview

Kavalan Lite (derived from "Kavalan," meaning "Guardian" in Tamil) is an intelligent, real-time scam detection system designed to protect individuals from sophisticated "Digital Arrest" fraud schemes. The system employs multimodal AI analysis to monitor video calls and identify fraudulent patterns, providing immediate alerts when suspicious activity is detected.

### Key Capabilities

- **Real-time Multimodal Analysis**: Simultaneous processing of audio, visual, and behavioral signals
- **Intelligent Threat Scoring**: Dynamic risk assessment with configurable thresholds
- **Evidence Collection**: Automated logging and documentation for law enforcement
- **Privacy-First Design**: Local processing with minimal data retention
- **Zero-Configuration Demo Mode**: Operational without external API dependencies

---

## Problem Statement

### The Digital Arrest Scam Crisis

Digital arrest scams represent a growing threat to public safety, particularly in India. Fraudsters impersonate law enforcement officials or government authorities during video calls, falsely claiming that victims are implicated in serious crimes such as money laundering, drug trafficking, or customs violations.

#### Attack Methodology

1. **Initial Contact**: Unsolicited video call from alleged official
2. **Authority Establishment**: Display of fake uniforms, badges, or government insignia
3. **Threat Escalation**: Claims of arrest warrants, FIRs, or legal proceedings
4. **Coercion**: Demands for immediate payment to avoid arrest
5. **Psychological Pressure**: Extended calls (often hours) to induce compliance

#### Impact Statistics

- **Financial Loss**: Over Rs 120 crore reported in 2024
- **Victim Demographics**: Includes professionals, retirees, and educated individuals
- **Average Loss**: Rs 5-50 lakhs per victim
- **Psychological Impact**: Severe trauma and mental health consequences

---

## Solution Architecture

### System Overview

Kavalan Lite employs a three-tier analysis pipeline that processes video call data in real-time:

```
Input Stream → Multimodal Analysis → Threat Assessment → Alert Generation
```

### Analysis Pipeline

```
┌──────────────────────────────────────────────────────────┐
│                  Kavalan Lite Core System                │
│                  (Streamlit + WebRTC)                    │
└───────────────────────┬──────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│    Audio     │ │    Visual    │ │  Liveness    │
│  Analysis    │ │  Analysis    │ │  Detection   │
├──────────────┤ ├──────────────┤ ├──────────────┤
│  • Whisper   │ │  • Gemini    │ │  • MediaPipe │
│  • Keyword   │ │    Vision    │ │  • Facial    │
│    Engine    │ │  • Uniform   │ │    Landmark  │
│  • Urgency   │ │    Detection │ │  • Deepfake  │
│    Detection │ │              │ │    Analysis  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │ Fusion Engine   │
              │ Threat Score    │
              │ Computation     │
              │ (0.0 - 10.0)    │
              └────────┬────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Alert     │ │  Evidence   │ │  Database   │
│   System    │ │   Logger    │ │  Reporter   │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

## Core Features

### 1. Real-time Threat Scoring

The system computes a unified threat score (0.0 - 10.0) by aggregating signals from multiple analysis streams:

- **Audio Score**: Based on keyword frequency, urgency patterns, and threatening language
- **Visual Score**: Derived from uniform detection, insignia analysis, and environment assessment
- **Liveness Score**: Calculated from facial landmarks, motion patterns, and deepfake indicators

**Threat Levels**:
- **0.0 - 3.0**: Safe (Normal conversation)
- **3.0 - 6.0**: Caution (Suspicious elements detected)
- **6.0 - 10.0**: Critical (High probability of scam)

### 2. Intelligent Keyword Detection

The system monitors for five categories of scam-related language patterns:

| Category | Examples | Detection Method |
|----------|----------|-----------------|
| **Legal Threats** | arrest warrant, FIR, NCB, CBI, police custody, court summons | Pattern matching with context analysis |
| **Financial Coercion** | money laundering, hawala, freeze account, transfer funds, penalty | Financial terminology detection |
| **Urgency Tactics** | immediately, right now, don't disconnect, urgent, deadline | Time-pressure language identification |
| **Authority Claims** | senior officer, high court, government order, official investigation | Impersonation indicators |
| **Fear Induction** | jail, criminal case, your family, consequences, arrest | Threat language analysis |

### 3. Visual Intelligence

**Uniform Verification System**:
- Real-time comparison against authentic government uniform databases
- Insignia and badge authentication
- Background environment analysis for official settings

**Deepfake Detection**:
- Facial landmark consistency tracking
- Motion pattern analysis
- Frame integrity verification

### 4. Evidence Collection System

Automated documentation includes:
- Timestamped frame captures of suspicious moments
- Complete audio transcriptions with keyword highlights
- Threat score progression graphs
- Detection event logs with severity classification

All evidence is stored locally and can be exported for law enforcement reporting.

### 5. Stealth Mode Operation

The system provides discreet visual alerts that do not reveal the detection system's presence to potential scammers:
- Silent threat indicators
- Guardian Eye scanning visualization
- Real-time coercion level graphs
- Explainability cards with legal information

---

## Technical Implementation

### Core Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend Framework** | Streamlit | Web-based UI with real-time updates |
| **Video Processing** | WebRTC + OpenCV | Real-time video capture and processing |
| **Audio Transcription** | OpenAI Whisper | Speech-to-text conversion |
| **Visual Analysis** | Google Gemini 2.5 Flash | Computer vision and scene understanding |
| **Facial Analysis** | MediaPipe Face Landmarker | Liveness detection and facial tracking |
| **Data Storage** | SQLite | Local detection logs and evidence storage |
| **Report Generation** | ReportLab | PDF evidence reports |

### Algorithm Overview

**Threat Score Calculation**:

```python
ThreatScore = (AudioScore × W_a + VisualScore × W_v + LivenessScore × W_l) / (W_a + W_v + W_l)

Where:
- W_a = Audio weight (default: 0.4)
- W_v = Visual weight (default: 0.4)  
- W_l = Liveness weight (default: 0.2)
```

**Keyword Scoring Algorithm**:
1. Detect keyword presence in transcription
2. Apply category-specific weights
3. Calculate frequency-based intensity
4. Apply temporal decay for historical detections
5. Normalize to 0-10 scale

---

## Installation

### Prerequisites

- **Python**: Version 3.11 or higher
- **Hardware**: Webcam and microphone
- **Operating System**: Windows, macOS, or Linux

### Method 1: Automated Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/Keerthivasan-Venkitajalam/Kavalan-Lite.git
cd Kavalan-Lite

# Run automated installer
python install_dependencies.py
```

The automated installer handles dependency resolution with proper error handling and fallback options.

### Method 2: Manual Installation

```bash
# Create virtual environment
python -m venv kavalan_env

# Activate environment
# Windows:
kavalan_env\Scripts\activate
# Linux/macOS:
source kavalan_env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Method 3: Minimal Installation

For demonstration purposes without full AI capabilities:

```bash
pip install -r requirements_minimal.txt
```

This installs core dependencies only. The system will operate in mock mode for missing components.

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Google Gemini API Configuration
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: Vertex AI Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1
GEMINI_VISION_MODEL=gemini-2.5-flash
GOOGLE_APPLICATION_CREDENTIALS=config/vertex-ai-credentials.json

# Application Settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
LOG_LEVEL=INFO
```

### Obtaining API Keys

**Google Gemini API**:
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `.env` file as `GOOGLE_API_KEY`

**Optional - Vertex AI**:
1. Create a Google Cloud project
2. Enable Vertex AI API
3. Create service account credentials
4. Download JSON key file to `config/` directory

### Configuration Files

The system uses JSON configuration files for customization:

- **config/scam_keywords.json**: Keyword detection rules and weights
- **config/thresholds.json**: Threat level thresholds and scoring parameters
- **config/uniform_codes.json**: Authentic uniform verification database
- **config/gemini_prompts.json**: AI analysis prompt templates

---

## Usage

### Starting the Application

```bash
streamlit run app.py
```

The application will launch in your default browser at `http://localhost:8501`.

### Interface Overview

**Main Dashboard**:
- **Video Feed**: Real-time camera preview with overlay indicators
- **Threat Meter**: Current threat score with color-coded severity
- **Detection Timeline**: Historical threat score graph
- **Alert Panel**: Active warnings and recommendations
- **Evidence Panel**: Captured frames and transcriptions

**Control Panel**:
- **Start/Stop Detection**: Toggle real-time analysis
- **Demo Mode**: Load pre-recorded scam simulation videos
- **Sensitivity Settings**: Adjust detection thresholds
- **Evidence Export**: Generate reports for authorities

### Demo Mode

To test the system without a live call:

1. Launch the application
2. Navigate to "Demo Mode" in the sidebar
3. Select a demo video:
   - `Realtime Scam.mp4`: Simulated scam call (expect high threat scores)
   - `Realtime.mp4`: Normal conversation (expect low threat scores)
4. Observe real-time analysis and alerts

### Live Detection

1. Grant camera and microphone permissions when prompted
2. Click "Start Detection"
3. Join your video call in another window
4. Monitor the threat meter during the call
5. Follow on-screen recommendations if threats are detected

---

## Testing

### Running Test Suite

```bash
# Run all tests with verbose output
python -m pytest -v

# Run specific test modules
python -m pytest test_audio_properties.py -v
python -m pytest test_visual_analyzer.py -v
python -m pytest test_liveness_properties.py -v
python -m pytest test_fusion_properties.py -v

# Run with coverage report
python -m pytest --cov=modules --cov-report=html
```

### Property-Based Testing

The system includes comprehensive property-based tests using Hypothesis:

- **Audio Module**: Keyword detection accuracy, transcription quality
- **Visual Module**: Uniform recognition, frame analysis consistency
- **Liveness Module**: Facial landmark detection, deepfake resistance
- **Fusion Module**: Score calculation correctness, threshold validation

### Integration Testing

```bash
python -m pytest test_integration.py -v
```

Tests end-to-end workflow from video input to threat detection.

---

## Project Structure

```
Kavalan-Lite/
│
├── app.py                          # Main Streamlit application
├── install_dependencies.py         # Automated installer with error handling
├── requirements.txt                # Full dependency list
├── requirements_minimal.txt        # Core dependencies for demo mode
├── .env                           # Environment configuration (not in repo)
├── .gitignore                     # Git ignore rules
│
├── modules/                        # Core application modules
│   ├── __init__.py
│   ├── audio_processor.py         # Whisper transcription & keyword detection
│   ├── video_processor.py         # Gemini Vision & scene analysis
│   ├── fusion.py                  # Multi-signal threat scoring engine
│   ├── reporter.py                # Database logging and reporting
│   ├── evidence_logger.py         # Evidence capture and export
│   ├── config.py                  # Configuration management
│   ├── gemini_live.py             # Gemini Live API integration
│   └── mcp_contexts.py            # Multi-context processing utilities
│
├── config/                         # Configuration files
│   ├── scam_keywords.json         # Keyword detection rules
│   ├── thresholds.json            # Detection threshold parameters
│   ├── uniform_codes.json         # Uniform verification database
│   └── gemini_prompts.json        # AI analysis prompt templates
│
├── models/                         # Pre-trained model files
│   ├── face_landmarker.task       # MediaPipe face detection model
│   ├── deploy.prototxt            # Face detector architecture
│   └── res10_300x300_ssd_iter_140000.caffemodel  # Face detection weights
│
├── Videos/                         # Demo video files
│   ├── Realtime Scam.mp4         # Scam simulation video
│   └── Realtime.mp4              # Normal conversation video
│
├── evidence/                       # Evidence storage (auto-generated)
│   └── kavalan_YYYYMMDD_HHMMSS/  # Session-specific evidence folders
│
├── demo_output/                    # Demo mode output storage
│
├── test_*.py                      # Test modules (property-based tests)
│
├── README.md                      # This file
├── QUICK_START.md                # Quick start guide
└── LICENSE                        # MIT License

```

---

## Privacy & Security

### Data Protection Principles

1. **Local Processing**: All AI inference occurs on the local machine. Video frames are analyzed in real-time without transmission to external servers (except for Gemini API calls, which are necessary for visual analysis).

2. **Minimal Retention**: Video streams are processed frame-by-frame and immediately discarded. No video recording occurs unless evidence capture is explicitly triggered.

3. **Evidence Opt-in**: Screenshot and audio logging only activates when threat scores exceed configurable thresholds.

4. **Secure Storage**: All evidence is stored locally in encrypted form with restricted file permissions.

5. **Open Source Transparency**: Complete source code is available for security auditing and verification.

### Compliance Considerations

- **GDPR**: Local processing minimizes personal data exposure
- **Data Minimization**: Only threat-relevant data is retained
- **User Control**: Full control over evidence capture and retention
- **Audit Trail**: Complete logging of system decisions for accountability

---

## Contributing

We welcome contributions from the community. Whether you're improving detection algorithms, adding new features, or enhancing documentation, your contribution helps protect more individuals.

### Contribution Guidelines

1. **Fork the Repository**: Create your own fork of the project
2. **Create a Feature Branch**: `git checkout -b feature/EnhancedDetection`
3. **Write Tests**: Add tests for new functionality
4. **Follow Code Style**: Maintain consistency with existing code
5. **Document Changes**: Update relevant documentation
6. **Commit Changes**: Use clear, descriptive commit messages
7. **Push to Branch**: `git push origin feature/EnhancedDetection`
8. **Open Pull Request**: Submit PR with detailed description

### Areas for Contribution

- **Detection Algorithms**: Improve accuracy and reduce false positives
- **Keyword Databases**: Expand scam language pattern libraries
- **Uniform Databases**: Add regional uniform verification data
- **Internationalization**: Support for additional languages
- **Performance Optimization**: Reduce computational requirements
- **UI/UX Enhancements**: Improve user interface and experience

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for complete terms.

---

## Support Resources

### For Scam Victims

If you or someone you know has been targeted by a digital arrest scam:

1. **Do Not Comply**: Legitimate law enforcement never demands money over video calls
2. **End Communication**: You have no legal obligation to continue the call
3. **Preserve Evidence**: Save call logs, screenshots, and transaction details
4. **Report Immediately**:
   - **National Cybercrime Portal**: [https://cybercrime.gov.in](https://cybercrime.gov.in)
   - **Helpline**: 1930 (India)
   - **Local Police**: File FIR at nearest police station

### Technical Support

- **Issues**: Report bugs via [GitHub Issues](https://github.com/Keerthivasan-Venkitajalam/Kavalan-Lite/issues)
- **Discussions**: Join community discussions on GitHub
- **Documentation**: Refer to [QUICK_START.md](QUICK_START.md) for troubleshooting

---

## Acknowledgments

This project leverages cutting-edge technologies from leading organizations:

- **Google Cloud**: Vertex AI and Gemini 2.5 Flash Vision API
- **OpenAI**: Whisper automatic speech recognition
- **Google MediaPipe**: Real-time face landmark detection
- **Streamlit**: Open-source web application framework

Special thanks to the open-source community for tools and libraries that make this project possible.

---

**Kavalan Lite** - Protecting individuals through intelligent technology.

*Built for public safety. Maintained by the community.*
