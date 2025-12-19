"""
Audio Processor module for Kavalan Lite
Handles audio transcription and keyword matching for scam detection
"""

import numpy as np
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import re

# Try to import Whisper, but make it optional
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

logger = logging.getLogger(__name__)

@dataclass
class AudioResult:
    """Result from audio analysis"""
    score: float  # 0-10 (higher = more suspicious)
    transcript: str
    detected_keywords: Dict[str, List[str]]  # category -> keywords
    threat_level: str  # "low", "medium", "high", "critical"
    confidence: float

class AudioProcessor:
    """
    Processes audio for transcription and keyword matching
    
    Uses Whisper for speech-to-text and keyword dictionary for scam detection
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
        if WHISPER_AVAILABLE:
            try:
                # Use tiny model for speed (can be changed to base/small for accuracy)
                self.whisper_model = whisper.load_model("tiny")
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                self.whisper_model = None
        else:
            logger.warning("Whisper not available, audio transcription will use mock data")
        
        # Transcript buffer for continuous processing
        self.transcript_buffer = ""
        
        logger.info(f"AudioProcessor initialized with {len(self.keywords)} keyword categories")
    
    def _get_default_keywords(self) -> Dict[str, List[str]]:
        """Get default scam keywords"""
        return {
            "authority": ["CBI", "NCB", "Police", "Court"],
            "coercion": ["Do not disconnect", "Stay on call"],
            "financial": ["Transfer money", "Verification account"],
            "crime": ["Money laundering", "Arrest warrant"]
        }
    
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio using Whisper
        
        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate of audio (default 16000 Hz)
            
        Returns:
            Transcribed text
        """
        if not self.whisper_model:
            logger.warning("Whisper model not available, returning empty transcript")
            return ""
        
        try:
            # Ensure audio is float32 and normalized
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            
            # Normalize audio to [-1, 1] range
            if audio.max() > 1.0 or audio.min() < -1.0:
                audio = audio / np.abs(audio).max()
            
            # Transcribe
            result = self.whisper_model.transcribe(audio, language="en")
            transcript = result["text"].strip()
            
            logger.debug(f"Transcribed: {transcript[:100]}...")
            return transcript
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""
    
    def match_keywords(self, text: str) -> Dict[str, List[str]]:
        """
        Match text against scam keyword dictionary
        
        Args:
            text: Text to search for keywords
            
        Returns:
            Dictionary of category -> matched keywords
        """
        if not text:
            return {}
        
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        matches = {}
        
        for category, keywords in self.keywords.items():
            category_matches = []
            
            for keyword in keywords:
                # Case-insensitive search
                keyword_lower = keyword.lower()
                
                # Use word boundary matching for better accuracy
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                
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
            Threat score (0-10)
        """
        if not matches:
            return 0.0
        
        # Base score calculation
        score = 0.0
        
        # Category weights (some categories are more suspicious than others)
        category_weights = {
            "authority": 2.0,
            "coercion": 2.5,
            "financial": 3.0,
            "crime": 2.0,
            "urgency": 1.5
        }
        
        # Calculate score based on categories and keyword count
        for category, keywords in matches.items():
            weight = category_weights.get(category, 1.0)
            # Score increases with number of keywords in category
            category_score = min(weight * len(keywords), weight * 2)  # Cap per category
            score += category_score
        
        # Bonus for multiple categories (indicates more sophisticated scam)
        num_categories = len(matches)
        if num_categories >= 3:
            score += 2.0
        elif num_categories >= 2:
            score += 1.0
        
        # Clamp to [0, 10]
        score = max(0.0, min(10.0, score))
        
        return score
    
    def determine_threat_level(self, score: float) -> str:
        """
        Determine threat level based on score
        
        Args:
            score: Threat score (0-10)
            
        Returns:
            Threat level string
        """
        if score >= 8.0:
            return "critical"
        elif score >= 6.0:
            return "high"
        elif score >= 3.0:
            return "medium"
        else:
            return "low"
    
    def process_audio(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> AudioResult:
        """
        Process audio chunk and return analysis
        
        Args:
            audio_chunk: Audio data as numpy array
            sample_rate: Sample rate of audio
            
        Returns:
            AudioResult with analysis
        """
        # Transcribe audio
        transcript = self.transcribe(audio_chunk, sample_rate)
        
        # Add to buffer
        if transcript:
            self.transcript_buffer += " " + transcript
        
        # Keep buffer size manageable (last 1000 characters)
        if len(self.transcript_buffer) > 1000:
            self.transcript_buffer = self.transcript_buffer[-1000:]
        
        # Match keywords in full buffer
        matches = self.match_keywords(self.transcript_buffer)
        
        # Calculate score
        score = self.calculate_score(matches)
        
        # Determine threat level
        threat_level = self.determine_threat_level(score)
        
        # Calculate confidence (based on transcript length and clarity)
        confidence = min(len(transcript) / 100.0, 1.0) if transcript else 0.0
        
        return AudioResult(
            score=score,
            transcript=transcript,
            detected_keywords=matches,
            threat_level=threat_level,
            confidence=confidence
        )
    
    def reset_buffer(self):
        """Reset transcript buffer"""
        self.transcript_buffer = ""
        logger.debug("Audio transcript buffer reset")