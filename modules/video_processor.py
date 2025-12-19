"""
Video Processor module for Kavalan Lite
Handles liveness detection using MediaPipe Face Mesh and Eye Aspect Ratio (EAR)
Also handles visual analysis via Gemini API
Enhanced with: Head Pose Variance, Stress Detection, Privacy Redaction, OpenCV Fallback
"""

import cv2
import numpy as np
import time
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from collections import deque
import json
import base64
from PIL import Image
import io
from pathlib import Path

# Try to import MediaPipe, but make it optional for testing
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None

# Try to import Gemini, but make it optional
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)

# OpenCV Haar Cascade paths for fallback face detection
HAAR_CASCADE_FACE = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
HAAR_CASCADE_EYE = cv2.data.haarcascades + 'haarcascade_eye.xml'

@dataclass
class LivenessResult:
    """Result from liveness detection analysis"""
    score: float  # 0-10 (higher = more suspicious)
    blink_count: int
    blinks_per_minute: float
    face_detected: bool
    is_suspicious: bool
    ear_value: float
    confidence: float
    # New fields for enhanced detection
    head_pose_variance: float = 0.0
    is_static_spoof: bool = False
    is_distressed: bool = False
    detection_method: str = "none"  # "mediapipe", "opencv", "none"
    stress_level: str = "normal"  # "normal", "elevated", "high", "panic"

@dataclass
class VisualResult:
    """Result from visual uniform analysis"""
    score: float  # 0-10 (higher = more suspicious)
    uniform_detected: bool
    anomalies: List[str]
    background_static: bool
    raw_analysis: str
    confidence: float
    # New fields for uniform forensics
    uniform_agency_claimed: str = ""
    uniform_inconsistencies: List[str] = field(default_factory=list)
    is_verified_fake: bool = False

@dataclass
class HeadPose:
    """Head pose estimation result"""
    pitch: float = 0.0  # Up/down rotation
    yaw: float = 0.0    # Left/right rotation  
    roll: float = 0.0   # Tilt rotation
    
@dataclass
class StressIndicators:
    """Stress detection indicators"""
    blink_flutter: bool = False  # Rapid fluttering blinks
    head_jitter: bool = False    # Erratic head movements
    stress_level: str = "normal"
    confidence: float = 0.0

class VideoProcessor:
    """
    Processes video frames for liveness detection and visual analysis
    
    Liveness Detection:
    - Uses MediaPipe Face Mesh to detect facial landmarks (primary)
    - Falls back to OpenCV Haar Cascades if MediaPipe unavailable
    - Calculates Eye Aspect Ratio (EAR) to detect blinks
    - Tracks blink rate over time to detect suspicious behavior
    - NEW: Head pose variance for spoof detection
    - NEW: Stress indicators for victim distress detection
    
    Visual Analysis:
    - Samples frames at intervals for Gemini API analysis
    - Detects fake uniforms with RAG-based forensic verification
    - Privacy-preserving background redaction
    """
    
    # Eye landmark indices for MediaPipe Face Mesh
    LEFT_EYE_LANDMARKS = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
    RIGHT_EYE_LANDMARKS = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    
    # EAR calculation points (6 points per eye)
    LEFT_EYE_POINTS = [33, 160, 158, 133, 153, 144]  # Outer, top, bottom corners
    RIGHT_EYE_POINTS = [362, 385, 387, 263, 373, 380]
    
    # Head pose estimation landmarks (nose tip, chin, eye corners, mouth corners)
    HEAD_POSE_LANDMARKS = [1, 33, 263, 61, 291, 199]  # Key facial points for pose
    
    # 3D model points for head pose estimation (generic face model)
    MODEL_POINTS_3D = np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (-30.0, -125.0, -30.0),      # Left eye corner
        (30.0, -125.0, -30.0),       # Right eye corner  
        (-60.0, -70.0, -60.0),       # Left mouth corner
        (60.0, -70.0, -60.0),        # Right mouth corner
        (0.0, -330.0, -65.0)         # Chin
    ], dtype=np.float64)
    
    def __init__(self, gemini_api_key: str, config: dict = None):
        """
        Initialize video processor with enhanced detection capabilities
        
        Args:
            gemini_api_key: API key for Gemini visual analysis
            config: Configuration dictionary with thresholds
        """
        self.config = config or {}
        
        # Liveness detection parameters
        self.ear_threshold = self.config.get('ear_threshold', 0.25)
        self.min_blinks_per_minute = self.config.get('min_blinks_per_minute', 10)
        self.frame_sample_interval = self.config.get('frame_sample_interval', 2.0)
        
        # Enhanced detection thresholds
        self.head_pose_static_threshold = self.config.get('head_pose_static_threshold', 0.5)  # degrees
        self.head_pose_jitter_threshold = self.config.get('head_pose_jitter_threshold', 5.0)  # degrees
        self.flutter_blink_threshold = self.config.get('flutter_blink_threshold', 0.4)  # EAR variance
        
        # Initialize face detection (try MediaPipe first, then OpenCV fallback)
        self.face_mesh = None
        self.selfie_segmentation = None
        self.detection_method = "none"
        self._init_mediapipe()
        
        # OpenCV fallback detectors
        self.face_cascade = None
        self.eye_cascade = None
        if self.face_mesh is None:
            self._init_opencv_fallback()
        
        # Blink tracking
        self.blink_history = deque(maxlen=100)  # Store last 100 blinks with timestamps
        self.last_ear_values = deque(maxlen=30)  # Extended for flutter detection
        self.blink_state = False  # Current blink state
        self.frame_count = 0
        
        # Head pose tracking for variance calculation
        self.head_pose_history = deque(maxlen=30)  # Last 30 poses (~1 second at 30fps)
        
        # Stress detection tracking
        self.recent_blink_intervals = deque(maxlen=10)
        self.last_blink_time = 0
        
        # Visual analysis
        self.last_analysis_time = 0
        self.gemini_model = None
        
        # Privacy redaction enabled
        self.privacy_redaction_enabled = self.config.get('privacy_redaction', True)
        
        # Load uniform forensics knowledge base
        self.uniform_codes = self._load_uniform_codes()
        
        # Initialize Gemini if API key provided
        if gemini_api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                logger.info("Gemini model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.gemini_model = None
        else:
            self.gemini_model = None
        
        logger.info(f"VideoProcessor initialized - Detection: {self.detection_method}, EAR: {self.ear_threshold}")
    
    def _init_mediapipe(self):
        """Initialize MediaPipe Face Mesh and Selfie Segmentation"""
        if not MEDIAPIPE_AVAILABLE:
            logger.warning("MediaPipe not available")
            return
            
        try:
            # Initialize Face Mesh
            from mediapipe.python.solutions import face_mesh as mp_face_mesh
            from mediapipe.python.solutions import selfie_segmentation as mp_selfie
            
            self.mp_face_mesh = mp_face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=2,  # Detect both user and potential scammer
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            # Initialize Selfie Segmentation for privacy redaction
            self.mp_selfie = mp_selfie
            self.selfie_segmentation = self.mp_selfie.SelfieSegmentation(model_selection=1)
            
            self.detection_method = "mediapipe"
            logger.info("MediaPipe Face Mesh and Selfie Segmentation initialized")
            
        except Exception as e:
            logger.warning(f"MediaPipe initialization failed: {e}")
            self.face_mesh = None
            self.selfie_segmentation = None
    
    def _init_opencv_fallback(self):
        """Initialize OpenCV Haar Cascades as fallback for face detection"""
        try:
            self.face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_FACE)
            self.eye_cascade = cv2.CascadeClassifier(HAAR_CASCADE_EYE)
            
            if self.face_cascade.empty():
                raise Exception("Failed to load face cascade")
            if self.eye_cascade.empty():
                raise Exception("Failed to load eye cascade")
                
            self.detection_method = "opencv"
            logger.info("OpenCV Haar Cascades initialized as fallback")
            
        except Exception as e:
            logger.error(f"OpenCV fallback initialization failed: {e}")
            self.face_cascade = None
            self.eye_cascade = None
    
    def _load_uniform_codes(self) -> Dict:
        """Load official uniform codes for RAG-based forensic verification"""
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'uniform_codes.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load uniform codes: {e}")
        
        # Default uniform knowledge base
        return {
            "CBI": {
                "name": "Central Bureau of Investigation",
                "typical_attire": "formal business attire (suits), NOT khaki uniforms",
                "badge": "CBI emblem with national emblem",
                "interrogation_setting": "formal office setting, never video calls for arrests",
                "red_flags": ["khaki uniform", "police cap", "video call arrest", "money demands"]
            },
            "ED": {
                "name": "Enforcement Directorate", 
                "typical_attire": "formal civilian attire (suits/formal wear)",
                "badge": "ED emblem with national emblem",
                "interrogation_setting": "official ED office, summons issued in writing",
                "red_flags": ["any uniform", "video interrogation", "immediate money transfer"]
            },
            "IPS": {
                "name": "Indian Police Service",
                "typical_attire": "khaki uniform with proper insignia",
                "badge": "Ashoka emblem, proper rank insignia",
                "cap": "peaked cap (NOT baseball cap)",
                "nameplate": "bilingual nameplate required",
                "red_flags": ["baseball cap", "generic POLICE text", "wrong badge placement"]
            },
            "NCB": {
                "name": "Narcotics Control Bureau",
                "typical_attire": "formal attire or NCB-specific uniform",
                "badge": "NCB emblem",
                "red_flags": ["video arrest", "immediate payment demands"]
            },
            "general_scam_indicators": [
                "Video call 'arrests' are ILLEGAL in India",
                "No agency demands money transfer during investigation",
                "Real summons are physical documents, not video calls",
                "Section 41A CrPC requires written notice, not video calls",
                "No 'Digital Arrest' exists in Indian law"
            ]
        }
    
    def calculate_ear(self, landmarks: List, eye_points: List[int]) -> float:
        """
        Calculate Eye Aspect Ratio (EAR) from facial landmarks
        
        EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
        Where p1-p6 are the 6 eye landmark points
        
        Args:
            landmarks: MediaPipe facial landmarks
            eye_points: List of 6 landmark indices for one eye
            
        Returns:
            EAR value (typically 0.2-0.4 for open eyes, <0.2 for closed)
        """
        try:
            # Extract eye points
            points = []
            for idx in eye_points:
                point = landmarks.landmark[idx]
                points.append([point.x, point.y])
            
            points = np.array(points)
            
            # Calculate distances
            # Vertical distances
            A = np.linalg.norm(points[1] - points[5])  # Top to bottom (outer)
            B = np.linalg.norm(points[2] - points[4])  # Top to bottom (inner)
            
            # Horizontal distance
            C = np.linalg.norm(points[0] - points[3])  # Left to right
            
            # Calculate EAR
            if C > 0:
                ear = (A + B) / (2.0 * C)
            else:
                ear = 0.0
            
            return ear
            
        except Exception as e:
            logger.error(f"Error calculating EAR: {e}")
            return 0.0
    
    def detect_blink(self, ear: float) -> bool:
        """
        Detect if current EAR indicates a blink
        
        Args:
            ear: Current Eye Aspect Ratio
            
        Returns:
            True if blink detected, False otherwise
        """
        # Add to smoothing buffer
        self.last_ear_values.append(ear)
        
        # Use smoothed EAR
        smoothed_ear = np.mean(list(self.last_ear_values)[-10:])  # Use last 10 for smoothing
        
        # Detect blink (EAR drops below threshold)
        if smoothed_ear < self.ear_threshold and not self.blink_state:
            # Blink started
            self.blink_state = True
            return False
        elif smoothed_ear >= self.ear_threshold and self.blink_state:
            # Blink ended - count it
            self.blink_state = False
            current_time = time.time()
            self.blink_history.append(current_time)
            
            # Track blink intervals for flutter detection
            if self.last_blink_time > 0:
                interval = current_time - self.last_blink_time
                self.recent_blink_intervals.append(interval)
            self.last_blink_time = current_time
            
            return True
        
        return False
    
    def estimate_head_pose(self, landmarks, frame_shape: Tuple[int, int, int]) -> HeadPose:
        """
        Estimate head pose (pitch, yaw, roll) from facial landmarks
        
        Args:
            landmarks: MediaPipe facial landmarks
            frame_shape: Shape of the frame (height, width, channels)
            
        Returns:
            HeadPose with pitch, yaw, roll values
        """
        try:
            h, w = frame_shape[:2]
            
            # Extract 2D image points
            image_points = []
            landmark_indices = [1, 33, 263, 61, 291, 199]  # Nose, eyes, mouth corners, chin
            
            for idx in landmark_indices:
                lm = landmarks.landmark[idx]
                image_points.append([lm.x * w, lm.y * h])
            
            image_points = np.array(image_points, dtype=np.float64)
            
            # Camera matrix (approximate)
            focal_length = w
            center = (w / 2, h / 2)
            camera_matrix = np.array([
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1]
            ], dtype=np.float64)
            
            # No lens distortion
            dist_coeffs = np.zeros((4, 1))
            
            # Solve PnP
            success, rotation_vec, translation_vec = cv2.solvePnP(
                self.MODEL_POINTS_3D,
                image_points,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
            
            if success:
                # Convert rotation vector to Euler angles
                rotation_mat, _ = cv2.Rodrigues(rotation_vec)
                pose_mat = cv2.hconcat([rotation_mat, translation_vec])
                _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)
                
                pitch = euler_angles[0][0]
                yaw = euler_angles[1][0]
                roll = euler_angles[2][0]
                
                return HeadPose(pitch=pitch, yaw=yaw, roll=roll)
            
        except Exception as e:
            logger.debug(f"Head pose estimation failed: {e}")
        
        return HeadPose()
    
    def calculate_head_pose_variance(self) -> float:
        """
        Calculate variance in head pose over recent frames
        
        Returns:
            Variance value (low = static/spoof, high = jittery/stressed)
        """
        if len(self.head_pose_history) < 5:
            return 0.0
        
        poses = list(self.head_pose_history)
        pitches = [p.pitch for p in poses]
        yaws = [p.yaw for p in poses]
        rolls = [p.roll for p in poses]
        
        # Combined variance across all axes
        variance = np.var(pitches) + np.var(yaws) + np.var(rolls)
        return float(variance)
    
    def detect_stress_indicators(self, ear: float, head_pose_variance: float) -> StressIndicators:
        """
        Detect stress indicators based on blink patterns and head movements
        
        Following the "Adaptive Panic Liveness" matrix from the spec:
        - Static spoof: No blinks + low head variance
        - Distress: Flutter blinks + high head jitter
        
        Args:
            ear: Current EAR value
            head_pose_variance: Current head pose variance
            
        Returns:
            StressIndicators with detection results
        """
        indicators = StressIndicators()
        
        # Check for blink flutter (rapid, irregular blinks)
        if len(self.recent_blink_intervals) >= 3:
            avg_interval = np.mean(self.recent_blink_intervals)
            interval_variance = np.var(self.recent_blink_intervals)
            
            # Flutter: rapid blinks (< 0.5s average) with high variance
            if avg_interval < 0.5 and interval_variance > 0.1:
                indicators.blink_flutter = True
        
        # Check EAR variance for flutter detection
        if len(self.last_ear_values) >= 10:
            ear_variance = np.var(list(self.last_ear_values)[-10:])
            if ear_variance > self.flutter_blink_threshold:
                indicators.blink_flutter = True
        
        # Check for head jitter (high pose variance)
        if head_pose_variance > self.head_pose_jitter_threshold:
            indicators.head_jitter = True
        
        # Determine stress level
        if indicators.blink_flutter and indicators.head_jitter:
            indicators.stress_level = "panic"
            indicators.confidence = 0.9
        elif indicators.blink_flutter or indicators.head_jitter:
            indicators.stress_level = "high"
            indicators.confidence = 0.7
        elif head_pose_variance > 2.0 or (len(self.recent_blink_intervals) > 0 and np.mean(self.recent_blink_intervals) < 1.0):
            indicators.stress_level = "elevated"
            indicators.confidence = 0.5
        else:
            indicators.stress_level = "normal"
            indicators.confidence = 0.8
        
        return indicators
    
    def detect_static_spoof(self, blinks_per_minute: float, head_pose_variance: float) -> bool:
        """
        Detect static spoof attacks (looped video, static image, deepfake)
        
        Args:
            blinks_per_minute: Current blink rate
            head_pose_variance: Current head pose variance
            
        Returns:
            True if static spoof detected
        """
        # Static spoof indicators:
        # 1. No blinks (or very few) over extended period
        # 2. Head pose variance near zero (perfectly still)
        
        no_blinks = blinks_per_minute < 3  # Almost no blinks
        static_pose = head_pose_variance < self.head_pose_static_threshold
        
        # Both conditions = high confidence spoof
        if no_blinks and static_pose and self.frame_count > 90:  # 3 seconds at 30fps
            return True
        
        return False
    
    def apply_privacy_redaction(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply privacy-preserving background blur using MediaPipe Selfie Segmentation
        
        This ensures only the person (face) is visible, protecting sensitive
        background details like family members, documents, room layout.
        
        Args:
            frame: Input BGR frame
            
        Returns:
            Frame with blurred background
        """
        if not self.privacy_redaction_enabled or self.selfie_segmentation is None:
            return frame
        
        try:
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get segmentation mask
            results = self.selfie_segmentation.process(rgb_frame)
            
            if results.segmentation_mask is not None:
                # Create mask (person = 1, background = 0)
                mask = results.segmentation_mask
                mask = np.stack([mask] * 3, axis=-1)
                
                # Apply heavy Gaussian blur to background
                blurred = cv2.GaussianBlur(frame, (55, 55), 0)
                
                # Combine: keep person sharp, blur background
                output = np.where(mask > 0.5, frame, blurred).astype(np.uint8)
                
                return output
            
        except Exception as e:
            logger.debug(f"Privacy redaction failed: {e}")
        
        return frame
    
    def process_with_opencv_fallback(self, frame: np.ndarray) -> Tuple[bool, float, float]:
        """
        Fallback face detection using OpenCV Haar Cascades
        
        Args:
            frame: Input BGR frame
            
        Returns:
            Tuple of (face_detected, approximate_ear, confidence)
        """
        if self.face_cascade is None:
            return False, 0.0, 0.0
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            if len(faces) > 0:
                # Get largest face
                face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = face
                
                # Extract face region for eye detection
                face_roi = gray[y:y+h, x:x+w]
                
                # Detect eyes within face
                eyes = self.eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=5)
                
                # Estimate EAR based on eye detection (rough approximation)
                if len(eyes) >= 2:
                    # Eyes detected - likely open
                    ear_estimate = 0.3
                elif len(eyes) == 1:
                    # One eye detected - partially closed or profile
                    ear_estimate = 0.2
                else:
                    # No eyes detected - possibly closed or occluded
                    ear_estimate = 0.15
                
                return True, ear_estimate, 0.6
            
        except Exception as e:
            logger.debug(f"OpenCV fallback detection failed: {e}")
        
        return False, 0.0, 0.0
    
    def calculate_blink_rate(self) -> Tuple[int, float]:
        """
        Calculate blink rate over the last minute
        
        Returns:
            Tuple of (blink_count, blinks_per_minute)
        """
        current_time = time.time()
        
        # Remove blinks older than 1 minute
        while self.blink_history and (current_time - self.blink_history[0]) > 60:
            self.blink_history.popleft()
        
        blink_count = len(self.blink_history)
        
        # Calculate blinks per minute
        if self.blink_history:
            time_span = current_time - self.blink_history[0] if len(self.blink_history) > 1 else 60
            blinks_per_minute = (blink_count / time_span) * 60
        else:
            blinks_per_minute = 0.0
        
        return blink_count, blinks_per_minute
    
    def calculate_liveness_score(self, blinks_per_minute: float, face_detected: bool, ear: float,
                                   head_pose_variance: float = 0.0, stress_indicators: StressIndicators = None) -> Tuple[float, bool]:
        """
        Calculate liveness score based on blink rate, head pose, and stress indicators
        
        Enhanced with "Adaptive Panic Liveness" matrix:
        - Static Spoof Detection: No blinks + static pose = BLOCK
        - Distress Detection: Flutter blinks + jitter = CALM DOWN protocol
        
        Args:
            blinks_per_minute: Current blink rate
            face_detected: Whether a face was detected
            ear: Current EAR value
            head_pose_variance: Head pose variance over time
            stress_indicators: Stress detection results
            
        Returns:
            Tuple of (score, is_suspicious)
        """
        if not face_detected:
            return 8.0, True  # High suspicion if no face detected
        
        score = 0.0
        is_suspicious = False
        
        # Check for static spoof (looped video/deepfake)
        if self.detect_static_spoof(blinks_per_minute, head_pose_variance):
            score += 9.0  # Critical - likely fake
            is_suspicious = True
            logger.warning("STATIC SPOOF DETECTED: Possible looped video or deepfake")
        else:
            # Normal blink rate check
            if blinks_per_minute < self.min_blinks_per_minute:
                # Too few blinks - possible deepfake or static image
                score += 6.0
                is_suspicious = True
            elif blinks_per_minute > 40:
                # Too many blinks - possible nervousness or manipulation
                score += 2.0
        
        # Check head pose variance
        if head_pose_variance < self.head_pose_static_threshold and self.frame_count > 90:
            # Unnaturally static - possible video injection
            score += 3.0
            is_suspicious = True
        
        # Check EAR consistency  
        if len(self.last_ear_values) >= 5:
            ear_variance = np.var(list(self.last_ear_values)[-10:])
            if ear_variance < 0.001 and self.frame_count > 90:
                # Too consistent - possible static image
                score += 3.0
                is_suspicious = True
        
        # Check if eyes are always open (EAR never drops)
        if len(self.blink_history) == 0 and self.frame_count > 150:  # 5 seconds at 30fps
            score += 5.0
            is_suspicious = True
        
        # Stress indicators don't add to suspicion score (victim protection)
        # but we track them for UI response
        
        # Clamp score to [0, 10]
        score = max(0.0, min(10.0, score))
        
        return score, is_suspicious
    
    def process_liveness(self, frame: np.ndarray) -> LivenessResult:
        """
        Process frame for liveness detection with enhanced capabilities
        
        Features:
        - Primary: MediaPipe Face Mesh with EAR blink detection
        - Fallback: OpenCV Haar Cascades
        - NEW: Head pose variance for spoof detection
        - NEW: Stress indicator detection for victim protection
        
        Args:
            frame: Input video frame (BGR format)
            
        Returns:
            LivenessResult with comprehensive liveness analysis
        """
        self.frame_count += 1
        
        # Validate frame
        if frame is None or frame.size == 0 or len(frame.shape) != 3:
            return LivenessResult(
                score=0.0,
                blink_count=0,
                blinks_per_minute=0.0,
                face_detected=False,
                is_suspicious=False,
                ear_value=0.0,
                confidence=0.0,
                detection_method="none"
            )
        
        face_detected = False
        ear_value = 0.0
        confidence = 0.0
        head_pose = HeadPose()
        detection_method = "none"
        
        # Try MediaPipe first (more accurate)
        if self.face_mesh is not None:
            try:
                # Convert BGR to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb_frame)
                
                if results and hasattr(results, 'multi_face_landmarks') and results.multi_face_landmarks:
                    face_detected = True
                    detection_method = "mediapipe"
                    landmarks = results.multi_face_landmarks[0]
                    
                    # Calculate EAR for both eyes
                    left_ear = self.calculate_ear(landmarks, self.LEFT_EYE_POINTS)
                    right_ear = self.calculate_ear(landmarks, self.RIGHT_EYE_POINTS)
                    ear_value = (left_ear + right_ear) / 2.0
                    confidence = 0.85
                    
                    # Estimate head pose
                    head_pose = self.estimate_head_pose(landmarks, frame.shape)
                    self.head_pose_history.append(head_pose)
                    
                    # Detect blink
                    self.detect_blink(ear_value)
                    
            except Exception as e:
                logger.error(f"MediaPipe processing failed: {e}")
        
        # Fallback to OpenCV if MediaPipe didn't detect a face
        if not face_detected and self.face_cascade is not None:
            face_detected, ear_value, confidence = self.process_with_opencv_fallback(frame)
            if face_detected:
                detection_method = "opencv"
                # Still try to detect blink with estimated EAR
                self.detect_blink(ear_value)
        
        # Calculate head pose variance
        head_pose_variance = self.calculate_head_pose_variance()
        
        # Detect stress indicators
        stress_indicators = self.detect_stress_indicators(ear_value, head_pose_variance)
        
        # Detect static spoof
        blink_count, blinks_per_minute = self.calculate_blink_rate()
        is_static_spoof = self.detect_static_spoof(blinks_per_minute, head_pose_variance)
        
        # Calculate liveness score
        score, is_suspicious = self.calculate_liveness_score(
            blinks_per_minute, face_detected, ear_value,
            head_pose_variance, stress_indicators
        )
        
        return LivenessResult(
            score=score,
            blink_count=blink_count,
            blinks_per_minute=blinks_per_minute,
            face_detected=face_detected,
            is_suspicious=is_suspicious,
            ear_value=ear_value,
            confidence=confidence,
            head_pose_variance=head_pose_variance,
            is_static_spoof=is_static_spoof,
            is_distressed=stress_indicators.stress_level in ["high", "panic"],
            detection_method=detection_method,
            stress_level=stress_indicators.stress_level
        )
    
    def frame_to_base64(self, frame: np.ndarray) -> str:
        """Convert frame to base64 for Gemini API"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_frame)
            
            # Resize for API efficiency (max 1024px)
            max_size = 1024
            if max(pil_image.size) > max_size:
                ratio = max_size / max(pil_image.size)
                new_size = tuple(int(dim * ratio) for dim in pil_image.size)
                pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG', quality=85)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return img_base64
            
        except Exception as e:
            logger.error(f"Error converting frame to base64: {e}")
            return ""
    
    def analyze_uniform(self, frame: np.ndarray, prompt: str) -> VisualResult:
        """
        Analyze frame for fake uniform indicators using Gemini with RAG-based forensics
        
        Enhanced with:
        - Privacy redaction before sending to API
        - RAG-augmented uniform verification against official codes
        - Specific evidence-based refutations
        
        Args:
            frame: Input video frame
            prompt: Base analysis prompt for Gemini
            
        Returns:
            VisualResult with forensic uniform analysis
        """
        if not self.gemini_model:
            return VisualResult(
                score=0.0,
                uniform_detected=False,
                anomalies=[],
                background_static=False,
                raw_analysis="Gemini not available",
                confidence=0.0
            )
        
        try:
            # Apply privacy redaction before sending to cloud
            redacted_frame = self.apply_privacy_redaction(frame)
            
            # Convert frame to base64
            img_base64 = self.frame_to_base64(redacted_frame)
            if not img_base64:
                raise Exception("Failed to convert frame")
            
            # Enhance prompt with uniform forensics knowledge base
            forensic_prompt = self._build_forensic_prompt(prompt)
            
            # Prepare image for Gemini
            image_data = {
                "mime_type": "image/jpeg",
                "data": img_base64
            }
            
            # Call Gemini API with safety settings to allow threat analysis
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ]
            
            response = self.gemini_model.generate_content(
                [forensic_prompt, image_data],
                safety_settings=safety_settings
            )
            
            if not response.text:
                raise Exception("Empty response from Gemini")
            
            # Parse JSON response
            try:
                # Clean response text (remove markdown code blocks if present)
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                analysis = json.loads(response_text.strip())
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                analysis = {
                    "score": 5.0,
                    "uniform_detected": "uniform" in response.text.lower(),
                    "anomalies": ["Analysis not in JSON format"],
                    "background_static": "static" in response.text.lower(),
                    "analysis": response.text,
                    "agency_claimed": "",
                    "uniform_inconsistencies": [],
                    "is_verified_fake": False
                }
            
            return VisualResult(
                score=float(analysis.get("score", 5.0)),
                uniform_detected=bool(analysis.get("uniform_detected", False)),
                anomalies=analysis.get("anomalies", []),
                background_static=bool(analysis.get("background_static", False)),
                raw_analysis=analysis.get("analysis", response.text),
                confidence=0.85,
                uniform_agency_claimed=analysis.get("agency_claimed", ""),
                uniform_inconsistencies=analysis.get("uniform_inconsistencies", []),
                is_verified_fake=bool(analysis.get("is_verified_fake", False))
            )
            
        except Exception as e:
            logger.error(f"Error in uniform analysis: {e}")
            return VisualResult(
                score=5.0,  # Neutral score on error
                uniform_detected=False,
                anomalies=[f"Analysis error: {str(e)}"],
                background_static=False,
                raw_analysis=f"Error: {str(e)}",
                confidence=0.0
            )
    
    def _build_forensic_prompt(self, base_prompt: str) -> str:
        """
        Build RAG-augmented forensic prompt with official uniform codes
        
        Args:
            base_prompt: Original analysis prompt
            
        Returns:
            Enhanced prompt with uniform verification knowledge
        """
        # Build knowledge context from uniform codes
        knowledge_context = """
CRITICAL UNIFORM FORENSICS KNOWLEDGE BASE:

1. CBI (Central Bureau of Investigation):
   - Officers wear FORMAL BUSINESS ATTIRE (suits), NOT khaki uniforms
   - CBI does NOT conduct video call interrogations or "Digital Arrests"
   - Any person in khaki claiming to be CBI is FAKE

2. ED (Enforcement Directorate):
   - Officers wear CIVILIAN FORMAL ATTIRE (suits/formal wear)
   - ED does NOT conduct video call interrogations
   - ED summons are issued IN WRITING, never via video call

3. IPS (Indian Police Service):
   - Khaki uniform with PROPER INSIGNIA
   - PEAKED CAPS (not baseball caps with "POLICE" text)
   - Bilingual nameplates are MANDATORY
   - Ashoka emblem on badges
   - RED FLAGS: baseball cap, generic "POLICE" text, wrong badge placement

4. LEGAL FACTS:
   - "Digital Arrest" does NOT EXIST in Indian law
   - Section 41A CrPC requires PHYSICAL WRITTEN NOTICE before arrest
   - No legitimate agency demands money during investigation
   - Real judicial proceedings NEVER occur on mobile phone video calls

WHEN ANALYZING: If the person claims to be from CBI/ED but wears a khaki uniform, 
this is CONCLUSIVE EVIDENCE of a scam. Return is_verified_fake=true with specific 
inconsistencies.

"""
        
        enhanced_prompt = f"""{knowledge_context}

{base_prompt}

ADDITIONAL INSTRUCTIONS:
1. If a uniform is detected, identify which agency the person claims to represent
2. Compare their attire against the official uniform code above
3. List SPECIFIC inconsistencies (e.g., "CBI officer wearing khaki - CBI does not wear uniforms")
4. If inconsistencies found, set is_verified_fake=true

Return your analysis as JSON:
{{
  "score": <0-10>,
  "uniform_detected": <true/false>,
  "anomalies": ["list of visual anomalies"],
  "background_static": <true/false>,
  "analysis": "detailed reasoning",
  "agency_claimed": "<CBI/ED/IPS/Police/NCB/Unknown>",
  "uniform_inconsistencies": ["specific violations of official uniform codes"],
  "is_verified_fake": <true/false - true if inconsistencies prove this is fake>
}}
"""
        return enhanced_prompt
    
    def process_frame(self, frame: np.ndarray, uniform_prompt: str = None) -> Tuple[LivenessResult, Optional[VisualResult]]:
        """
        Process a single video frame for both liveness and visual analysis
        
        Enhanced with:
        - Privacy-preserving background redaction
        - Robust face detection with OpenCV fallback
        - Head pose variance tracking
        - Stress indicator detection
        
        Args:
            frame: Input video frame (BGR format)
            uniform_prompt: Optional prompt for uniform analysis
            
        Returns:
            Tuple of (LivenessResult, Optional[VisualResult])
        """
        # Always process liveness (fast, local)
        liveness_result = self.process_liveness(frame)
        
        # Process visual analysis only at intervals (slow, cloud)
        visual_result = None
        current_time = time.time()
        
        if (uniform_prompt and 
            self.gemini_model and 
            (current_time - self.last_analysis_time) >= self.frame_sample_interval):
            
            visual_result = self.analyze_uniform(frame, uniform_prompt)
            self.last_analysis_time = current_time
        
        return liveness_result, visual_result
    
    def get_detection_status(self) -> Dict:
        """
        Get current detection system status
        
        Returns:
            Dictionary with detection capabilities status
        """
        return {
            "face_detection": self.detection_method,
            "mediapipe_available": self.face_mesh is not None,
            "opencv_fallback": self.face_cascade is not None,
            "selfie_segmentation": self.selfie_segmentation is not None,
            "gemini_available": self.gemini_model is not None,
            "privacy_redaction": self.privacy_redaction_enabled,
            "frame_count": self.frame_count
        }
    
    def reset_tracking(self):
        """Reset all tracking state (useful when switching video sources)"""
        self.blink_history.clear()
        self.last_ear_values.clear()
        self.head_pose_history.clear()
        self.recent_blink_intervals.clear()
        self.blink_state = False
        self.frame_count = 0
        self.last_analysis_time = 0
        self.last_blink_time = 0
        logger.info("Video processor tracking reset")