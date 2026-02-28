"""
Threat Fusion Engine - Combines multimodal scores into unified threat assessment
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np


@dataclass
class ThreatResult:
    """Result of threat score fusion"""
    final_score: float
    audio_score: Optional[float]
    visual_score: Optional[float]
    liveness_score: Optional[float]
    threat_level: str
    is_alert: bool
    message: str
    explanation: List[str]
    confidence: float
    timestamp: datetime
    degraded_mode: bool = False
    available_modalities: List[str] = None
    
    def __post_init__(self):
        """Initialize available_modalities list if not provided"""
        if self.available_modalities is None:
            self.available_modalities = []


@dataclass
class ThreatHistoryEntry:
    """Single entry in threat score history"""
    timestamp: datetime
    final_score: float
    audio_score: Optional[float]
    visual_score: Optional[float]
    liveness_score: Optional[float]
    threat_level: str
    is_alert: bool
    confidence: float
    degraded_mode: bool = False


class ThreatAnalyzer:
    """
    Combines audio, visual, and liveness scores into unified threat assessment.
    
    Uses weighted fusion with configurable weights for each modality.
    Implements confidence-weighted conflict resolution when modalities disagree.
    Maintains historical threat score timeline for trend analysis.
    """
    
    def __init__(
        self,
        audio_weight: float = 0.45,
        visual_weight: float = 0.35,
        liveness_weight: float = 0.20
    ):
        """
        Initialize threat analyzer with modality weights.
        
        Args:
            audio_weight: Weight for audio score (default: 0.45)
            visual_weight: Weight for visual score (default: 0.35)
            liveness_weight: Weight for liveness score (default: 0.20)
        """
        # Validate weights sum to 1.0
        total_weight = audio_weight + visual_weight + liveness_weight
        if not (0.99 <= total_weight <= 1.01):  # Allow small floating point error
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        self.weights = {
            'audio': audio_weight,
            'visual': visual_weight,
            'liveness': liveness_weight
        }
        
        self.thresholds = {
            'low': 3.0,
            'moderate': 5.0,
            'high': 7.0,
            'critical': 8.5
        }
        
        # Initialize threat score history
        self.history: List[ThreatHistoryEntry] = []
    
    def fuse_scores(
        self,
        audio: Optional[float] = None,
        visual: Optional[float] = None,
        liveness: Optional[float] = None,
        audio_confidence: float = 1.0,
        visual_confidence: float = 1.0,
        liveness_confidence: float = 1.0
    ) -> ThreatResult:
        """
        Combine modality scores with weighted fusion.
        
        Supports graceful degradation: if one or more modalities are unavailable (None),
        the system continues with available modalities and returns a partial assessment.
        
        Args:
            audio: Audio threat score [0.0, 10.0] or None if unavailable
            visual: Visual threat score [0.0, 10.0] or None if unavailable
            liveness: Liveness threat score [0.0, 10.0] or None if unavailable
            audio_confidence: Confidence in audio score [0.0, 1.0]
            visual_confidence: Confidence in visual score [0.0, 1.0]
            liveness_confidence: Confidence in liveness score [0.0, 1.0]
        
        Returns:
            ThreatResult with fused score and metadata
            
        Raises:
            ValueError: If all modalities are unavailable
        """
        # Check which modalities are available
        available_modalities = []
        if audio is not None:
            available_modalities.append('audio')
        if visual is not None:
            available_modalities.append('visual')
        if liveness is not None:
            available_modalities.append('liveness')
        
        # Require at least one modality
        if not available_modalities:
            raise ValueError("At least one modality must be available for threat assessment")
        
        # Determine if we're in degraded mode
        degraded_mode = len(available_modalities) < 3
        
        # Validate available scores
        if audio is not None:
            self._validate_score(audio, "audio")
        if visual is not None:
            self._validate_score(visual, "visual")
        if liveness is not None:
            self._validate_score(liveness, "liveness")
        
        self._validate_confidence(audio_confidence, "audio_confidence")
        self._validate_confidence(visual_confidence, "visual_confidence")
        self._validate_confidence(liveness_confidence, "liveness_confidence")
        
        # Calculate fused score with available modalities
        if degraded_mode:
            final_score = self._partial_fusion(
                audio, visual, liveness,
                audio_confidence, visual_confidence, liveness_confidence
            )
        else:
            # All modalities available - use standard logic
            # Check for conflicting scores (variance > 4.0)
            scores = [audio, visual, liveness]
            variance = float(np.var(scores))
            
            if variance > 4.0:
                # Apply confidence-weighted conflict resolution
                final_score = self._confidence_weighted_fusion(
                    audio, visual, liveness,
                    audio_confidence, visual_confidence, liveness_confidence
                )
            else:
                # Use standard weighted average
                final_score = (
                    audio * self.weights['audio'] +
                    visual * self.weights['visual'] +
                    liveness * self.weights['liveness']
                )
        
        # Ensure final score is in valid range [0.0, 10.0]
        final_score = max(0.0, min(final_score, 10.0))
        
        # Determine threat level
        threat_level = self._determine_threat_level(final_score)
        
        # Determine if alert should be triggered
        is_alert = final_score >= self.thresholds['high']
        
        # Generate message (include degraded mode warning if applicable)
        message = self._generate_message(threat_level, is_alert, degraded_mode, available_modalities)
        
        # Generate explanation
        explanation = self._generate_explanation(audio, visual, liveness, degraded_mode, available_modalities)
        
        # Calculate overall confidence (lower in degraded mode)
        confidence = self._calculate_confidence(
            audio, visual, liveness,
            audio_confidence, visual_confidence, liveness_confidence,
            degraded_mode
        )
        
        return ThreatResult(
            final_score=final_score,
            audio_score=audio,
            visual_score=visual,
            liveness_score=liveness,
            threat_level=threat_level,
            is_alert=is_alert,
            message=message,
            explanation=explanation,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            degraded_mode=degraded_mode,
            available_modalities=available_modalities
        )
    
    def add_to_history(self, result: ThreatResult) -> None:
        """
        Add a threat result to the historical timeline.
        
        Args:
            result: ThreatResult to add to history
        """
        entry = ThreatHistoryEntry(
            timestamp=result.timestamp,
            final_score=result.final_score,
            audio_score=result.audio_score,
            visual_score=result.visual_score,
            liveness_score=result.liveness_score,
            threat_level=result.threat_level,
            is_alert=result.is_alert,
            confidence=result.confidence,
            degraded_mode=result.degraded_mode
        )
        self.history.append(entry)
    
    def get_history(
        self,
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[ThreatHistoryEntry]:
        """
        Retrieve threat score history.
        
        Args:
            limit: Maximum number of entries to return (most recent first)
            since: Only return entries after this timestamp
        
        Returns:
            List of ThreatHistoryEntry objects
        """
        filtered_history = self.history
        
        # Filter by timestamp if provided
        if since is not None:
            filtered_history = [
                entry for entry in filtered_history
                if entry.timestamp >= since
            ]
        
        # Sort by timestamp (most recent first)
        sorted_history = sorted(
            filtered_history,
            key=lambda x: x.timestamp,
            reverse=True
        )
        
        # Apply limit if provided
        if limit is not None:
            sorted_history = sorted_history[:limit]
        
        return sorted_history
    
    def get_max_threat_score(self) -> Optional[float]:
        """
        Get the maximum threat score from history.
        
        Returns:
            Maximum threat score, or None if history is empty
        """
        if not self.history:
            return None
        
        return max(entry.final_score for entry in self.history)
    
    def get_alert_count(self) -> int:
        """
        Get the total number of alerts triggered in history.
        
        Returns:
            Count of alerts (entries with is_alert=True)
        """
        return sum(1 for entry in self.history if entry.is_alert)
    
    def clear_history(self) -> None:
        """Clear all historical threat scores."""
        self.history.clear()
    
    def _validate_score(self, score: float, name: str) -> None:
        """Validate score is in range [0.0, 10.0]"""
        if not (0.0 <= score <= 10.0):
            raise ValueError(f"{name} score must be in [0.0, 10.0], got {score}")
    
    def _validate_confidence(self, confidence: float, name: str) -> None:
        """Validate confidence is in range [0.0, 1.0]"""
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"{name} must be in [0.0, 1.0], got {confidence}")
    
    def _determine_threat_level(self, score: float) -> str:
        """Determine threat level based on score thresholds"""
        if score >= self.thresholds['critical']:
            return 'critical'
        elif score >= self.thresholds['high']:
            return 'high'
        elif score >= self.thresholds['moderate']:
            return 'moderate'
        else:
            return 'low'
    
    def _generate_message(self, threat_level: str, is_alert: bool, degraded_mode: bool = False, available_modalities: List[str] = None) -> str:
        """Generate human-readable threat message with degraded mode warning"""
        messages = {
            'critical': "CRITICAL THREAT: Disconnect immediately",
            'high': "HIGH RISK: Potential scam detected",
            'moderate': "MODERATE: Suspicious activity",
            'low': "Safe - No threats detected"
        }
        base_message = messages.get(threat_level, "Unknown threat level")
        
        if degraded_mode:
            if available_modalities:
                modalities_str = ", ".join(available_modalities)
                base_message += f" [DEGRADED MODE: Only {modalities_str} analysis available]"
            else:
                base_message += " [DEGRADED MODE: Limited analysis available]"
        
        return base_message
    
    def _generate_explanation(
        self,
        audio: Optional[float],
        visual: Optional[float],
        liveness: Optional[float],
        degraded_mode: bool = False,
        available_modalities: List[str] = None
    ) -> List[str]:
        """Generate human-readable threat explanation"""
        explanations = []
        
        # Add degraded mode warning first if applicable
        if degraded_mode:
            unavailable = []
            if audio is None:
                unavailable.append("audio")
            if visual is None:
                unavailable.append("visual")
            if liveness is None:
                unavailable.append("liveness")
            
            if unavailable:
                unavailable_str = ", ".join(unavailable)
                explanations.append(f"WARNING: {unavailable_str} analysis unavailable - partial assessment only")
        
        # Add modality-specific explanations for available modalities
        if audio is not None:
            if audio > 7.0:
                explanations.append("Multiple scam keywords detected in conversation")
            elif audio > 5.0:
                explanations.append("Suspicious keywords detected in audio")
        
        if visual is not None:
            if visual > 6.0:
                explanations.append("Suspicious uniform or badge detected")
            elif visual > 4.0:
                explanations.append("Visual threat indicators present")
        
        if liveness is not None:
            if liveness > 7.0:
                explanations.append("Caller shows signs of stress or distress")
            elif liveness < 3.0:
                explanations.append("Potential deepfake or pre-recorded video detected")
        
        if audio is not None and visual is not None and audio > 5.0 and visual > 5.0:
            explanations.append("Combined audio and visual threat indicators")
        
        if len(explanations) <= (1 if degraded_mode else 0):
            explanations.append("No significant threats detected")
        
        return explanations
    
    def _calculate_confidence(
        self,
        audio: Optional[float],
        visual: Optional[float],
        liveness: Optional[float],
        audio_confidence: float,
        visual_confidence: float,
        liveness_confidence: float,
        degraded_mode: bool = False
    ) -> float:
        """
        Calculate confidence in threat assessment.
        
        Higher confidence when:
        1. Modalities agree (low variance)
        2. Individual confidence scores are high
        3. All modalities are available (not in degraded mode)
        """
        # Collect available scores
        available_scores = []
        if audio is not None:
            available_scores.append(audio)
        if visual is not None:
            available_scores.append(visual)
        if liveness is not None:
            available_scores.append(liveness)
        
        # Calculate variance of available scores (low variance = high agreement)
        if len(available_scores) > 1:
            variance = float(np.var(available_scores))
            # Normalize variance to [0, 1] range (max variance for [0,10] range is 33.33)
            agreement_confidence = 1.0 - min(variance / 33.33, 1.0)
        else:
            # Only one modality - no agreement to measure
            agreement_confidence = 0.5
        
        # Calculate weighted average of individual confidences for available modalities
        total_weight = 0.0
        weighted_confidence_sum = 0.0
        
        if audio is not None:
            total_weight += self.weights['audio']
            weighted_confidence_sum += audio_confidence * self.weights['audio']
        if visual is not None:
            total_weight += self.weights['visual']
            weighted_confidence_sum += visual_confidence * self.weights['visual']
        if liveness is not None:
            total_weight += self.weights['liveness']
            weighted_confidence_sum += liveness_confidence * self.weights['liveness']
        
        avg_confidence = weighted_confidence_sum / total_weight if total_weight > 0 else 0.5
        
        # Combine agreement and individual confidences
        overall_confidence = (agreement_confidence + avg_confidence) / 2.0
        
        # Apply degradation penalty (reduce confidence when in degraded mode)
        if degraded_mode:
            # Reduce confidence based on number of missing modalities
            num_available = len(available_scores)
            degradation_factor = num_available / 3.0  # 1/3 for 1 modality, 2/3 for 2 modalities
            overall_confidence *= degradation_factor
        
        # Ensure confidence is in valid range [0.0, 1.0]
        return max(0.0, min(overall_confidence, 1.0))
    
    def _confidence_weighted_fusion(
        self,
        audio: Optional[float],
        visual: Optional[float],
        liveness: Optional[float],
        audio_confidence: float,
        visual_confidence: float,
        liveness_confidence: float
    ) -> float:
        """
        Apply confidence-weighted averaging when modality scores conflict.
        
        When variance > 4.0, higher-confidence scores have greater influence.
        Handles None values for unavailable modalities.
        
        Args:
            audio: Audio threat score or None
            visual: Visual threat score or None
            liveness: Liveness threat score or None
            audio_confidence: Confidence in audio score
            visual_confidence: Confidence in visual score
            liveness_confidence: Confidence in liveness score
        
        Returns:
            Confidence-weighted fused score
        """
        # Combine base weights with confidence scores for available modalities
        audio_weight = self.weights['audio'] * audio_confidence if audio is not None else 0.0
        visual_weight = self.weights['visual'] * visual_confidence if visual is not None else 0.0
        liveness_weight = self.weights['liveness'] * liveness_confidence if liveness is not None else 0.0
        
        # Normalize weights to sum to 1.0
        total_weight = audio_weight + visual_weight + liveness_weight
        
        if total_weight == 0.0:
            # All confidences are zero - fall back to equal weighting of available modalities
            available_scores = []
            if audio is not None:
                available_scores.append(audio)
            if visual is not None:
                available_scores.append(visual)
            if liveness is not None:
                available_scores.append(liveness)
            return sum(available_scores) / len(available_scores) if available_scores else 0.0
        
        audio_weight /= total_weight
        visual_weight /= total_weight
        liveness_weight /= total_weight
        
        # Calculate confidence-weighted score
        fused_score = 0.0
        if audio is not None:
            fused_score += audio * audio_weight
        if visual is not None:
            fused_score += visual * visual_weight
        if liveness is not None:
            fused_score += liveness * liveness_weight
        
        return fused_score
    
    def _partial_fusion(
        self,
        audio: Optional[float],
        visual: Optional[float],
        liveness: Optional[float],
        audio_confidence: float,
        visual_confidence: float,
        liveness_confidence: float
    ) -> float:
        """
        Perform fusion with partial modalities (degraded mode).
        
        Reweights available modalities to sum to 1.0 and applies weighted averaging.
        
        Args:
            audio: Audio threat score or None
            visual: Visual threat score or None
            liveness: Liveness threat score or None
            audio_confidence: Confidence in audio score
            visual_confidence: Confidence in visual score
            liveness_confidence: Confidence in liveness score
        
        Returns:
            Fused score based on available modalities
        """
        # Calculate total weight of available modalities
        total_weight = 0.0
        if audio is not None:
            total_weight += self.weights['audio']
        if visual is not None:
            total_weight += self.weights['visual']
        if liveness is not None:
            total_weight += self.weights['liveness']
        
        if total_weight == 0.0:
            return 0.0
        
        # Normalize weights for available modalities
        audio_weight = self.weights['audio'] / total_weight if audio is not None else 0.0
        visual_weight = self.weights['visual'] / total_weight if visual is not None else 0.0
        liveness_weight = self.weights['liveness'] / total_weight if liveness is not None else 0.0
        
        # Calculate weighted score
        fused_score = 0.0
        if audio is not None:
            fused_score += audio * audio_weight
        if visual is not None:
            fused_score += visual * visual_weight
        if liveness is not None:
            fused_score += liveness * liveness_weight
        
        return fused_score
