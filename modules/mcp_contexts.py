"""
MCP Context Definitions for Kavalan Lite

This project uses a lightweight MCP-style context separation internally
to keep visual, audio, and decision reasoning isolated and auditable.

Each context defines:
- Inputs: What data it accepts
- Constraints: Assumptions, limits, invariants
- Expected outputs: Structure and meaning

Contexts are immutable once created and passed explicitly between modules.
They contain NO business logic, perform NO orchestration, and have NO
knowledge of other contexts internally.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass(frozen=True)
class VisualAuthorityContext:
    """
    MCP Context: Visual Authority Reasoning
    
    Wraps outputs from video_processor's visual analysis.
    Isolates reasoning about uniform/authority visual signals.
    
    Inputs:
        - visual_score: Suspicion score from uniform analysis (0-10)
        - uniform_detected: Whether any uniform was visually detected
        - uniform_agency_claimed: Agency name if uniform detected (e.g., "CBI", "Police")
        - uniform_is_verified_fake: Whether uniform fails forensic verification
        - anomalies: List of visual anomalies detected
        - confidence: Model confidence in visual analysis (0-1)
    
    Constraints:
        - visual_score must be in range [0, 10]
        - confidence must be in range [0, 1]
        - If uniform_is_verified_fake is True, uniform_detected must also be True
        - This context does NOT perform analysis, only holds results
    
    Expected Outputs (when consumed):
        - Provides visual authority signals to fusion decision
        - Uniform verification status for evidence logging
    """
    visual_score: float
    uniform_detected: bool
    uniform_agency_claimed: str
    uniform_is_verified_fake: bool
    anomalies: tuple  # Immutable list of anomaly strings
    confidence: float
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Validate constraints on creation"""
        object.__setattr__(self, 'visual_score', max(0.0, min(10.0, self.visual_score)))
        object.__setattr__(self, 'confidence', max(0.0, min(1.0, self.confidence)))


@dataclass(frozen=True)
class AudioCoercionContext:
    """
    MCP Context: Audio/Language Coercion Reasoning
    
    Wraps outputs from audio_processor's transcription and keyword analysis.
    Isolates reasoning about verbal coercion and threat signals.
    
    Inputs:
        - audio_score: Suspicion score from keyword analysis (0-10)
        - coercion_detected: Whether coercion keywords found
        - financial_demand_detected: Whether financial demand keywords found
        - authority_claim_detected: Whether authority claim keywords found
        - detected_categories: Categories of detected keywords
        - transcript_snippet: Recent transcript for audit (last N chars)
        - confidence: Model confidence in transcription (0-1)
    
    Constraints:
        - audio_score must be in range [0, 10]
        - confidence must be in range [0, 1]
        - transcript_snippet should be bounded (audit only, not full history)
        - This context does NOT perform transcription, only holds results
    
    Expected Outputs (when consumed):
        - Provides audio coercion signals to fusion decision
        - Keyword categories for evidence logging
    """
    audio_score: float
    coercion_detected: bool
    financial_demand_detected: bool
    authority_claim_detected: bool
    detected_categories: tuple  # Immutable list of category strings
    transcript_snippet: str
    confidence: float
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Validate constraints on creation"""
        object.__setattr__(self, 'audio_score', max(0.0, min(10.0, self.audio_score)))
        object.__setattr__(self, 'confidence', max(0.0, min(1.0, self.confidence)))
        # Bound transcript to last 200 chars for audit purposes
        if len(self.transcript_snippet) > 200:
            object.__setattr__(self, 'transcript_snippet', self.transcript_snippet[-200:])


@dataclass(frozen=True)
class FusionDecisionContext:
    """
    MCP Context: Fusion Decision Reasoning
    
    Consumes VisualAuthorityContext, AudioCoercionContext, and liveness signals
    to produce a final decision. This context captures the decision state,
    NOT the decision logic (which remains in FusionEngine).
    
    Inputs:
        - visual_context: VisualAuthorityContext instance
        - audio_context: AudioCoercionContext instance
        - liveness_score: Score from liveness detection (0-10)
        - is_static_spoof: Whether static spoof attack detected
        - user_stress_level: Detected stress level of user
    
    Constraints:
        - liveness_score must be in range [0, 10]
        - visual_context and audio_context must be provided (not None)
        - user_stress_level must be one of: "normal", "elevated", "high", "panic"
        - This context does NOT perform fusion, only captures inputs for fusion
    
    Expected Outputs (when consumed by FusionEngine):
        - All signals needed for weighted score fusion
        - Context for stress-aware messaging
        - Audit trail of what inputs produced the decision
    """
    visual_context: VisualAuthorityContext
    audio_context: AudioCoercionContext
    liveness_score: float
    is_static_spoof: bool
    user_stress_level: str
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Validate constraints on creation"""
        object.__setattr__(self, 'liveness_score', max(0.0, min(10.0, self.liveness_score)))
        valid_stress_levels = ("normal", "elevated", "high", "panic")
        if self.user_stress_level not in valid_stress_levels:
            object.__setattr__(self, 'user_stress_level', "normal")


def create_visual_context(visual_result) -> Optional[VisualAuthorityContext]:
    """
    Factory function to create VisualAuthorityContext from video_processor output.
    
    Args:
        visual_result: VisualResult from VideoProcessor.analyze_uniform()
        
    Returns:
        VisualAuthorityContext or None if visual_result is None
    """
    if visual_result is None:
        return None
    
    return VisualAuthorityContext(
        visual_score=visual_result.score,
        uniform_detected=visual_result.uniform_detected,
        uniform_agency_claimed=visual_result.uniform_agency_claimed,
        uniform_is_verified_fake=visual_result.is_verified_fake,
        anomalies=tuple(visual_result.anomalies) if visual_result.anomalies else (),
        confidence=visual_result.confidence
    )


def create_audio_context(audio_result) -> Optional[AudioCoercionContext]:
    """
    Factory function to create AudioCoercionContext from audio_processor output.
    
    Args:
        audio_result: AudioResult from AudioProcessor.process_audio()
        
    Returns:
        AudioCoercionContext or None if audio_result is None
    """
    if audio_result is None:
        return None
    
    keywords = audio_result.detected_keywords if audio_result.detected_keywords else {}
    
    return AudioCoercionContext(
        audio_score=audio_result.score,
        coercion_detected=bool(keywords.get('coercion')),
        financial_demand_detected=bool(keywords.get('financial')),
        authority_claim_detected=bool(keywords.get('authority')),
        detected_categories=tuple(keywords.keys()),
        transcript_snippet=audio_result.transcript or "",
        confidence=audio_result.confidence
    )


def create_fusion_context(
    visual_context: Optional[VisualAuthorityContext],
    audio_context: Optional[AudioCoercionContext],
    liveness_result
) -> FusionDecisionContext:
    """
    Factory function to create FusionDecisionContext from component contexts and liveness.
    
    Args:
        visual_context: VisualAuthorityContext (or None for default)
        audio_context: AudioCoercionContext (or None for default)
        liveness_result: LivenessResult from VideoProcessor.process_liveness()
        
    Returns:
        FusionDecisionContext ready for fusion engine
    """
    # Create default contexts if None
    if visual_context is None:
        visual_context = VisualAuthorityContext(
            visual_score=0.0,
            uniform_detected=False,
            uniform_agency_claimed="",
            uniform_is_verified_fake=False,
            anomalies=(),
            confidence=0.0
        )
    
    if audio_context is None:
        audio_context = AudioCoercionContext(
            audio_score=0.0,
            coercion_detected=False,
            financial_demand_detected=False,
            authority_claim_detected=False,
            detected_categories=(),
            transcript_snippet="",
            confidence=0.0
        )
    
    # Extract liveness signals
    liveness_score = liveness_result.score if liveness_result else 0.0
    is_static_spoof = liveness_result.is_static_spoof if liveness_result else False
    user_stress_level = liveness_result.stress_level if liveness_result else "normal"
    
    return FusionDecisionContext(
        visual_context=visual_context,
        audio_context=audio_context,
        liveness_score=liveness_score,
        is_static_spoof=is_static_spoof,
        user_stress_level=user_stress_level
    )
