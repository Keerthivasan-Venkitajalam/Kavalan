"""
Audio Transcription Service using OpenAI Whisper

Supports:
- Hindi, English, Tamil, Telugu, Malayalam, Kannada
- Word-level timestamps
- Speaker diarization
- Keyword matching
- Low-confidence flagging
- Redis-based pattern caching
"""
import whisper
import numpy as np
import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from app.utils.pattern_cache import PatternCache

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """Represents a segment of transcribed audio"""
    text: str
    start: float
    end: float
    confidence: float
    speaker: Optional[str] = None
    words: Optional[List[Dict]] = None


@dataclass
class AudioResult:
    """Result of audio transcription and analysis"""
    transcript: str
    language: str
    segments: List[TranscriptSegment]
    keywords: Dict[str, List[str]]
    score: float
    confidence: float
    low_confidence_segments: List[int]


class AudioTranscriber:
    """
    Audio transcription and keyword matching engine
    
    Uses OpenAI Whisper (medium model) for transcription with:
    - Multi-language support (Hindi, English, Tamil, Telugu, Malayalam, Kannada)
    - Word-level timestamps
    - Speaker diarization
    - Keyword-based threat detection
    """
    
    # Supported languages
    SUPPORTED_LANGUAGES = ['hi', 'en', 'ta', 'te', 'ml', 'kn']
    
    # Language name mapping
    LANGUAGE_NAMES = {
        'hi': 'Hindi',
        'en': 'English',
        'ta': 'Tamil',
        'te': 'Telugu',
        'ml': 'Malayalam',
        'kn': 'Kannada'
    }
    
    # Low confidence threshold
    LOW_CONFIDENCE_THRESHOLD = 0.6
    
    def __init__(self, model_size: str = 'medium', keywords_path: Optional[str] = None):
        """
        Initialize audio transcriber
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            keywords_path: Path to keyword database JSON file
        """
        logger.info(f"Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)
        logger.info(f"Whisper model loaded successfully")
        
        # Load keyword database
        if keywords_path is None:
            keywords_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "scam_keywords.json"
        
        self.keywords = self._load_keywords(keywords_path)
        logger.info(f"Loaded {sum(len(v) for v in self.keywords.values())} keywords across {len(self.keywords)} categories")
        
        # Initialize pattern cache
        try:
            self.pattern_cache = PatternCache()
            logger.info("Pattern cache initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize pattern cache: {e}. Continuing without caching.")
            self.pattern_cache = None
    
    def _load_keywords(self, path: Path) -> Dict[str, List[str]]:
        """Load keyword database from JSON file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                keywords = json.load(f)
            return keywords
        except Exception as e:
            logger.error(f"Failed to load keywords from {path}: {e}")
            # Return empty keywords dict as fallback
            return {
                'authority': [],
                'coercion': [],
                'financial': [],
                'crime': [],
                'urgency': []
            }
    
    def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
        sample_rate: int = 16000
    ) -> Dict:
        """
        Transcribe audio chunk with word-level timestamps
        
        Args:
            audio: Audio data as numpy array
            language: Language code (e.g., 'hi', 'en', 'ta'). If None, auto-detect
            sample_rate: Audio sample rate in Hz
        
        Returns:
            Dictionary with transcript, language, segments, and word-level timestamps
        """
        try:
            # Validate language
            if language and language not in self.SUPPORTED_LANGUAGES:
                logger.warning(f"Unsupported language '{language}', will auto-detect")
                language = None
            
            # Transcribe with Whisper
            logger.info(f"Transcribing audio (language: {language or 'auto-detect'})")
            result = self.model.transcribe(
                audio,
                language=language,
                fp16=False,  # Use FP32 for better accuracy
                word_timestamps=True,  # Enable word-level timestamps
                verbose=False
            )
            
            detected_language = result.get('language', 'unknown')
            logger.info(f"Transcription complete. Detected language: {detected_language}")
            
            return {
                'text': result['text'],
                'language': detected_language,
                'segments': result.get('segments', [])
            }
        
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def detect_speaker_changes(self, segments: List[Dict]) -> List[TranscriptSegment]:
        """
        Detect speaker changes in audio segments
        
        Uses simple heuristic based on:
        - Pauses between segments (> 1 second = potential speaker change)
        - Audio energy changes (not implemented in this version)
        
        Args:
            segments: List of transcript segments from Whisper
        
        Returns:
            List of TranscriptSegment with speaker labels
        """
        labeled_segments = []
        current_speaker = "Speaker_1"
        speaker_count = 1
        
        for i, segment in enumerate(segments):
            # Check for long pause indicating speaker change
            if i > 0:
                prev_end = segments[i-1]['end']
                curr_start = segment['start']
                pause_duration = curr_start - prev_end
                
                # If pause > 1 second, assume speaker change
                if pause_duration > 1.0:
                    speaker_count += 1
                    current_speaker = f"Speaker_{speaker_count}"
            
            # Create TranscriptSegment with speaker label
            labeled_segment = TranscriptSegment(
                text=segment['text'],
                start=segment['start'],
                end=segment['end'],
                confidence=segment.get('confidence', 1.0),
                speaker=current_speaker,
                words=segment.get('words', [])
            )
            labeled_segments.append(labeled_segment)
        
        logger.info(f"Detected {speaker_count} speakers in audio")
        return labeled_segments
    
    def match_keywords(self, transcript: str, language: str = 'en') -> Dict[str, List[str]]:
        """
        Match transcript against scam keyword patterns
        
        Uses Redis caching for frequently accessed patterns (>10 accesses/minute).
        Cached patterns have a TTL of 5 minutes.
        
        Args:
            transcript: Transcribed text
            language: Language code for language-specific matching
        
        Returns:
            Dictionary mapping category to matched keywords
        """
        matches = {}
        transcript_lower = transcript.lower()
        
        for category, patterns in self.keywords.items():
            # Use cached patterns if available
            if self.pattern_cache:
                patterns = self.pattern_cache.get_or_cache_patterns(
                    category=category,
                    patterns=patterns,
                    language=language
                )
            
            found = []
            for pattern in patterns:
                # Case-insensitive matching
                if pattern.lower() in transcript_lower:
                    found.append(pattern)
            
            if found:
                matches[category] = found
        
        logger.info(f"Matched {sum(len(v) for v in matches.values())} keywords across {len(matches)} categories")
        return matches
    
    def calculate_score(self, matches: Dict[str, List[str]]) -> float:
        """
        Calculate audio threat score (0-10) based on keyword matches
        
        Scoring weights:
        - authority: 2.5 per keyword
        - coercion: 3.0 per keyword
        - financial: 2.0 per keyword
        - crime: 2.5 per keyword
        - urgency: 2.0 per keyword
        
        Args:
            matches: Dictionary of matched keywords by category
        
        Returns:
            Threat score in range [0.0, 10.0]
        """
        weights = {
            'authority': 2.5,
            'coercion': 3.0,
            'financial': 2.0,
            'crime': 2.5,
            'urgency': 2.0
        }
        
        score = 0.0
        for category, keywords in matches.items():
            weight = weights.get(category, 1.0)
            score += len(keywords) * weight
        
        # Cap at 10.0
        score = min(score, 10.0)
        
        logger.info(f"Calculated audio threat score: {score:.2f}")
        return score
    
    def flag_low_confidence(self, segments: List[TranscriptSegment]) -> List[int]:
        """
        Flag segments with confidence below threshold
        
        Args:
            segments: List of transcript segments
        
        Returns:
            List of segment indices with low confidence
        """
        low_confidence_indices = []
        
        for i, segment in enumerate(segments):
            if segment.confidence < self.LOW_CONFIDENCE_THRESHOLD:
                low_confidence_indices.append(i)
                logger.warning(
                    f"Low confidence segment {i}: '{segment.text}' "
                    f"(confidence: {segment.confidence:.2f})"
                )
        
        if low_confidence_indices:
            logger.info(f"Flagged {len(low_confidence_indices)} low-confidence segments")
        
        return low_confidence_indices
    
    def analyze(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
        sample_rate: int = 16000
    ) -> AudioResult:
        """
        Complete audio analysis pipeline
        
        Args:
            audio: Audio data as numpy array
            language: Language code (optional, will auto-detect)
            sample_rate: Audio sample rate in Hz
        
        Returns:
            AudioResult with transcript, keywords, score, and metadata
        """
        # Step 1: Transcribe audio
        transcription = self.transcribe(audio, language, sample_rate)
        
        # Step 2: Detect speaker changes
        segments = self.detect_speaker_changes(transcription['segments'])
        
        # Step 3: Match keywords
        keywords = self.match_keywords(transcription['text'], transcription['language'])
        
        # Step 4: Calculate threat score
        score = self.calculate_score(keywords)
        
        # Step 5: Flag low-confidence segments
        low_confidence_segments = self.flag_low_confidence(segments)
        
        # Step 6: Calculate overall confidence
        if segments:
            avg_confidence = sum(s.confidence for s in segments) / len(segments)
        else:
            avg_confidence = 1.0
        
        return AudioResult(
            transcript=transcription['text'],
            language=transcription['language'],
            segments=segments,
            keywords=keywords,
            score=score,
            confidence=avg_confidence,
            low_confidence_segments=low_confidence_segments
        )

    def get_cache_stats(self) -> Dict:
        """
        Get pattern cache statistics
        
        Returns:
            Dictionary with cache statistics, or empty dict if cache unavailable
        """
        if self.pattern_cache:
            return self.pattern_cache.get_cache_stats()
        return {}
    
    def clear_cache(self, category: Optional[str] = None, language: Optional[str] = None):
        """
        Clear pattern cache
        
        Args:
            category: If specified, clear only this category
            language: If specified, clear only this language
        """
        if self.pattern_cache:
            self.pattern_cache.clear_cache(category, language)
            logger.info("Pattern cache cleared")
        else:
            logger.warning("Pattern cache not available")
