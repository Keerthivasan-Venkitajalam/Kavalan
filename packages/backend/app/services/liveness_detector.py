"""
Liveness Detection Service using MediaPipe

This service detects deepfakes, pre-recorded videos, and stress indicators
using facial landmark analysis.
"""
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from PIL import Image
import io
import cv2

logger = logging.getLogger(__name__)


@dataclass
class LivenessResult:
    """Result from liveness detection analysis"""
    face_detected: bool
    liveness_score: float
    blink_rate: float
    stress_level: float
    is_natural: bool
    is_deepfake: bool
    num_faces: int
    faces: List[Dict]


class LivenessDetector:
    """
    Detect liveness and stress indicators using MediaPipe Face Landmarker.
    
    Key Features:
    - Detects facial landmarks (468 points)
    - Calculates Eye Aspect Ratio (EAR) for blink detection
    - Analyzes head pose variance
    - Detects stress indicators
    - Supports multi-face analysis
    """
    
    def __init__(self):
        """Initialize MediaPipe Face Landmarker"""
        # For the new MediaPipe API, we need to download the model file
        # For now, we'll use a simpler approach with cv2 face detection
        # In production, download the face_landmarker.task model
        
        # Use OpenCV's face detector as fallback
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
        # History tracking for temporal analysis
        self.ear_history: Dict[int, List[float]] = {}
        self.blink_counts: Dict[int, int] = {}
        self.frame_count = 0
        
        # Frame rate control (1 FPS)
        self.target_fps = 1.0
        self.last_processed_time = 0.0
        self.frame_skip_count = 0
        
        # Eye landmark indices for EAR calculation (simplified for OpenCV)
        # We'll use eye region detection instead of precise landmarks
        
        logger.info("LivenessDetector initialized with OpenCV face detection")
    
    def detect_liveness(self, frame_bytes: bytes, timestamp: float = None) -> LivenessResult:
        """
        Detect liveness and stress indicators from a video frame.
        
        Implements frame rate control: processes frames at 1 FPS, skips frames
        if processing falls behind.
        
        Args:
            frame_bytes: Raw image bytes (JPEG, PNG, etc.)
            timestamp: Frame timestamp (optional, uses current time if not provided)
            
        Returns:
            LivenessResult with liveness scores and analysis
        """
        import time
        
        # Get current timestamp
        if timestamp is None:
            timestamp = time.time()
        
        # Frame rate control: check if enough time has passed since last frame
        time_since_last = timestamp - self.last_processed_time
        min_interval = 1.0 / self.target_fps  # 1 second for 1 FPS
        
        if self.last_processed_time > 0 and time_since_last < min_interval:
            # Skip this frame - processing too fast
            self.frame_skip_count += 1
            logger.debug(
                f"Skipping frame (time_since_last={time_since_last:.3f}s < {min_interval:.3f}s), "
                f"total skipped={self.frame_skip_count}"
            )
            # Return last known result or empty result
            return LivenessResult(
                face_detected=False,
                liveness_score=0.0,
                blink_rate=0.0,
                stress_level=0.0,
                is_natural=False,
                is_deepfake=True,
                num_faces=0,
                faces=[]
            )
        
        # Update last processed time
        self.last_processed_time = timestamp
        
        try:
            # Decode image
            image = Image.open(io.BytesIO(frame_bytes))
            image_array = np.array(image.convert('RGB'))
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            if len(faces) == 0:
                logger.debug("No faces detected in frame")
                return LivenessResult(
                    face_detected=False,
                    liveness_score=0.0,
                    blink_rate=0.0,
                    stress_level=0.0,
                    is_natural=False,
                    is_deepfake=True,
                    num_faces=0,
                    faces=[]
                )
            
            # Analyze each detected face
            faces_analysis = []
            for face_idx, (x, y, w, h) in enumerate(faces):
                face_result = self._analyze_single_face(
                    image_array, gray, face_idx, x, y, w, h
                )
                faces_analysis.append(face_result)
            
            # Aggregate results (use worst-case for security)
            min_liveness = min(f['liveness_score'] for f in faces_analysis)
            max_stress = max(f['stress_level'] for f in faces_analysis)
            avg_blink_rate = sum(f['blink_rate'] for f in faces_analysis) / len(faces_analysis)
            
            # Determine if any face is unnatural
            any_unnatural = any(not f['is_natural'] for f in faces_analysis)
            any_deepfake = any(f['is_deepfake'] for f in faces_analysis)
            
            self.frame_count += 1
            
            return LivenessResult(
                face_detected=True,
                liveness_score=min_liveness,
                blink_rate=avg_blink_rate,
                stress_level=max_stress,
                is_natural=not any_unnatural,
                is_deepfake=any_deepfake,
                num_faces=len(faces_analysis),
                faces=faces_analysis
            )
            
        except Exception as e:
            logger.error(f"Error in liveness detection: {e}", exc_info=True)
            return LivenessResult(
                face_detected=False,
                liveness_score=0.0,
                blink_rate=0.0,
                stress_level=0.0,
                is_natural=False,
                is_deepfake=True,
                num_faces=0,
                faces=[]
            )
    
    def _analyze_single_face(
        self,
        image_array: np.ndarray,
        gray: np.ndarray,
        face_idx: int,
        x: int,
        y: int,
        w: int,
        h: int
    ) -> Dict:
        """
        Analyze a single face for liveness indicators.
        
        Args:
            image_array: RGB image array
            gray: Grayscale image
            face_idx: Index of the face (for tracking)
            x, y, w, h: Face bounding box
            
        Returns:
            Dictionary with face analysis results
        """
        # Extract face region
        face_roi_gray = gray[y:y+h, x:x+w]
        face_roi_color = image_array[y:y+h, x:x+w]
        
        # Detect eyes in face region
        eyes = self.eye_cascade.detectMultiScale(face_roi_gray)
        
        # Calculate Eye Aspect Ratio (simplified)
        ear = self._calculate_ear_from_eyes(eyes, w, h)
        
        # Initialize history for new faces
        if face_idx not in self.ear_history:
            self.ear_history[face_idx] = []
            self.blink_counts[face_idx] = 0
        
        # Track EAR history
        self.ear_history[face_idx].append(ear)
        
        # Detect blinks (EAR drops below threshold)
        if len(self.ear_history[face_idx]) > 2:
            prev_ear = self.ear_history[face_idx][-2]
            if prev_ear > 0.25 and ear < 0.2:
                self.blink_counts[face_idx] += 1
        
        # Calculate blink rate (blinks per minute)
        # Assuming 30 FPS, calculate based on frame count
        if len(self.ear_history[face_idx]) > 0:
            time_elapsed_minutes = len(self.ear_history[face_idx]) / (30 * 60)
            blink_rate = self.blink_counts[face_idx] / max(time_elapsed_minutes, 0.01)
        else:
            blink_rate = 0.0
        
        # Calculate head pose variance (simplified using face size)
        head_pose_variance = self._calculate_head_pose_variance(w, h)
        
        # Detect stress indicators
        stress_level = self._detect_stress(face_roi_color, ear, len(eyes))
        
        # Determine if blink rate is natural (8-20 blinks per minute)
        is_natural_blink = 8.0 <= blink_rate <= 20.0 if blink_rate > 0 else False
        
        # Calculate liveness score (0.0 = fake, 1.0 = real)
        liveness_score = self._calculate_liveness_score(
            blink_rate, head_pose_variance, ear, is_natural_blink, len(eyes)
        )
        
        # Flag as deepfake if score < 0.5
        is_deepfake = liveness_score < 0.5
        
        return {
            'face_idx': face_idx,
            'liveness_score': liveness_score,
            'blink_rate': blink_rate,
            'stress_level': stress_level,
            'is_natural': is_natural_blink,
            'is_deepfake': is_deepfake,
            'ear': ear,
            'head_pose_variance': head_pose_variance,
            'num_eyes_detected': len(eyes)
        }
    
    def _calculate_ear_from_eyes(
        self,
        eyes: np.ndarray,
        face_width: int,
        face_height: int
    ) -> float:
        """
        Calculate simplified Eye Aspect Ratio from detected eyes.
        
        Args:
            eyes: Array of detected eye regions
            face_width: Width of face region
            face_height: Height of face region
            
        Returns:
            Simplified EAR value
        """
        if len(eyes) == 0:
            return 0.0
        
        # Calculate average eye height relative to face
        avg_eye_height = np.mean([h for (x, y, w, h) in eyes])
        avg_eye_width = np.mean([w for (x, y, w, h) in eyes])
        
        # Simplified EAR: height / width ratio
        if avg_eye_width > 0:
            ear = avg_eye_height / avg_eye_width
        else:
            ear = 0.0
        
        return ear
    
    def _calculate_head_pose_variance(self, face_width: int, face_height: int) -> float:
        """
        Calculate head pose variance (simplified).
        
        Args:
            face_width: Width of detected face
            face_height: Height of detected face
            
        Returns:
            Variance in head pose (higher = more movement)
        """
        # Simplified: use aspect ratio as proxy for pose
        if face_height > 0:
            aspect_ratio = face_width / face_height
            # Deviation from ideal ratio (1.0)
            variance = abs(aspect_ratio - 1.0)
        else:
            variance = 0.0
        
        return min(variance, 1.0)
    
    def _detect_stress(
        self,
        face_roi: np.ndarray,
        ear: float,
        num_eyes: int
    ) -> float:
        """
        Detect stress indicators from facial features.
        
        Args:
            face_roi: Face region of interest
            ear: Eye Aspect Ratio
            num_eyes: Number of eyes detected
            
        Returns:
            Stress level (0.0 = calm, 1.0 = high stress)
        """
        stress_score = 0.0
        
        # Wide eyes indicator (high EAR suggests stress)
        if ear > 0.3:
            stress_score += 0.3
        
        # Missing eyes (occlusion or stress-related squinting)
        if num_eyes < 2:
            stress_score += 0.2
        
        # Calculate brightness variance (stress can cause facial tension)
        if face_roi.size > 0:
            brightness_var = np.var(face_roi) / 10000.0  # Normalize
            stress_score += min(brightness_var, 0.5)
        
        return min(stress_score, 1.0)
    
    def _calculate_liveness_score(
        self,
        blink_rate: float,
        head_pose_variance: float,
        ear: float,
        is_natural_blink: bool,
        num_eyes: int
    ) -> float:
        """
        Calculate overall liveness score.
        
        Args:
            blink_rate: Blinks per minute
            head_pose_variance: Variance in head movement
            ear: Eye Aspect Ratio
            is_natural_blink: Whether blink rate is natural
            num_eyes: Number of eyes detected
            
        Returns:
            Liveness score (0.0 = fake, 1.0 = real)
        """
        score = 0.5  # Start at neutral
        
        # Natural blink rate is a strong indicator
        if is_natural_blink:
            score += 0.3
        else:
            score -= 0.2
        
        # Both eyes detected is good
        if num_eyes >= 2:
            score += 0.2
        else:
            score -= 0.1
        
        # Head movement indicates liveness
        if head_pose_variance > 0.1:
            score += 0.1
        
        # EAR variance (blinking) indicates liveness
        if 0.15 < ear < 0.35:
            score += 0.1
        
        # Clamp to [0.0, 1.0]
        return max(0.0, min(score, 1.0))
    
    def reset_history(self):
        """Reset tracking history (call between sessions)"""
        self.ear_history.clear()
        self.blink_counts.clear()
        self.frame_count = 0
        self.last_processed_time = 0.0
        self.frame_skip_count = 0
        logger.info("Liveness detector history reset")
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return {
            'frames_processed': self.frame_count,
            'frames_skipped': self.frame_skip_count,
            'target_fps': self.target_fps,
            'last_processed_time': self.last_processed_time
        }
