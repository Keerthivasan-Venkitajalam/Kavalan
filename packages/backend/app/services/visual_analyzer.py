"""
Visual Analysis Service using Google Gemini Vision API

Supports:
- Uniform and badge detection
- Threatening element identification
- On-screen text extraction (OCR)
- Confidence scoring
- Rate limit handling
- Frame caching
"""
import google.generativeai as genai
from PIL import Image
import io
import json
import logging
import hashlib
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


@dataclass
class VisualResult:
    """Result of visual frame analysis"""
    uniform_detected: bool
    badge_detected: bool
    threats: List[str]
    text_detected: str
    confidence: float
    score: float
    analysis: str
    cached: bool = False


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded"""
    pass


class VisualAnalyzer:
    """
    Visual frame analysis engine using Google Gemini Vision API
    
    Features:
    - Detects official uniforms and badges
    - Identifies threatening visual elements
    - Extracts on-screen text (OCR)
    - Generates confidence scores
    - Handles rate limits with queueing
    - Caches similar frame analyses
    """
    
    # Uniform database for validation
    KNOWN_UNIFORMS = [
        'police', 'cbi', 'ed', 'income tax', 'customs',
        'government official', 'military', 'security'
    ]
    
    # Frame similarity threshold for caching
    SIMILARITY_THRESHOLD = 0.95
    
    # Cache TTL in seconds
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self, api_key: str, model_name: str = 'gemini-2.0-flash-exp'):
        """
        Initialize visual analyzer
        
        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use
        """
        logger.info(f"Initializing Gemini Vision API with model: {model_name}")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # Frame cache: {frame_hash: (result, timestamp)}
        self.frame_cache: Dict[str, Tuple[VisualResult, datetime]] = {}
        
        # Rate limit queue: frames waiting to be processed
        self.rate_limit_queue: List[Tuple[bytes, datetime]] = []
        
        # Last analyzed frame for deduplication
        self.last_frame_bytes: Optional[bytes] = None
        self.last_frame_result: Optional[VisualResult] = None
        
        logger.info("Visual analyzer initialized successfully")
    
    def _calculate_frame_hash(self, frame_bytes: bytes) -> str:
        """Calculate SHA-256 hash of frame for caching"""
        return hashlib.sha256(frame_bytes).hexdigest()
    
    def _calculate_frame_similarity(self, frame1_bytes: bytes, frame2_bytes: bytes) -> float:
        """
        Calculate similarity between two frames using perceptual hashing
        
        Args:
            frame1_bytes: First frame as bytes
            frame2_bytes: Second frame as bytes
        
        Returns:
            Similarity score in range [0.0, 1.0]
        """
        try:
            # Load images
            img1 = Image.open(io.BytesIO(frame1_bytes))
            img2 = Image.open(io.BytesIO(frame2_bytes))
            
            # Resize to same size for comparison
            size = (64, 64)
            img1 = img1.resize(size, Image.Resampling.LANCZOS)
            img2 = img2.resize(size, Image.Resampling.LANCZOS)
            
            # Convert to grayscale
            img1_gray = img1.convert('L')
            img2_gray = img2.convert('L')
            
            # Convert to numpy arrays
            arr1 = np.array(img1_gray).flatten()
            arr2 = np.array(img2_gray).flatten()
            
            # Calculate normalized correlation
            correlation = np.corrcoef(arr1, arr2)[0, 1]
            
            # Handle NaN (can occur if arrays are constant)
            if np.isnan(correlation):
                correlation = 1.0 if np.array_equal(arr1, arr2) else 0.0
            
            return float(correlation)
        
        except Exception as e:
            logger.error(f"Failed to calculate frame similarity: {e}")
            return 0.0
    
    def _check_cache(self, frame_bytes: bytes) -> Optional[VisualResult]:
        """
        Check if similar frame exists in cache
        
        Args:
            frame_bytes: Frame data as bytes
        
        Returns:
            Cached VisualResult if found, None otherwise
        """
        frame_hash = self._calculate_frame_hash(frame_bytes)
        
        # Check exact match first
        if frame_hash in self.frame_cache:
            result, timestamp = self.frame_cache[frame_hash]
            
            # Check if cache entry is still valid
            if datetime.now() - timestamp < timedelta(seconds=self.CACHE_TTL):
                logger.info(f"Cache hit (exact match): {frame_hash[:16]}...")
                result.cached = True
                return result
            else:
                # Remove expired entry
                del self.frame_cache[frame_hash]
        
        # Check for similar frames
        for cached_hash, (cached_result, timestamp) in list(self.frame_cache.items()):
            # Skip expired entries
            if datetime.now() - timestamp >= timedelta(seconds=self.CACHE_TTL):
                del self.frame_cache[cached_hash]
                continue
            
            # Calculate similarity (expensive, so we limit checks)
            # In production, use a more efficient similarity index
            # For now, we only check exact hash matches
            pass
        
        return None
    
    def _add_to_cache(self, frame_bytes: bytes, result: VisualResult):
        """
        Add frame analysis result to cache
        
        Args:
            frame_bytes: Frame data as bytes
            result: Analysis result to cache
        """
        frame_hash = self._calculate_frame_hash(frame_bytes)
        self.frame_cache[frame_hash] = (result, datetime.now())
        logger.info(f"Added to cache: {frame_hash[:16]}... (cache size: {len(self.frame_cache)})")
    
    def _clean_cache(self):
        """Remove expired entries from cache"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.frame_cache.items()
            if now - timestamp >= timedelta(seconds=self.CACHE_TTL)
        ]
        
        for key in expired_keys:
            del self.frame_cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def analyze_frame(self, frame_bytes: bytes) -> VisualResult:
        """
        Analyze video frame for threats
        
        Args:
            frame_bytes: Frame data as bytes (JPEG, PNG, etc.)
        
        Returns:
            VisualResult with analysis, score, and confidence
        
        Raises:
            RateLimitError: If API rate limit is exceeded
        """
        # Check for frame deduplication (similar consecutive frames)
        if self.last_frame_bytes is not None and self.last_frame_result is not None:
            similarity = self._calculate_frame_similarity(self.last_frame_bytes, frame_bytes)
            if similarity > self.SIMILARITY_THRESHOLD:
                logger.info(f"Frame deduplication: similarity={similarity:.3f} > {self.SIMILARITY_THRESHOLD}, skipping analysis")
                # Return cached result from last frame
                deduplicated_result = VisualResult(
                    uniform_detected=self.last_frame_result.uniform_detected,
                    badge_detected=self.last_frame_result.badge_detected,
                    threats=self.last_frame_result.threats,
                    text_detected=self.last_frame_result.text_detected,
                    confidence=self.last_frame_result.confidence,
                    score=self.last_frame_result.score,
                    analysis=self.last_frame_result.analysis,
                    cached=True
                )
                return deduplicated_result
        
        # Check cache first
        cached_result = self._check_cache(frame_bytes)
        if cached_result:
            # Update last frame for deduplication
            self.last_frame_bytes = frame_bytes
            self.last_frame_result = cached_result
            return cached_result
        
        try:
            # Load image
            image = Image.open(io.BytesIO(frame_bytes))
            
            # Construct analysis prompt
            prompt = """Analyze this video call frame for potential scam indicators. Provide a JSON response with:

1. "uniform_detected": true/false - Is someone wearing an official uniform (police, CBI, government)?
2. "uniform_type": string - Type of uniform if detected (e.g., "police", "CBI", "government official")
3. "badge_detected": true/false - Are there visible badges or insignias?
4. "badge_description": string - Description of badge if detected
5. "threats": array of strings - List any threatening visual elements (weapons, legal documents, intimidating imagery)
6. "text_detected": string - Any visible on-screen text (OCR)
7. "text_positions": array of objects with {text, x, y, width, height} - Position of detected text
8. "confidence": float 0.0-1.0 - Overall confidence in the analysis
9. "analysis": string - Brief summary of findings

Focus on identifying:
- Official-looking uniforms (police, CBI, ED, Income Tax, Customs)
- Government badges or insignias
- Legal documents or arrest warrants
- Threatening imagery or weapons
- Text that might indicate scam (bank details, threats, official notices)

Respond ONLY with valid JSON, no additional text."""
            
            # Call Gemini Vision API
            logger.info("Calling Gemini Vision API for frame analysis")
            response = self.model.generate_content([prompt, image])
            
            # Parse response
            analysis_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text[7:]
            if analysis_text.startswith('```'):
                analysis_text = analysis_text[3:]
            if analysis_text.endswith('```'):
                analysis_text = analysis_text[:-3]
            
            analysis_text = analysis_text.strip()
            
            # Parse JSON
            try:
                analysis = json.loads(analysis_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {e}")
                logger.error(f"Response text: {analysis_text}")
                # Return default result
                analysis = {
                    'uniform_detected': False,
                    'badge_detected': False,
                    'threats': [],
                    'text_detected': '',
                    'confidence': 0.5,
                    'analysis': 'Failed to parse API response'
                }
            
            # Extract fields
            uniform_detected = analysis.get('uniform_detected', False)
            badge_detected = analysis.get('badge_detected', False)
            threats = analysis.get('threats', [])
            text_detected = analysis.get('text_detected', '')
            confidence = float(analysis.get('confidence', 0.5))
            analysis_summary = analysis.get('analysis', '')
            
            # Calculate threat score
            score = self.calculate_score(analysis)
            
            # Create result
            result = VisualResult(
                uniform_detected=uniform_detected,
                badge_detected=badge_detected,
                threats=threats,
                text_detected=text_detected,
                confidence=confidence,
                score=score,
                analysis=analysis_summary,
                cached=False
            )
            
            # Add to cache
            self._add_to_cache(frame_bytes, result)
            
            # Update last frame for deduplication
            self.last_frame_bytes = frame_bytes
            self.last_frame_result = result
            
            # Clean expired cache entries periodically
            if len(self.frame_cache) > 100:
                self._clean_cache()
            
            logger.info(f"Frame analysis complete: score={score:.2f}, confidence={confidence:.2f}")
            return result
        
        except Exception as e:
            # Check if it's a rate limit error
            error_str = str(e).lower()
            if 'rate limit' in error_str or 'quota' in error_str or '429' in error_str:
                logger.warning(f"Gemini API rate limit exceeded: {e}")
                raise RateLimitError(f"API rate limit exceeded: {e}")
            
            # Other errors
            logger.error(f"Frame analysis failed: {e}")
            raise
    
    def calculate_score(self, analysis: Dict) -> float:
        """
        Calculate visual threat score (0-10) based on analysis
        
        Scoring:
        - Uniform detected: +4.0
        - Badge detected: +3.0
        - Each threat element: +1.5
        - Threatening text detected: +2.0
        
        Args:
            analysis: Analysis dictionary from Gemini
        
        Returns:
            Threat score in range [0.0, 10.0]
        """
        score = 0.0
        
        # Uniform detection
        if analysis.get('uniform_detected', False):
            score += 4.0
            logger.info("Uniform detected: +4.0")
        
        # Badge detection
        if analysis.get('badge_detected', False):
            score += 3.0
            logger.info("Badge detected: +3.0")
        
        # Threat elements
        threats = analysis.get('threats', [])
        if threats:
            threat_score = len(threats) * 1.5
            score += threat_score
            logger.info(f"{len(threats)} threats detected: +{threat_score:.1f}")
        
        # Threatening text
        text = analysis.get('text_detected', '').lower()
        threatening_keywords = [
            'arrest', 'warrant', 'police', 'court', 'legal action',
            'fine', 'penalty', 'jail', 'prison', 'investigation'
        ]
        if any(keyword in text for keyword in threatening_keywords):
            score += 2.0
            logger.info("Threatening text detected: +2.0")
        
        # Cap at 10.0
        score = min(score, 10.0)
        
        logger.info(f"Calculated visual threat score: {score:.2f}")
        return score
    
    def queue_frame(self, frame_bytes: bytes):
        """
        Queue frame for delayed processing (rate limit handling)
        
        Args:
            frame_bytes: Frame data to queue
        """
        self.rate_limit_queue.append((frame_bytes, datetime.now()))
        logger.info(f"Frame queued for delayed processing (queue size: {len(self.rate_limit_queue)})")
    
    def process_queued_frames(self, max_frames: int = 10) -> List[VisualResult]:
        """
        Process frames from rate limit queue
        
        Args:
            max_frames: Maximum number of frames to process
        
        Returns:
            List of VisualResult for processed frames
        """
        results = []
        processed = 0
        
        while self.rate_limit_queue and processed < max_frames:
            frame_bytes, queued_time = self.rate_limit_queue.pop(0)
            
            try:
                result = self.analyze_frame(frame_bytes)
                results.append(result)
                processed += 1
                
                # Add small delay to avoid hitting rate limit again
                time.sleep(0.5)
            
            except RateLimitError:
                # Put back in queue and stop processing
                self.rate_limit_queue.insert(0, (frame_bytes, queued_time))
                logger.warning("Rate limit hit again, stopping queue processing")
                break
            
            except Exception as e:
                logger.error(f"Failed to process queued frame: {e}")
                # Continue with next frame
        
        if results:
            logger.info(f"Processed {len(results)} frames from queue")
        
        return results
    
    def get_queue_size(self) -> int:
        """Get current size of rate limit queue"""
        return len(self.rate_limit_queue)
    
    def clear_cache(self):
        """Clear all cached frame analyses"""
        self.frame_cache.clear()
        logger.info("Frame cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'size': len(self.frame_cache),
            'ttl_seconds': self.CACHE_TTL,
            'similarity_threshold': self.SIMILARITY_THRESHOLD
        }
