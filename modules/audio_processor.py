"""
Audio Processor module for Kavalan Lite
Handles audio transcription and keyword matching for scam detection

Uses OpenAI Whisper for transcription (offline, no API needed)
Optimized for faster processing with smaller audio chunks
"""

import numpy as np
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import re
import os
import time
import threading
import queue

logger = logging.getLogger(__name__)

# Try to import Whisper
WHISPER_AVAILABLE = False
try:
    import whisper
    WHISPER_AVAILABLE = True
    logger.info("OpenAI Whisper available for transcription")
except ImportError:
    whisper = None
    logger.warning("whisper not installed - audio transcription disabled")


@dataclass
class AudioResult:
    """Result from audio analysis"""
    score: float  # 0-10 (higher = more suspicious)
    transcript: str
    detected_keywords: Dict[str, List[str]]  # category -> keywords
    threat_level: str  # "low", "medium", "high", "critical"
    confidence: float
    is_final: bool = True  # Always True for Whisper (batch processing)


class AudioProcessor:
    """
    Processes audio for transcription and keyword matching
    
    Uses OpenAI Whisper for transcription (runs locally, no API needed)
    """
    
    def __init__(self, keywords_path: str = None, keywords_dict: Dict = None):
        """
        Initialize audio processor
        
        Args:
            keywords_path: Path to JSON file with scam keywords
            keywords_dict: Direct dictionary of keywords (alternative to file)
        """
        # Load keywords
        self.keywords = {}
        if keywords_dict:
            self.keywords = keywords_dict
        elif keywords_path:
            try:
                with open(keywords_path, 'r', encoding='utf-8') as f:
                    self.keywords = json.load(f)
                logger.info(f"Loaded keywords from {keywords_path}")
            except Exception as e:
                logger.error(f"Failed to load keywords: {e}")
                self.keywords = self._get_default_keywords()
        else:
            self.keywords = self._get_default_keywords()
        
        # Initialize Whisper model
        self.whisper_model = None
        self.model_size = "tiny"  # tiny, base, small, medium, large
        
        if WHISPER_AVAILABLE:
            try:
                # Use tiny model for speed (can upgrade to "base" for better accuracy)
                self.whisper_model = whisper.load_model(self.model_size)
                logger.info(f"Whisper model '{self.model_size}' loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
        
        # Transcript buffer for continuous processing
        self.transcript_buffer = ""
        self.full_transcript = ""
        self._last_process_time = 0
        
        # Background processing queue
        self._audio_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._processing_thread = None
        self._stop_processing = False
        
        logger.info(f"AudioProcessor initialized with {len(self.keywords)} keyword categories")
        logger.info(f"Whisper available: {WHISPER_AVAILABLE}")
    
    def _get_default_keywords(self) -> Dict[str, List[str]]:
        """Get default scam keywords for Digital Arrest scams"""
        return {
            "authority_impersonation": [
                "CBI", "NCB", "ED", "Enforcement Directorate", "Central Bureau",
                "Police", "Court", "Judge", "Magistrate", "Commissioner",
                "Cyber Cell", "Crime Branch", "IPS", "Inspector", "Officer",
                "Government", "Ministry", "Department", "Customs", "Income Tax"
            ],
            "fake_legal_threats": [
                "Digital Arrest", "arrest warrant", "FIR", "case registered",
                "money laundering", "NDPS", "narcotics", "drug trafficking",
                "hawala", "terror funding", "PMLA", "court order", "summons",
                "criminal case", "investigation", "interrogation", "custody"
            ],
            "coercion_isolation": [
                "do not disconnect", "stay on call", "don't tell anyone",
                "keep this confidential", "don't inform family",
                "remain on video", "we are watching", "under surveillance",
                "do not move", "stay where you are", "keep camera on"
            ],
            "financial_demands": [
                "transfer money", "verification account", "safe account",
                "refundable deposit", "security amount", "clear your name",
                "pay fine", "settlement amount", "RBI account", "bank transfer",
                "UPI", "NEFT", "RTGS", "cryptocurrency", "bitcoin"
            ],
            "urgency_pressure": [
                "immediate arrest", "within 24 hours", "right now",
                "last chance", "final warning", "time is running out",
                "officers on the way", "raid your house", "immediately",
                "urgent", "emergency", "deadline", "no time"
            ]
        }
    
    def start_streaming(self) -> bool:
        """Start background processing thread"""
        if self._processing_thread is not None and self._processing_thread.is_alive():
            return True
        
        self._stop_processing = False
        self._processing_thread = threading.Thread(target=self._background_processor, daemon=True)
        self._processing_thread.start()
        logger.info("Audio background processing started")
        return True
    
    def stop_streaming(self):
        """Stop background processing thread"""
        self._stop_processing = True
        if self._processing_thread:
            self._processing_thread.join(timeout=2)
        logger.info("Audio background processing stopped")
    
    def _background_processor(self):
        """Background thread for processing audio"""
        audio_buffer = []
        buffer_duration = 0.0
        
        while not self._stop_processing:
            try:
                # Get audio chunk with timeout
                chunk_data = self._audio_queue.get(timeout=0.1)
                if chunk_data is None:
                    continue
                
                audio_array, sample_rate = chunk_data
                chunk_duration = len(audio_array) / sample_rate
                
                audio_buffer.append(audio_array)
                buffer_duration += chunk_duration
                
                # Process when we have enough audio (2 seconds for faster response)
                if buffer_duration >= 2.0:
                    full_audio = np.concatenate(audio_buffer)
                    audio_buffer = []
                    buffer_duration = 0.0
                    
                    # Process with Whisper
                    result = self._process_with_whisper(full_audio, sample_rate)
                    if result:
                        self._result_queue.put(result)
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Background processing error: {e}")
    
    def process_audio_chunk(self, audio_bytes: bytes) -> Optional[AudioResult]:
        """
        Process audio chunk (called from WebRTC callback)
        
        For compatibility with streaming API, but uses Whisper internally
        """
        # Check for results from background thread
        try:
            return self._result_queue.get_nowait()
        except queue.Empty:
            return None
    
    def add_audio_to_buffer(self, audio_array: np.ndarray, sample_rate: int):
        """Add audio to processing queue"""
        self._audio_queue.put((audio_array, sample_rate))
    
    def _process_with_whisper(self, audio: np.ndarray, sample_rate: int) -> Optional[AudioResult]:
        """Process audio with Whisper model"""
        if not self.whisper_model:
            return None
        
        try:
            # Ensure float32 in range [-1, 1]
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            
            if np.abs(audio).max() > 1.0:
                audio = audio / 32768.0
            
            # Resample to 16kHz if needed (Whisper requirement)
            if sample_rate != 16000:
                # Simple resampling
                ratio = 16000 / sample_rate
                new_length = int(len(audio) * ratio)
                indices = np.linspace(0, len(audio) - 1, new_length).astype(int)
                audio = audio[indices]
            
            # Pad or trim to 30 seconds (Whisper expects this)
            audio = whisper.pad_or_trim(audio)
            
            # Transcribe
            result = self.whisper_model.transcribe(
                audio,
                language="en",  # Can be "hi" for Hindi or None for auto-detect
                fp16=False,  # Use fp32 for CPU
                task="transcribe"
            )
            
            transcript = result.get("text", "").strip()
            
            if transcript:
                # Add to full transcript
                self.full_transcript += " " + transcript
                
                # Match keywords
                matches = self.match_keywords(self.full_transcript)
                score = self.calculate_score(matches)
                threat_level = self.determine_threat_level(score)
                
                logger.info(f"Transcribed: {transcript[:80]}...")
                if matches:
                    logger.warning(f"Keywords found: {matches}")
                
                return AudioResult(
                    score=score,
                    transcript=transcript,
                    detected_keywords=matches,
                    threat_level=threat_level,
                    confidence=0.85,
                    is_final=True
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return None
    
    def process_audio(self, audio: np.ndarray, sample_rate: int) -> Optional[AudioResult]:
        """
        Process audio array with Whisper (synchronous, for direct calls)
        
        Args:
            audio: Audio samples as numpy array
            sample_rate: Sample rate in Hz
            
        Returns:
            AudioResult with transcription and analysis
        """
        return self._process_with_whisper(audio, sample_rate)
    
    def match_keywords(self, text: str) -> Dict[str, List[str]]:
        """
        Match scam keywords in text
        
        Args:
            text: Text to search for keywords
            
        Returns:
            Dictionary of category -> matched keywords
        """
        matches = {}
        text_lower = text.lower()
        
        for category, keywords in self.keywords.items():
            category_matches = []
            for keyword in keywords:
                # Case-insensitive search with word boundaries
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    category_matches.append(keyword)
            
            if category_matches:
                matches[category] = category_matches
        
        return matches
    
    def calculate_score(self, matches: Dict[str, List[str]]) -> float:
        """
        Calculate threat score based on keyword matches
        
        Args:
            matches: Dictionary of category -> matched keywords
            
        Returns:
            Score from 0-10
        """
        if not matches:
            return 0.0
        
        # Weight by category severity
        category_weights = {
            "authority_impersonation": 2.0,
            "fake_legal_threats": 2.5,
            "coercion_isolation": 3.0,
            "financial_demands": 2.5,
            "urgency_pressure": 2.0
        }
        
        total_score = 0.0
        for category, keywords in matches.items():
            weight = category_weights.get(category, 1.0)
            # More keywords = higher score, with diminishing returns
            keyword_score = min(len(keywords) * 0.8, 3.0)
            total_score += keyword_score * weight
        
        # Bonus for multiple categories (more suspicious)
        if len(matches) >= 3:
            total_score *= 1.3
        elif len(matches) >= 2:
            total_score *= 1.15
        
        return min(10.0, total_score)
    
    def determine_threat_level(self, score: float) -> str:
        """
        Determine threat level from score
        
        Args:
            score: Threat score (0-10)
            
        Returns:
            Threat level string
        """
        if score >= 8.0:
            return "critical"
        elif score >= 6.0:
            return "high"
        elif score >= 4.0:
            return "medium"
        else:
            return "low"
    
    def get_full_transcript(self) -> str:
        """Get the full accumulated transcript"""
        return self.full_transcript.strip()
    
    def reset(self):
        """Reset transcript buffer"""
        self.transcript_buffer = ""
        self.full_transcript = ""
        logger.info("Audio processor reset")


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    processor = AudioProcessor()
    
    # Test keyword matching
    test_text = """
    This is CBI officer speaking. You are under digital arrest.
    There is an arrest warrant against you for money laundering.
    Do not disconnect this call or we will raid your house.
    Transfer money to this verification account immediately.
    """
    
    matches = processor.match_keywords(test_text)
    score = processor.calculate_score(matches)
    level = processor.determine_threat_level(score)
    
    print(f"\nMatches: {matches}")
    print(f"Score: {score:.1f}/10")
    print(f"Threat Level: {level}")
