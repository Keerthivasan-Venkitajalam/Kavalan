"""
Fusion Engine for Kavalan Lite
Combines scores from visual, liveness, and audio analysis modules
"""

from dataclasses import dataclass
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

@dataclass
class FusionResult:
    """Result from fusion engine combining all analysis scores"""
    final_score: float  # 0-10
    visual_score: float  # 0-10
    liveness_score: float  # 0-10
    audio_score: float  # 0-10
    is_alert: bool
    alert_message: str
    
    def __post_init__(self):
        """Validate score ranges after initialization"""
        self._validate_score("final_score", self.final_score)
        self._validate_score("visual_score", self.visual_score)
        self._validate_score("liveness_score", self.liveness_score)
        self._validate_score("audio_score", self.audio_score)
    
    def _validate_score(self, name: str, score: float):
        """Ensure score is in valid range [0, 10]"""
        if not (0.0 <= score <= 10.0):
            logger.warning(f"{name} out of range: {score}, clamping to [0, 10]")
            # Clamp the score to valid range
            if hasattr(self, name):
                setattr(self, name, max(0.0, min(10.0, score)))

class FusionEngine:
    """
    Combines scores from multiple analysis modules using weighted average
    
    Weights:
    - Visual: 0.4 (uniform detection is most important indicator)
    - Liveness: 0.3 (deepfake detection is critical)
    - Audio: 0.3 (keyword matching provides context)
    """
    
    # Default weights (can be overridden via config)
    VISUAL_WEIGHT: float = 0.4
    LIVENESS_WEIGHT: float = 0.3
    AUDIO_WEIGHT: float = 0.3
    ALERT_THRESHOLD: float = 8.0
    
    def __init__(self, thresholds: dict = None):
        """
        Initialize fusion engine with optional custom thresholds
        
        Args:
            thresholds: Dictionary containing custom weights and thresholds
        """
        if thresholds:
            self.visual_weight = thresholds.get("visual_weight", self.VISUAL_WEIGHT)
            self.liveness_weight = thresholds.get("liveness_weight", self.LIVENESS_WEIGHT)
            self.audio_weight = thresholds.get("audio_weight", self.AUDIO_WEIGHT)
            self.alert_threshold = thresholds.get("alert_threshold", self.ALERT_THRESHOLD)
        else:
            self.visual_weight = self.VISUAL_WEIGHT
            self.liveness_weight = self.LIVENESS_WEIGHT
            self.audio_weight = self.AUDIO_WEIGHT
            self.alert_threshold = self.ALERT_THRESHOLD
        
        # Validate weights sum to 1.0 (approximately)
        total_weight = self.visual_weight + self.liveness_weight + self.audio_weight
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights don't sum to 1.0: {total_weight}, normalizing...")
            self.visual_weight /= total_weight
            self.liveness_weight /= total_weight
            self.audio_weight /= total_weight
        
        logger.info(f"FusionEngine initialized with weights: V={self.visual_weight:.2f}, "
                   f"L={self.liveness_weight:.2f}, A={self.audio_weight:.2f}, "
                   f"threshold={self.alert_threshold}")
    
    def _clamp_score(self, score: float) -> float:
        """Ensure score is in valid range [0, 10]"""
        return max(0.0, min(10.0, score))
    
    def fuse_scores(
        self, 
        visual: float, 
        liveness: float, 
        audio: float
    ) -> FusionResult:
        """
        Combine scores using weighted average
        
        Args:
            visual: Visual analysis score (0-10)
            liveness: Liveness detection score (0-10)
            audio: Audio analysis score (0-10)
            
        Returns:
            FusionResult with combined score and alert status
        """
        # Clamp input scores to valid range
        visual = self._clamp_score(visual)
        liveness = self._clamp_score(liveness)
        audio = self._clamp_score(audio)
        
        # Calculate weighted average
        final_score = (
            visual * self.visual_weight +
            liveness * self.liveness_weight +
            audio * self.audio_weight
        )
        
        # Ensure final score is in valid range (should be guaranteed by math, but safety first)
        final_score = self._clamp_score(final_score)
        
        # Check if alert should be triggered
        is_alert, alert_message = self.check_alert(final_score)
        
        logger.debug(f"Fusion: V={visual:.2f}*{self.visual_weight:.2f} + "
                    f"L={liveness:.2f}*{self.liveness_weight:.2f} + "
                    f"A={audio:.2f}*{self.audio_weight:.2f} = {final_score:.2f}")
        
        return FusionResult(
            final_score=final_score,
            visual_score=visual,
            liveness_score=liveness,
            audio_score=audio,
            is_alert=is_alert,
            alert_message=alert_message
        )
    
    def check_alert(self, score: float) -> Tuple[bool, str]:
        """
        Check if score triggers alert and generate appropriate message
        
        Args:
            score: Final fusion score (0-10)
            
        Returns:
            Tuple of (is_alert: bool, message: str)
        """
        if score > self.alert_threshold:
            # High alert - likely scam
            if score >= 9.0:
                message = "🚨 CRITICAL ALERT: High probability Digital Arrest scam detected! DISCONNECT IMMEDIATELY!"
            elif score >= 8.5:
                message = "⚠️ HIGH ALERT: Potential Digital Arrest scam detected. Consider disconnecting."
            else:
                message = "⚠️ ALERT: Suspicious activity detected. Exercise extreme caution."
            
            return True, message
        else:
            # No alert
            if score >= 6.0:
                message = "⚡ Moderate risk detected. Stay vigilant."
            elif score >= 3.0:
                message = "✓ Low risk. Continue with normal caution."
            else:
                message = "✓ No significant threats detected."
            
            return False, message
    
    def get_score_breakdown(self, result: FusionResult) -> dict:
        """
        Get detailed breakdown of how the final score was calculated
        
        Args:
            result: FusionResult to analyze
            
        Returns:
            Dictionary with score breakdown details
        """
        return {
            "final_score": result.final_score,
            "components": {
                "visual": {
                    "score": result.visual_score,
                    "weight": self.visual_weight,
                    "contribution": result.visual_score * self.visual_weight
                },
                "liveness": {
                    "score": result.liveness_score,
                    "weight": self.liveness_weight,
                    "contribution": result.liveness_score * self.liveness_weight
                },
                "audio": {
                    "score": result.audio_score,
                    "weight": self.audio_weight,
                    "contribution": result.audio_score * self.audio_weight
                }
            },
            "alert": {
                "triggered": result.is_alert,
                "threshold": self.alert_threshold,
                "message": result.alert_message
            }
        }