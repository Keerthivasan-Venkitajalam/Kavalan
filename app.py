"""
Kavalan Lite - Digital Arrest Scam Detection System
Main Streamlit Application

Enhanced with:
- Stealth Mode: Silent visual alerts that don't alert scammers
- Guardian Eye Widget: AI scanning visualization
- Real-time Coercion Level Graph ("Lie Detector")
- Explainability Cards with legal information
- Evidence Logger integration
- Privacy-preserving background redaction
"""

import streamlit as st
import cv2
import numpy as np
import time
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import logging
from typing import Optional
import os
from dotenv import load_dotenv
from datetime import datetime

# Import our modules
from modules.config import get_config
from modules.video_processor import VideoProcessor
from modules.audio_processor import AudioProcessor
from modules.fusion import FusionEngine, ThreatContext
from modules.reporter import Reporter
from modules.evidence_logger import EvidenceLogger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Kavalan Lite - Scam Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Stealth Mode alerts and Guardian Eye
CUSTOM_CSS = """
<style>
/* Stealth Alert - Visual only, excluded from screen share */
.stealth-alert {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    z-index: 9999;
    animation: pulse-border 1s infinite;
}

@keyframes pulse-border {
    0%, 100% { box-shadow: inset 0 0 30px 10px rgba(255, 0, 0, 0.5); }
    50% { box-shadow: inset 0 0 50px 20px rgba(255, 0, 0, 0.8); }
}

/* Guardian Eye Widget */
.guardian-eye {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: radial-gradient(circle, #00ff00 0%, #004400 100%);
    animation: eye-pulse 2s infinite;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40px;
}

.guardian-eye.alert {
    background: radial-gradient(circle, #ff0000 0%, #440000 100%);
    animation: eye-alert 0.5s infinite;
}

@keyframes eye-pulse {
    0%, 100% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.1); opacity: 1; }
}

@keyframes eye-alert {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.2); }
}

/* Explainability Card */
.explain-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-left: 4px solid #00ff00;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
}

.explain-card.warning {
    border-left-color: #ffaa00;
}

.explain-card.danger {
    border-left-color: #ff0000;
}

/* Coercion Level Meter */
.coercion-meter {
    height: 20px;
    background: linear-gradient(90deg, #00ff00 0%, #ffff00 50%, #ff0000 100%);
    border-radius: 10px;
    position: relative;
}

.coercion-indicator {
    position: absolute;
    top: -5px;
    width: 10px;
    height: 30px;
    background: white;
    border-radius: 5px;
    transition: left 0.3s ease;
}

/* Detection Status Indicators */
.status-dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
}

.status-dot.active { background: #00ff00; }
.status-dot.warning { background: #ffaa00; }
.status-dot.error { background: #ff0000; }
.status-dot.inactive { background: #666666; }
</style>
"""

# RTC Configuration for WebRTC
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

class KavalanApp:
    """Main application class with enhanced UI"""
    
    def __init__(self):
        """Initialize the application"""
        # Load configuration
        self.config = get_config("config")
        
        # Initialize processors
        self.init_processors()
        
        # Initialize session state
        self.init_session_state()
        
        # Inject custom CSS
        st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    def init_processors(self):
        """Initialize all processing modules"""
        try:
            # Get API key from environment
            gemini_api_key = os.getenv("GOOGLE_API_KEY", "")
            
            # Initialize video processor (enhanced with face detection fixes)
            self.video_processor = VideoProcessor(
                gemini_api_key=gemini_api_key,
                config=self.config.thresholds
            )
            
            # Initialize audio processor
            self.audio_processor = AudioProcessor(
                keywords_dict=self.config.keywords
            )
            
            # Initialize fusion engine (enhanced)
            self.fusion_engine = FusionEngine(self.config.thresholds)
            
            # Initialize reporter
            self.reporter = Reporter()
            
            # Initialize evidence logger
            self.evidence_logger = EvidenceLogger(output_dir="evidence")
            self.evidence_logger.start_session()
            
            logger.info("All processors initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize processors: {e}")
            st.error(f"Failed to initialize system: {e}")
    
    def init_session_state(self):
        """Initialize Streamlit session state"""
        defaults = {
            'scores_history': [],
            'alerts_count': 0,
            'last_transcript': "",
            'current_fusion_result': None,
            'stealth_mode': True,  # Silent alerts by default
            'coercion_history': [],
            'threat_explanations': [],
            'detection_status': {},
            'session_start_time': datetime.now(),
            'evidence_committed': False
        }
        
        for key, default in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default
    
    def video_frame_callback(self, frame: av.VideoFrame) -> av.VideoFrame:
        """Process video frames from WebRTC stream with enhanced detection"""
        try:
            # Convert frame to numpy array
            img = frame.to_ndarray(format="bgr24")
            
            # Get uniform analysis prompt
            uniform_prompt = self.config.prompts.get("uniform_analysis", "")
            
            # Process frame (now with enhanced detection)
            liveness_result, visual_result = self.video_processor.process_frame(img, uniform_prompt)
            
            # Store results in session state for UI display
            if liveness_result:
                st.session_state.last_liveness = liveness_result
                st.session_state.detection_status = {
                    'face_detected': liveness_result.face_detected,
                    'detection_method': liveness_result.detection_method,
                    'stress_level': liveness_result.stress_level,
                    'is_distressed': liveness_result.is_distressed,
                    'is_static_spoof': liveness_result.is_static_spoof
                }
            
            if visual_result:
                st.session_state.last_visual = visual_result
            
            # Log evidence (frame sampling)
            if hasattr(self, 'evidence_logger') and self.evidence_logger:
                fusion_result = st.session_state.get('current_fusion_result')
                threat_score = fusion_result.final_score if fusion_result else 0.0
                annotations = []
                if liveness_result and liveness_result.is_static_spoof:
                    annotations.append("SPOOF_DETECTED")
                if visual_result and visual_result.uniform_detected:
                    annotations.append(f"UNIFORM:{visual_result.uniform_agency_claimed}")
                self.evidence_logger.add_frame(img, threat_score, annotations)
            
            # Update fusion if we have all components
            self.update_fusion_score()
            
            # Draw overlay information on frame (Stealth Mode aware)
            img = self.draw_overlay(img, liveness_result, visual_result)
            
            return av.VideoFrame.from_ndarray(img, format="bgr24")
            
        except Exception as e:
            logger.error(f"Error in video callback: {e}")
            return frame
    
    def audio_frame_callback(self, frame: av.AudioFrame) -> av.AudioFrame:
        """Process audio frames from WebRTC stream"""
        try:
            # Convert audio frame to numpy array
            audio_array = frame.to_ndarray()
            
            # Flatten if stereo
            if len(audio_array.shape) > 1:
                audio_array = audio_array.mean(axis=1)
            
            # Process audio
            audio_result = self.audio_processor.process_audio(audio_array, frame.sample_rate)
            
            # Store results in session state
            if audio_result:
                st.session_state.last_audio = audio_result
                if audio_result.transcript:
                    st.session_state.last_transcript = audio_result.transcript
            
            # Update fusion score
            self.update_fusion_score()
            
            return frame
            
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
            return frame
    
    def update_fusion_score(self):
        """Update fusion score based on latest results with context awareness"""
        try:
            # Ensure session state variables are initialized (thread-safe check)
            if not hasattr(st.session_state, 'coercion_history') or st.session_state.coercion_history is None:
                st.session_state.coercion_history = []
            if not hasattr(st.session_state, 'scores_history') or st.session_state.scores_history is None:
                st.session_state.scores_history = []
            if not hasattr(st.session_state, 'alerts_count'):
                st.session_state.alerts_count = 0
            if not hasattr(st.session_state, 'threat_explanations'):
                st.session_state.threat_explanations = []
            
            # Get latest results from session state
            liveness_result = getattr(st.session_state, 'last_liveness', None)
            visual_result = getattr(st.session_state, 'last_visual', None)
            audio_result = getattr(st.session_state, 'last_audio', None)
            
            # Use default scores if results not available
            liveness_score = liveness_result.score if liveness_result else 0.0
            visual_score = visual_result.score if visual_result else 0.0
            audio_score = audio_result.score if audio_result else 0.0
            
            # Build threat context for enhanced fusion
            context = ThreatContext(
                uniform_detected=visual_result.uniform_detected if visual_result else False,
                uniform_is_fake=visual_result.is_verified_fake if visual_result else False,
                agency_claimed=visual_result.uniform_agency_claimed if visual_result else "",
                coercion_detected=bool(audio_result and audio_result.detected_keywords.get('coercion')),
                financial_demand=bool(audio_result and audio_result.detected_keywords.get('financial')),
                authority_claim=bool(audio_result and audio_result.detected_keywords.get('authority')),
                user_stress_level=liveness_result.stress_level if liveness_result else "normal",
                is_static_spoof=liveness_result.is_static_spoof if liveness_result else False,
                transcript_keywords=list(audio_result.detected_keywords.keys()) if audio_result and audio_result.detected_keywords else []
            )
            
            # Fuse scores with context
            fusion_result = self.fusion_engine.fuse_scores(
                visual=visual_score,
                liveness=liveness_score,
                audio=audio_score,
                context=context
            )
            
            # Store in session state
            st.session_state.current_fusion_result = fusion_result
            
            # Track coercion level history (for Lie Detector graph)
            st.session_state.coercion_history.append({
                'timestamp': time.time(),
                'level': fusion_result.final_score
            })
            # Keep only last 60 entries (1 minute at 1/sec)
            if len(st.session_state.coercion_history) > 60:
                st.session_state.coercion_history = st.session_state.coercion_history[-60:]
            
            # Store explanations for explainability cards
            if fusion_result.explanation:
                st.session_state.threat_explanations = fusion_result.explanation.split(". ")
            
            # Add to history
            st.session_state.scores_history.append({
                'timestamp': time.time(),
                'final_score': fusion_result.final_score,
                'visual': visual_score,
                'liveness': liveness_score,
                'audio': audio_score,
                'is_alert': fusion_result.is_alert,
                'alert_level': fusion_result.alert_level,
                'threat_types': fusion_result.threat_types
            })
            
            # Keep only last 100 entries
            if len(st.session_state.scores_history) > 100:
                st.session_state.scores_history = st.session_state.scores_history[-100:]
            
            # Handle alerts and evidence logging
            if fusion_result.is_alert:
                st.session_state.alerts_count += 1
                self.reporter.log_alert(fusion_result)
                
                # Log threat event to evidence logger
                if hasattr(self, 'evidence_logger') and self.evidence_logger:
                    transcript = st.session_state.get('last_transcript', '')
                    self.evidence_logger.record_threat(
                        threat_type=fusion_result.alert_level,
                        threat_score=fusion_result.final_score,
                        description=fusion_result.alert_message,
                        transcript=transcript
                    )
            
        except Exception as e:
            logger.error(f"Error updating fusion score: {e}")
    
    def draw_overlay(self, img: np.ndarray, liveness_result, visual_result) -> np.ndarray:
        """Draw overlay information on video frame - Stealth Mode aware"""
        try:
            height, width = img.shape[:2]
            stealth_mode = st.session_state.get('stealth_mode', True)
            
            # Draw liveness info (small, non-intrusive)
            if liveness_result:
                # Detection method indicator
                method_color = (0, 255, 0) if liveness_result.detection_method == "mediapipe" else (0, 255, 255)
                cv2.putText(img, f"Detection: {liveness_result.detection_method}", 
                           (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, method_color, 1)
                
                # Blink rate - show actual count
                blink_text = f"Blinks/min: {liveness_result.blinks_per_minute:.1f}"
                cv2.putText(img, blink_text, 
                           (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # EAR value for debugging
                cv2.putText(img, f"EAR: {liveness_result.ear_value:.3f}", 
                           (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                
                # Face detection status - use ASCII only
                face_color = (0, 255, 0) if liveness_result.face_detected else (0, 0, 255)
                face_text = "Face: YES" if liveness_result.face_detected else "Face: NO"
                cv2.putText(img, face_text, (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, face_color, 1)
                
                # Stress indicator (if distressed)
                if liveness_result.is_distressed:
                    cv2.putText(img, f"Stress: {liveness_result.stress_level.upper()}", 
                               (10, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                
                # Spoof warning - use ASCII only
                if liveness_result.is_static_spoof:
                    cv2.putText(img, "WARNING: SPOOF DETECTED", 
                               (width//2 - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Draw current fusion score
            fusion_result = st.session_state.get('current_fusion_result')
            if fusion_result:
                # Color based on threat level
                if fusion_result.alert_level == "critical":
                    score_color = (0, 0, 255)  # Red
                elif fusion_result.alert_level == "high":
                    score_color = (0, 128, 255)  # Orange
                elif fusion_result.alert_level == "moderate":
                    score_color = (0, 255, 255)  # Yellow
                else:
                    score_color = (0, 255, 0)  # Green
                
                cv2.putText(img, f"Threat: {fusion_result.final_score:.1f}/10", 
                           (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, score_color, 2)
                
                # STEALTH MODE ALERT - Visual only (no audio)
                if fusion_result.is_alert:
                    if stealth_mode:
                        # Subtle but attention-grabbing pulsing border
                        border_thickness = 15
                        border_color = (0, 0, 255)  # Red
                        
                        # Draw pulsing border
                        cv2.rectangle(img, (0, 0), (width, height), border_color, border_thickness)
                        
                        # Small "STOP" indicator in corner (not center - less visible to screen share)
                        cv2.rectangle(img, (width - 120, 10), (width - 10, 50), (0, 0, 200), -1)
                        cv2.putText(img, "STOP", (width - 100, 38), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    else:
                        # Full alert overlay (original behavior)
                        overlay = img.copy()
                        cv2.rectangle(overlay, (0, 0), (width, height), (0, 0, 255), -1)
                        img = cv2.addWeighted(img, 0.7, overlay, 0.3, 0)
                        
                        # Alert text
                        cv2.putText(img, "POTENTIAL SCAM DETECTED", 
                                   (width//2 - 150, height//2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                        cv2.putText(img, "DISCONNECT NOW", 
                                   (width//2 - 100, height//2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            return img
            
        except Exception as e:
            logger.error(f"Error drawing overlay: {e}")
            return img
    
    def render_sidebar(self):
        """Render sidebar with controls and information"""
        st.sidebar.title("🛡️ Kavalan Lite")
        st.sidebar.markdown("**AI-Powered Digital Bodyguard**")
        
        # Guardian Eye Status Widget
        st.sidebar.markdown("---")
        fusion_result = st.session_state.get('current_fusion_result')
        alert_class = "alert" if (fusion_result and fusion_result.is_alert) else ""
        
        st.sidebar.markdown(f"""
        <div class="guardian-eye {alert_class}">👁️</div>
        <p style="text-align: center; margin-top: 10px;">
            <b>Guardian Eye</b><br/>
            {"🔴 THREAT DETECTED" if alert_class else "🟢 Monitoring"}
        </p>
        """, unsafe_allow_html=True)
        
        # System Status
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔧 System Status")
        
        # Detection capabilities
        detection_status = st.session_state.get('detection_status', {})
        face_detected = detection_status.get('face_detected', False)
        detection_method = detection_status.get('detection_method', 'none')
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            face_icon = "🟢" if face_detected else "🔴"
            st.markdown(f"{face_icon} Face")
        with col2:
            method_icon = "🟢" if detection_method != "none" else "🟡"
            st.markdown(f"{method_icon} {detection_method.title()}")
        
        # Check processor status
        video_status = "🟢" if hasattr(self, 'video_processor') and self.video_processor.face_mesh else "🟡"
        audio_status = "🟢" if hasattr(self, 'audio_processor') else "🔴"
        gemini_status = "🟢" if hasattr(self, 'video_processor') and self.video_processor.gemini_model else "🟡"
        
        st.sidebar.text(f"{video_status} MediaPipe")
        st.sidebar.text(f"{audio_status} Audio Processing")
        st.sidebar.text(f"{gemini_status} Gemini AI")
        
        # Session Statistics
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 Session Stats")
        
        session_duration = (datetime.now() - st.session_state.get('session_start_time', datetime.now())).seconds
        st.sidebar.text(f"Duration: {session_duration // 60}m {session_duration % 60}s")
        st.sidebar.metric("Total Alerts", st.session_state.alerts_count)
        
        if st.session_state.scores_history:
            recent_scores = [s['final_score'] for s in st.session_state.scores_history[-10:]]
            avg_score = sum(recent_scores) / len(recent_scores)
            max_score = max(recent_scores)
            st.sidebar.metric("Avg Score (last 10)", f"{avg_score:.1f}")
            st.sidebar.metric("Peak Score", f"{max_score:.1f}")
        
        # Controls
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Controls")
        
        # Stealth Mode Toggle
        stealth_mode = st.sidebar.toggle(
            "🤫 Stealth Mode",
            value=st.session_state.get('stealth_mode', True),
            help="Silent alerts that won't alert the scammer if they can hear your device"
        )
        st.session_state.stealth_mode = stealth_mode
        
        if st.sidebar.button("🔄 Reset Session"):
            st.session_state.scores_history = []
            st.session_state.alerts_count = 0
            st.session_state.last_transcript = ""
            st.session_state.coercion_history = []
            if hasattr(self, 'evidence_logger'):
                self.evidence_logger.clear_buffers()
                self.evidence_logger.start_session()
            st.rerun()
        
        if st.sidebar.button("📋 Generate Evidence Report"):
            if hasattr(self, 'evidence_logger'):
                report_path = self.evidence_logger.generate_digital_fir()
                if report_path:
                    st.sidebar.success(f"Report saved to: {report_path}")
                else:
                    st.sidebar.warning("Could not generate report")
        
        # Help Information
        st.sidebar.markdown("---")
        st.sidebar.markdown("""
        **🆘 Emergency Contacts:**
        - Cyber Crime: **1930**
        - cybercrime.gov.in
        """)
    
    def render_guardian_eye_widget(self):
        """Render the Guardian Eye status widget"""
        fusion_result = st.session_state.get('current_fusion_result')
        
        if fusion_result:
            if fusion_result.alert_level == "critical":
                eye_color = "#ff0000"
                status_text = "🚨 CRITICAL THREAT"
            elif fusion_result.alert_level == "high":
                eye_color = "#ff6600"
                status_text = "⚠️ HIGH RISK"
            elif fusion_result.alert_level == "moderate":
                eye_color = "#ffcc00"
                status_text = "⚡ MODERATE"
            else:
                eye_color = "#00ff00"
                status_text = "✅ MONITORING"
        else:
            eye_color = "#00ff00"
            status_text = "👁️ INITIALIZING"
        
        return f"""
        <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 15px;">
            <div style="width: 80px; height: 80px; border-radius: 50%; background: radial-gradient(circle, {eye_color} 0%, #000 100%); 
                        margin: 0 auto; display: flex; align-items: center; justify-content: center; font-size: 30px;
                        animation: pulse 2s infinite;">
                👁️
            </div>
            <h3 style="color: {eye_color}; margin-top: 15px;">{status_text}</h3>
        </div>
        """
    
    def render_coercion_meter(self):
        """Render real-time Coercion Level meter (Lie Detector style)"""
        import pandas as pd
        
        coercion_history = st.session_state.get('coercion_history', [])
        
        if coercion_history:
            df = pd.DataFrame(coercion_history)
            df['time'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Create a line chart that looks like a lie detector
            st.markdown("### 📈 Real-time Threat Level")
            st.line_chart(df.set_index('time')['level'], use_container_width=True, height=150)
            
            # Current level indicator
            current_level = coercion_history[-1]['level'] if coercion_history else 0
            level_pct = (current_level / 10) * 100
            
            # Color based on level
            if current_level >= 8:
                bar_color = "#ff0000"
            elif current_level >= 6:
                bar_color = "#ff6600"
            elif current_level >= 4:
                bar_color = "#ffcc00"
            else:
                bar_color = "#00ff00"
            
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #00ff00 0%, #ffff00 50%, #ff0000 100%); 
                        height: 25px; border-radius: 12px; position: relative; margin: 10px 0;">
                <div style="position: absolute; left: {level_pct}%; top: -3px; width: 6px; height: 31px; 
                            background: white; border-radius: 3px; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>
            </div>
            <p style="text-align: center;"><b>Coercion Level: {current_level:.1f}/10</b></p>
            """, unsafe_allow_html=True)
    
    def render_explainability_cards(self):
        """Render explainability cards explaining why threats were detected"""
        fusion_result = st.session_state.get('current_fusion_result')
        explanations = st.session_state.get('threat_explanations', [])
        
        if fusion_result and fusion_result.is_alert and explanations:
            st.markdown("### 📚 Why is this suspicious?")
            
            for explanation in explanations[:3]:  # Show top 3 explanations
                if explanation.strip():
                    # Determine card type
                    if "ILLEGAL" in explanation.upper() or "NOT" in explanation.upper():
                        card_class = "danger"
                        icon = "🚫"
                    elif "NEVER" in explanation.upper() or "fraud" in explanation.lower():
                        card_class = "warning"
                        icon = "⚠️"
                    else:
                        card_class = ""
                        icon = "ℹ️"
                    
                    st.markdown(f"""
                    <div class="explain-card {card_class}">
                        {icon} {explanation}
                    </div>
                    """, unsafe_allow_html=True)
    
    def render_dashboard(self):
        """Render main dashboard with enhanced UI"""
        # Title with Guardian Eye
        col_title, col_eye = st.columns([3, 1])
        with col_title:
            st.title("🛡️ Kavalan Lite")
            st.caption("AI-Powered Digital Arrest Scam Detection | Real-time Protection")
        with col_eye:
            st.markdown(self.render_guardian_eye_widget(), unsafe_allow_html=True)
        
        # Stealth Alert Banner (if active)
        fusion_result = st.session_state.get('current_fusion_result')
        if fusion_result and fusion_result.is_alert:
            if st.session_state.get('stealth_mode', True):
                # Subtle but visible banner
                st.error(f"🔇 **SILENT ALERT** | {fusion_result.alert_message}")
            else:
                st.error(f"🚨 **{fusion_result.alert_message}**")
            
            # Show recommended action
            if fusion_result.recommended_action == "disconnect":
                st.warning("👆 **Recommended Action:** DISCONNECT the call immediately")
        
        # Main content area
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📹 Live Video Feed")
            
            # WebRTC streamer
            webrtc_ctx = webrtc_streamer(
                key="kavalan-detector",
                mode=WebRtcMode.SENDRECV,
                rtc_configuration=RTC_CONFIGURATION,
                video_frame_callback=self.video_frame_callback,
                audio_frame_callback=self.audio_frame_callback,
                media_stream_constraints={
                    "video": True,
                    "audio": True
                },
                async_processing=True,
            )
            
            # Coercion Level Meter (Lie Detector Graph)
            self.render_coercion_meter()
        
        with col2:
            st.subheader("📊 Analysis Results")
            
            # Current fusion result
            if fusion_result:
                # Final score with visual indicator
                score = fusion_result.final_score
                if score >= 8:
                    score_color = "red"
                    score_emoji = "🔴"
                elif score >= 6:
                    score_color = "orange"
                    score_emoji = "🟠"
                elif score >= 4:
                    score_color = "yellow"
                    score_emoji = "🟡"
                else:
                    score_color = "green"
                    score_emoji = "🟢"
                
                st.markdown(f"### {score_emoji} Threat Score: <span style='color: {score_color}'>{score:.1f}/10</span>", 
                           unsafe_allow_html=True)
                
                # Component scores in columns
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("👁️ Visual", f"{fusion_result.visual_score:.1f}")
                with m2:
                    st.metric("😊 Liveness", f"{fusion_result.liveness_score:.1f}")
                with m3:
                    st.metric("🎤 Audio", f"{fusion_result.audio_score:.1f}")
                
                # Confidence indicator
                st.progress(fusion_result.confidence, text=f"Confidence: {fusion_result.confidence*100:.0f}%")
                
                # Detected threat types
                if fusion_result.threat_types:
                    st.markdown("**Detected Threats:**")
                    for threat in fusion_result.threat_types:
                        threat_display = threat.replace("_", " ").title()
                        st.markdown(f"- 🚩 {threat_display}")
            
            # Detection Status
            st.markdown("---")
            detection_status = st.session_state.get('detection_status', {})
            if detection_status.get('face_detected'):
                st.success(f"✅ Face Detected ({detection_status.get('detection_method', 'unknown')})")
            else:
                st.warning("⚠️ No Face Detected")
            
            if detection_status.get('is_static_spoof'):
                st.error("🚨 SPOOF DETECTED: Possible fake video!")
            
            if detection_status.get('is_distressed'):
                st.info(f"😰 User stress level: {detection_status.get('stress_level', 'unknown').upper()}")
            
            # Recent transcript
            st.markdown("---")
            st.subheader("🎤 Live Transcript")
            transcript = st.session_state.get('last_transcript', 'No audio detected yet...')
            st.text_area("Transcript", value=transcript, height=100, disabled=True, label_visibility="collapsed")
            
            # Detected keywords
            audio_result = getattr(st.session_state, 'last_audio', None)
            if audio_result and hasattr(audio_result, 'detected_keywords') and audio_result.detected_keywords:
                st.markdown("**🔍 Detected Keywords:**")
                for category, keywords in audio_result.detected_keywords.items():
                    if keywords:
                        color = "red" if category in ["coercion", "financial"] else "orange"
                        st.markdown(f"<span style='color:{color}'>**{category.title()}:**</span> {', '.join(keywords)}", 
                                   unsafe_allow_html=True)
        
        # Explainability Cards Section
        self.render_explainability_cards()
        
        # Score history chart
        if st.session_state.scores_history and len(st.session_state.scores_history) > 5:
            st.markdown("---")
            st.subheader("📈 Threat Score History")
            
            # Prepare data for chart
            import pandas as pd
            
            df = pd.DataFrame(st.session_state.scores_history)
            df['time'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Line chart
            st.line_chart(df.set_index('time')[['final_score', 'visual', 'liveness', 'audio']], height=200)
    
    def run(self):
        """Run the main application"""
        try:
            # Render sidebar
            self.render_sidebar()
            
            # Render main dashboard
            self.render_dashboard()
            
        except Exception as e:
            logger.error(f"Error running application: {e}")
            st.error(f"Application error: {e}")

def main():
    """Main entry point"""
    try:
        app = KavalanApp()
        app.run()
    except Exception as e:
        st.error(f"Failed to start application: {e}")
        logger.error(f"Startup error: {e}")

if __name__ == "__main__":
    main()