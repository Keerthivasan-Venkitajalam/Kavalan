"""
Kavalan Lite - Digital Arrest Scam Detection System
Main Streamlit Application
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

# Import our modules
from modules.config import get_config
from modules.video_processor import VideoProcessor
from modules.audio_processor import AudioProcessor
from modules.fusion import FusionEngine
from modules.reporter import Reporter

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

# RTC Configuration for WebRTC
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

class KavalanApp:
    """Main application class"""
    
    def __init__(self):
        """Initialize the application"""
        # Load configuration
        self.config = get_config("config")
        
        # Initialize processors
        self.init_processors()
        
        # Initialize session state
        self.init_session_state()
    
    def init_processors(self):
        """Initialize all processing modules"""
        try:
            # Get API key from environment
            gemini_api_key = os.getenv("GOOGLE_API_KEY", "")
            
            # Initialize video processor
            self.video_processor = VideoProcessor(
                gemini_api_key=gemini_api_key,
                config=self.config.thresholds
            )
            
            # Initialize audio processor
            self.audio_processor = AudioProcessor(
                keywords_dict=self.config.keywords
            )
            
            # Initialize fusion engine
            self.fusion_engine = FusionEngine(self.config.thresholds)
            
            # Initialize reporter
            self.reporter = Reporter()
            
            logger.info("All processors initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize processors: {e}")
            st.error(f"Failed to initialize system: {e}")
    
    def init_session_state(self):
        """Initialize Streamlit session state"""
        if 'scores_history' not in st.session_state:
            st.session_state.scores_history = []
        
        if 'alerts_count' not in st.session_state:
            st.session_state.alerts_count = 0
        
        if 'last_transcript' not in st.session_state:
            st.session_state.last_transcript = ""
        
        if 'current_fusion_result' not in st.session_state:
            st.session_state.current_fusion_result = None
    
    def video_frame_callback(self, frame: av.VideoFrame) -> av.VideoFrame:
        """Process video frames from WebRTC stream"""
        try:
            # Convert frame to numpy array
            img = frame.to_ndarray(format="bgr24")
            
            # Get uniform analysis prompt
            uniform_prompt = self.config.prompts.get("uniform_analysis", "")
            
            # Process frame
            liveness_result, visual_result = self.video_processor.process_frame(img, uniform_prompt)
            
            # Store results in session state for UI display
            if liveness_result:
                st.session_state.last_liveness = liveness_result
            
            if visual_result:
                st.session_state.last_visual = visual_result
            
            # Update fusion if we have all components
            self.update_fusion_score()
            
            # Draw overlay information on frame
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
        """Update fusion score based on latest results"""
        try:
            # Get latest results from session state
            liveness_result = getattr(st.session_state, 'last_liveness', None)
            visual_result = getattr(st.session_state, 'last_visual', None)
            audio_result = getattr(st.session_state, 'last_audio', None)
            
            # Use default scores if results not available
            liveness_score = liveness_result.score if liveness_result else 0.0
            visual_score = visual_result.score if visual_result else 0.0
            audio_score = audio_result.score if audio_result else 0.0
            
            # Fuse scores
            fusion_result = self.fusion_engine.fuse_scores(
                visual=visual_score,
                liveness=liveness_score,
                audio=audio_score
            )
            
            # Store in session state
            st.session_state.current_fusion_result = fusion_result
            
            # Add to history
            st.session_state.scores_history.append({
                'timestamp': time.time(),
                'final_score': fusion_result.final_score,
                'visual': visual_score,
                'liveness': liveness_score,
                'audio': audio_score,
                'is_alert': fusion_result.is_alert
            })
            
            # Keep only last 100 entries
            if len(st.session_state.scores_history) > 100:
                st.session_state.scores_history = st.session_state.scores_history[-100:]
            
            # Handle alerts
            if fusion_result.is_alert:
                st.session_state.alerts_count += 1
                self.reporter.log_alert(fusion_result)
            
        except Exception as e:
            logger.error(f"Error updating fusion score: {e}")
    
    def draw_overlay(self, img: np.ndarray, liveness_result, visual_result) -> np.ndarray:
        """Draw overlay information on video frame"""
        try:
            height, width = img.shape[:2]
            
            # Draw liveness info
            if liveness_result:
                # Blink rate
                cv2.putText(img, f"Blinks/min: {liveness_result.blinks_per_minute:.1f}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Face detection
                face_color = (0, 255, 0) if liveness_result.face_detected else (0, 0, 255)
                cv2.putText(img, f"Face: {'Yes' if liveness_result.face_detected else 'No'}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, face_color, 2)
            
            # Draw current fusion score
            fusion_result = st.session_state.get('current_fusion_result')
            if fusion_result:
                score_color = (0, 0, 255) if fusion_result.is_alert else (0, 255, 0)
                cv2.putText(img, f"Threat Score: {fusion_result.final_score:.1f}/10", 
                           (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, score_color, 2)
                
                # Alert overlay
                if fusion_result.is_alert:
                    overlay = img.copy()
                    cv2.rectangle(overlay, (0, 0), (width, height), (0, 0, 255), -1)
                    img = cv2.addWeighted(img, 0.7, overlay, 0.3, 0)
                    
                    # Alert text
                    cv2.putText(img, "⚠️ POTENTIAL SCAM DETECTED ⚠️", 
                               (width//2 - 200, height//2), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
            
            return img
            
        except Exception as e:
            logger.error(f"Error drawing overlay: {e}")
            return img
    
    def render_sidebar(self):
        """Render sidebar with controls and information"""
        st.sidebar.title("🛡️ Kavalan Lite")
        st.sidebar.markdown("**Digital Arrest Scam Detection**")
        
        # System status
        st.sidebar.subheader("System Status")
        
        # Check processor status
        video_status = "✅" if hasattr(self, 'video_processor') else "❌"
        audio_status = "✅" if hasattr(self, 'audio_processor') else "❌"
        fusion_status = "✅" if hasattr(self, 'fusion_engine') else "❌"
        
        st.sidebar.text(f"Video Processor: {video_status}")
        st.sidebar.text(f"Audio Processor: {audio_status}")
        st.sidebar.text(f"Fusion Engine: {fusion_status}")
        
        # Statistics
        st.sidebar.subheader("Session Statistics")
        st.sidebar.metric("Total Alerts", st.session_state.alerts_count)
        
        if st.session_state.scores_history:
            recent_scores = [s['final_score'] for s in st.session_state.scores_history[-10:]]
            avg_score = sum(recent_scores) / len(recent_scores)
            st.sidebar.metric("Avg Score (last 10)", f"{avg_score:.1f}")
        
        # Controls
        st.sidebar.subheader("Controls")
        
        if st.sidebar.button("Reset Session"):
            st.session_state.scores_history = []
            st.session_state.alerts_count = 0
            st.session_state.last_transcript = ""
            st.rerun()
        
        if st.sidebar.button("Clear Transcript Buffer"):
            if hasattr(self, 'audio_processor'):
                self.audio_processor.reset_buffer()
            st.sidebar.success("Buffer cleared!")
    
    def render_dashboard(self):
        """Render main dashboard"""
        # Title
        st.title("🛡️ Kavalan Lite - Real-time Scam Detection")
        
        # Create columns
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
        
        with col2:
            st.subheader("📊 Analysis Results")
            
            # Current fusion result
            fusion_result = st.session_state.get('current_fusion_result')
            if fusion_result:
                # Final score with color coding
                score_color = "red" if fusion_result.is_alert else "green"
                st.markdown(f"### Threat Score: <span style='color: {score_color}'>{fusion_result.final_score:.1f}/10</span>", 
                           unsafe_allow_html=True)
                
                # Component scores
                st.metric("Visual Analysis", f"{fusion_result.visual_score:.1f}/10")
                st.metric("Liveness Detection", f"{fusion_result.liveness_score:.1f}/10")
                st.metric("Audio Analysis", f"{fusion_result.audio_score:.1f}/10")
                
                # Alert status
                if fusion_result.is_alert:
                    st.error(f"🚨 {fusion_result.alert_message}")
                else:
                    st.success("✅ No threats detected")
            
            # Recent transcript
            st.subheader("🎤 Recent Transcript")
            transcript = st.session_state.get('last_transcript', 'No audio detected yet...')
            st.text_area("", value=transcript, height=100, disabled=True)
            
            # Detected keywords
            audio_result = getattr(st.session_state, 'last_audio', None)
            if audio_result and audio_result.detected_keywords:
                st.subheader("🔍 Detected Keywords")
                for category, keywords in audio_result.detected_keywords.items():
                    st.write(f"**{category.title()}:** {', '.join(keywords)}")
        
        # Score history chart
        if st.session_state.scores_history:
            st.subheader("📈 Threat Score History")
            
            # Prepare data for chart
            import pandas as pd
            
            df = pd.DataFrame(st.session_state.scores_history)
            df['time'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Line chart
            st.line_chart(df.set_index('time')[['final_score', 'visual', 'liveness', 'audio']])
    
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