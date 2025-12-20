# 🛡️ Kavalan Lite

**Real-time AI-powered scam call detection to protect citizens from "Digital Arrest" fraud**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![Google Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-orange.svg)](https://cloud.google.com/vertex-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 The Problem We're Solving

**"Digital Arrest" scams** have become a massive crisis in India. Fraudsters impersonate police officers, CBI agents, or government officials on video calls, claiming victims are implicated in crimes like money laundering or drug trafficking. They create a fake sense of urgency, demand immediate payment, and threaten arrest—all while the victim is held hostage on a video call for hours.

**The numbers are staggering:**
- ₹120+ crore lost to digital arrest scams in 2024 alone
- Victims include doctors, engineers, professors, and retired officials
- Average loss per victim: ₹5-50 lakhs
- Many victims suffer severe psychological trauma

**Kavalan Lite fights back.**

---

## 💡 What is Kavalan Lite?

Kavalan (meaning "Guardian" in Tamil) is a browser-based real-time scam detection system that analyzes video calls using multimodal AI. It works silently in the background during any video call and alerts you the moment it detects scam patterns.

### How It Works

```
📹 Video Feed → 🔍 Multimodal Analysis → ⚠️ Real-time Alerts
```

The system performs **three simultaneous analysis streams**:

| Analysis Type | What It Detects | Technology |
|--------------|-----------------|------------|
| 🎙️ **Audio Intelligence** | Scam keywords, threatening language, urgency tactics | OpenAI Whisper + Keyword Engine |
| 👁️ **Visual Analysis** | Fake police uniforms, government insignias, suspicious backgrounds | Google Gemini 2.5 Flash Vision |
| 😰 **Liveness Detection** | Pre-recorded videos, deepfakes, victim stress indicators | MediaPipe Face Landmarker |

---

## ✨ Key Features

### 🔴 Real-time Threat Scoring
A unified threat score (0-10) computed from audio, visual, and behavioral signals. Scores above 6.0 trigger immediate warnings.

### 🎯 Keyword Intelligence
Detects 5 categories of scam language:
- **Legal Threats**: arrest warrant, FIR, NCB, CBI, police custody
- **Financial Pressure**: money laundering, hawala, freeze account, transfer funds
- **Urgency Tactics**: immediately, right now, don't disconnect, urgent
- **Authority Claims**: senior officer, high court, government order
- **Fear Induction**: jail, criminal case, your family, consequences

### 👮 Uniform Verification
AI-powered detection of fake government uniforms with cross-referencing against known insignia patterns.

### 📊 Evidence Logging
Automatic capture of suspicious frames, transcripts, and detection logs for reporting to authorities.

### 🎬 Demo Mode
Built-in demo video player to showcase the system's capabilities without a live call.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Webcam & microphone access
- Google Cloud account (for Gemini Vision API)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Kavalan-Lite.git
cd Kavalan-Lite

# Create conda environment
conda create -n kavalan python=3.11 -y
conda activate kavalan

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Google Cloud credentials
```

### Configuration

Create a `.env` file:
```env
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_LOCATION=us-central1
GEMINI_VISION_MODEL=gemini-2.5-flash
GOOGLE_APPLICATION_CREDENTIALS=config/vertex-ai-credentials.json
```

### Run the App

```bash
streamlit run app.py --server.port 8501
```

Open http://localhost:8501 in your browser.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Kavalan Lite UI                         │
│                    (Streamlit + WebRTC)                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Audio     │   │   Visual    │   │  Liveness   │
│  Processor  │   │  Processor  │   │  Detector   │
│  (Whisper)  │   │  (Gemini)   │   │ (MediaPipe) │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       └────────────────┬┴─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  Fusion Engine  │
              │  (Score: 0-10)  │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │  Alert   │  │ Evidence │  │ Reporter │
   │  System  │  │  Logger  │  │   (DB)   │
   └──────────┘  └──────────┘  └──────────┘
```

---

## 📁 Project Structure

```
Kavalan-Lite/
├── app.py                    # Main Streamlit application
├── modules/
│   ├── audio_processor.py    # Whisper-based transcription & keyword detection
│   ├── video_processor.py    # Gemini Vision & MediaPipe analysis
│   ├── fusion.py             # Multi-signal threat scoring
│   ├── reporter.py           # Database & logging
│   └── evidence_logger.py    # Frame & transcript capture
├── config/
│   ├── scam_keywords.json    # Keyword detection rules
│   ├── thresholds.json       # Scoring thresholds
│   └── uniform_codes.json    # Uniform verification data
├── models/
│   ├── face_landmarker.task  # MediaPipe face model
│   └── *.caffemodel          # Face detection model
├── Videos/                   # Demo video files
└── database/                 # SQLite detection logs
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Run specific test suites
python -m pytest test_audio_properties.py -v
python -m pytest test_visual_analyzer.py -v
python -m pytest test_liveness_properties.py -v
```

---

## 🎬 Demo Videos

The system includes pre-recorded demo videos to showcase detection capabilities:

| Video | Type | Expected Detection |
|-------|------|-------------------|
| `Realtime Scam.mp4` | Scam simulation | High threat score, keyword alerts |
| `Realtime.mp4` | Normal conversation | Low threat score, safe |

---

## 🔒 Privacy & Security

- **Local Processing**: All AI inference runs locally—no video data is sent to external servers
- **No Recording by Default**: Video streams are analyzed in real-time and discarded
- **Evidence Opt-in**: Screenshot capture only activates when threats are detected
- **Open Source**: Full code transparency for security auditing

---

## 🤝 Contributing

We welcome contributions! Whether it's adding new scam keyword patterns, improving detection accuracy, or enhancing the UI—every contribution helps protect more people.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Cloud** for Vertex AI and Gemini Vision API
- **OpenAI** for Whisper speech recognition
- **MediaPipe** for real-time face landmark detection
- **Streamlit** for the amazing web framework

---

## 🆘 Support

If you or someone you know has been a victim of a digital arrest scam:

1. **Do not pay anything** - Real police never demand money over video calls
2. **Disconnect the call** - You are not under any legal obligation to stay
3. **Report to Cyber Crime**: https://cybercrime.gov.in or call 1930
4. **File an FIR** at your local police station

---

<p align="center">
  <b>Built with ❤️ for India's safety</b><br>
  <i>Protecting citizens, one call at a time</i>
</p>
