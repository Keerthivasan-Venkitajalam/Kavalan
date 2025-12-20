"""
Fusion Engine for Kavalan Lite
Combines scores from visual, liveness, and audio analysis modules

Enhanced with:
- Dynamic weighting based on confidence
- Stress-aware response generation
- Evidence-based alert messaging
- Cluster logic (require multiple signals)
- MCP context support for auditable decision inputs
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Optional, TYPE_CHECKING
import logging
import time

# Import MCP contexts for type hints (avoid circular imports)
if TYPE_CHECKING:
    from modules.mcp_contexts import FusionDecisionContext

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
    # Enhanced fields
    alert_level: str = "none"  # "none", "low", "moderate", "high", "critical"
    threat_types: List[str] = field(default_factory=list)
    is_user_distressed: bool = False
    recommended_action: str = "monitor"
    explanation: str = ""
    confidence: float = 0.0
    
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


@dataclass
class ThreatContext:
    """Contextual information about detected threats"""
    uniform_detected: bool = False
    uniform_is_fake: bool = False
    agency_claimed: str = ""
    coercion_detected: bool = False
    financial_demand: bool = False
    authority_claim: bool = False
    user_stress_level: str = "normal"
    is_static_spoof: bool = False
    transcript_keywords: List[str] = field(default_factory=list)

class FusionEngine:
    """
    Combines scores from multiple analysis modules using weighted average
    
    Enhanced with:
    - Cluster logic: Require multiple signals for high alerts
    - Confidence-based dynamic weighting
    - Stress-aware response generation
    - Evidence-based messaging
    
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
    
    # Alert level thresholds
    LEVEL_CRITICAL: float = 9.0
    LEVEL_HIGH: float = 8.0
    LEVEL_MODERATE: float = 6.0
    LEVEL_LOW: float = 3.0
    
    # Legal explainability messages
    LEGAL_EXPLANATIONS = {
        "digital_arrest": "⚖️ 'Digital Arrest' is NOT a legal concept in India. No law enforcement agency conducts arrests or interrogations via video call.",
        "money_demand": "💰 Legitimate law enforcement NEVER demands money transfers during investigation. This is financial fraud.",
        "video_interrogation": "📹 Real judicial proceedings do not occur on video calls. Section 41A CrPC requires physical written notice.",
        "uniform_fake": "👮 The uniform shown does not match official regulations for the claimed agency. CBI/ED officers wear formal business attire, not khaki.",
        "stay_on_call": "📞 You are NOT legally obligated to stay on a video call. Real police cannot force continuous video surveillance.",
    }
    
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
        
        # Track threat history for cluster detection
        self._threat_history: List[Dict] = []
        
        logger.info(f"FusionEngine initialized with weights: V={self.visual_weight:.2f}, "
                   f"L={self.liveness_weight:.2f}, A={self.audio_weight:.2f}, "
                   f"threshold={self.alert_threshold}")
    
    def _clamp_score(self, score: float) -> float:
        """Ensure score is in valid range [0, 10]"""
        return max(0.0, min(10.0, score))
    
    def _check_cluster_logic(self, visual: float, liveness: float, audio: float, 
                             context: ThreatContext = None) -> Tuple[bool, List[str]]:
        """
        Check if multiple threat signals are present (cluster logic)
        
        High alerts should only trigger on CLUSTERS of signals, not single signals.
        
        Returns:
            Tuple of (is_cluster, list of detected threat types)
        """
        threat_types = []
        signal_count = 0
        
        # Check visual threat (uniform detected)
        if visual >= 6.0:
            signal_count += 1
            if context and context.uniform_is_fake:
                threat_types.append("fake_uniform")
            elif context and context.uniform_detected:
                threat_types.append("suspicious_uniform")
        
        # Check liveness threat (spoof detection)
        if liveness >= 6.0:
            signal_count += 1
            if context and context.is_static_spoof:
                threat_types.append("video_injection")
            else:
                threat_types.append("liveness_concern")
        
        # Check audio threat (keywords)
        if audio >= 6.0:
            signal_count += 1
            if context:
                if context.coercion_detected:
                    threat_types.append("coercion")
                if context.financial_demand:
                    threat_types.append("financial_demand")
                if context.authority_claim:
                    threat_types.append("authority_claim")
        
        # Cluster = 2+ different threat types
        is_cluster = signal_count >= 2
        
        return is_cluster, threat_types
    
    def _generate_explanation(self, threat_types: List[str], context: ThreatContext = None) -> str:
        """Generate user-friendly legal explanation for the threat"""
        explanations = []
        
        if "fake_uniform" in threat_types or "suspicious_uniform" in threat_types:
            explanations.append(self.LEGAL_EXPLANATIONS["uniform_fake"])
        
        if "financial_demand" in threat_types:
            explanations.append(self.LEGAL_EXPLANATIONS["money_demand"])
        
        if "coercion" in threat_types:
            explanations.append(self.LEGAL_EXPLANATIONS["stay_on_call"])
        
        if "authority_claim" in threat_types:
            explanations.append(self.LEGAL_EXPLANATIONS["digital_arrest"])
        
        if not explanations:
            explanations.append(self.LEGAL_EXPLANATIONS["video_interrogation"])
        
        return " ".join(explanations)
    
    def _get_stress_aware_message(self, alert_level: str, is_distressed: bool, 
                                   threat_types: List[str]) -> str:
        """
        Generate alert message that's sensitive to user's stress state
        
        If user is distressed, use calming language instead of alarming language.
        """
        if is_distressed:
            # Calming, supportive messages for distressed users
            if alert_level == "critical":
                return "🤗 We detect you may be stressed. Take a deep breath. This appears to be a scam call. You can safely disconnect - we're here to help."
            elif alert_level == "high":
                return "💚 Stay calm. We've detected concerning patterns in this call. It's okay to end the call if you feel uncomfortable."
            else:
                return "😊 You seem worried. Remember: No legitimate authority conducts business this way. Take your time."
        else:
            # Standard alert messages
            if alert_level == "critical":
                return "🚨 CRITICAL ALERT: High probability Digital Arrest scam! DISCONNECT IMMEDIATELY!"
            elif alert_level == "high":
                return "⚠️ HIGH ALERT: Potential Digital Arrest scam detected. Consider disconnecting."
            elif alert_level == "moderate":
                return "⚡ MODERATE: Suspicious activity detected. Exercise caution."
            elif alert_level == "low":
                return "✓ Low risk. Continue with normal caution."
            else:
                return "✅ No significant threats detected."
    
    def fuse_scores(
        self, 
        visual: float, 
        liveness: float, 
        audio: float,
        context: ThreatContext = None
    ) -> FusionResult:
        """
        Combine scores using weighted average with enhanced context awareness
        
        Args:
            visual: Visual analysis score (0-10)
            liveness: Liveness detection score (0-10)
            audio: Audio analysis score (0-10)
            context: Optional threat context for richer analysis
            
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
        
        # Apply cluster logic boost/penalty
        is_cluster, threat_types = self._check_cluster_logic(visual, liveness, audio, context)
        
        # If multiple threat types detected, boost confidence
        if is_cluster:
            # Boost score by up to 1.5 for strong clusters
            cluster_boost = min(1.5, len(threat_types) * 0.5)
            final_score = min(10.0, final_score + cluster_boost)
            confidence = 0.9
        else:
            # Single signal - still allow alerts but with lower confidence
            confidence = 0.7
            # Single strong signals can still trigger alerts (no aggressive capping)
        
        # Ensure final score is in valid range
        final_score = self._clamp_score(final_score)
        
        # Determine alert level
        if final_score >= self.LEVEL_CRITICAL:
            alert_level = "critical"
        elif final_score >= self.LEVEL_HIGH:
            alert_level = "high"
        elif final_score >= self.LEVEL_MODERATE:
            alert_level = "moderate"
        elif final_score >= self.LEVEL_LOW:
            alert_level = "low"
        else:
            alert_level = "none"
        
        # Check if user is distressed
        is_distressed = context.user_stress_level in ["high", "panic"] if context else False
        
        # Generate stress-aware message
        alert_message = self._get_stress_aware_message(alert_level, is_distressed, threat_types)
        
        # Generate legal explanation
        explanation = self._generate_explanation(threat_types, context)
        
        # Determine recommended action
        if alert_level in ["critical", "high"]:
            recommended_action = "disconnect"
        elif alert_level == "moderate":
            recommended_action = "warn"
        else:
            recommended_action = "monitor"
        
        # Check if alert should be triggered
        is_alert = final_score >= self.alert_threshold
        
        logger.debug(f"Fusion: V={visual:.2f}*{self.visual_weight:.2f} + "
                    f"L={liveness:.2f}*{self.liveness_weight:.2f} + "
                    f"A={audio:.2f}*{self.audio_weight:.2f} = {final_score:.2f} "
                    f"[cluster={is_cluster}, types={threat_types}]")
        
        return FusionResult(
            final_score=final_score,
            visual_score=visual,
            liveness_score=liveness,
            audio_score=audio,
            is_alert=is_alert,
            alert_message=alert_message,
            alert_level=alert_level,
            threat_types=threat_types,
            is_user_distressed=is_distressed,
            recommended_action=recommended_action,
            explanation=explanation,
            confidence=confidence
        )
    
    def check_alert(self, score: float) -> Tuple[bool, str]:
        """
        Check if score triggers alert and generate appropriate message
        
        Args:
            score: Final fusion score (0-10)
            
        Returns:
            Tuple of (is_alert: bool, message: str)
        """
        if score >= self.alert_threshold:
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
                message = "✅ No significant threats detected."
            
            return False, message
    
    def fuse_scores_simple(
        self, 
        visual: float, 
        liveness: float, 
        audio: float
    ) -> FusionResult:
        """
        Simple fusion without context (backward compatible)
        
        Args:
            visual: Visual analysis score (0-10)
            liveness: Liveness detection score (0-10)
            audio: Audio analysis score (0-10)
            
        Returns:
            FusionResult with combined score and alert status
        """
        return self.fuse_scores(visual, liveness, audio, context=None)
    
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
    
    def fuse_from_context(self, fusion_context: "FusionDecisionContext") -> FusionResult:
        """
        Fuse scores from an explicit MCP FusionDecisionContext.
        
        This method provides an auditable entry point where all decision
        inputs are captured in an immutable context before fusion.
        
        Args:
            fusion_context: FusionDecisionContext containing visual, audio,
                           and liveness signals
            
        Returns:
            FusionResult with combined score and alert status
        """
        # Extract scores from MCP contexts
        visual_score = fusion_context.visual_context.visual_score
        audio_score = fusion_context.audio_context.audio_score
        liveness_score = fusion_context.liveness_score
        
        # Build ThreatContext from MCP contexts for existing fusion logic
        context = ThreatContext(
            uniform_detected=fusion_context.visual_context.uniform_detected,
            uniform_is_fake=fusion_context.visual_context.uniform_is_verified_fake,
            agency_claimed=fusion_context.visual_context.uniform_agency_claimed,
            coercion_detected=fusion_context.audio_context.coercion_detected,
            financial_demand=fusion_context.audio_context.financial_demand_detected,
            authority_claim=fusion_context.audio_context.authority_claim_detected,
            user_stress_level=fusion_context.user_stress_level,
            is_static_spoof=fusion_context.is_static_spoof,
            transcript_keywords=list(fusion_context.audio_context.detected_categories)
        )
        
        # Delegate to existing fusion logic
        return self.fuse_scores(
            visual=visual_score,
            liveness=liveness_score,
            audio=audio_score,
            context=context
        )