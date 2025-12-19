"""
Evidence Logger Module for Kavalan Lite
"Black Box" for scam calls - buffers evidence and generates Digital FIR reports

Features:
- Rolling buffer of last 30 seconds of audio/video
- Auto-commit to local storage on high threat detection
- Generate "Digital FIR" PDF with timestamped evidence
- Export-ready evidence package for law enforcement
"""

import base64
import io
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import threading

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Try to import PDF generation (optional)
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not available - PDF generation disabled")


@dataclass
class EvidenceFrame:
    """Single frame of video evidence"""
    timestamp: float
    frame_data: np.ndarray
    threat_score: float = 0.0
    annotations: List[str] = field(default_factory=list)


@dataclass
class EvidenceAudioChunk:
    """Single chunk of audio evidence"""
    timestamp: float
    audio_data: np.ndarray
    duration_seconds: float
    transcript: str = ""


@dataclass
class ThreatEvent:
    """Record of a detected threat"""
    timestamp: float
    threat_type: str
    threat_score: float
    description: str
    evidence_frame_idx: int = -1
    audio_transcript: str = ""


@dataclass
class EvidencePackage:
    """Complete evidence package for export"""
    session_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    max_threat_score: float
    threat_events: List[ThreatEvent]
    key_frames: List[Tuple[float, bytes]]  # (timestamp, jpeg_bytes)
    transcripts: List[Tuple[float, str]]  # (timestamp, text)
    analysis_summary: str
    recommendations: List[str]


class EvidenceLogger:
    """
    Evidence logging system for scam call documentation
    
    Acts as a "Black Box" that continuously buffers the last 30 seconds
    of audio/video evidence. When a high-threat event is detected, the
    buffer is committed to storage for later analysis and reporting.
    """
    
    BUFFER_DURATION_SECONDS = 30
    MAX_FRAMES_IN_BUFFER = 30  # 1 FPS for 30 seconds
    MAX_AUDIO_CHUNKS = 60  # 0.5s chunks for 30 seconds
    
    def __init__(self, output_dir: str = None):
        """
        Initialize evidence logger
        
        Args:
            output_dir: Directory for storing evidence (default: ./evidence)
        """
        self.output_dir = Path(output_dir) if output_dir else Path("evidence")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Rolling buffers
        self._frame_buffer: deque[EvidenceFrame] = deque(maxlen=self.MAX_FRAMES_IN_BUFFER)
        self._audio_buffer: deque[EvidenceAudioChunk] = deque(maxlen=self.MAX_AUDIO_CHUNKS)
        
        # Threat tracking
        self._threat_events: List[ThreatEvent] = []
        self._max_threat_score = 0.0
        
        # Session tracking
        self._session_id = None
        self._session_start = None
        self._is_recording = False
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Auto-commit threshold
        self.auto_commit_threshold = 8.0  # Commit evidence when threat >= 8.0
        self._committed = False
        
        logger.info(f"EvidenceLogger initialized, output: {self.output_dir}")
    
    def start_session(self) -> str:
        """Start a new evidence collection session"""
        with self._lock:
            self._session_id = f"kavalan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._session_start = datetime.now()
            self._is_recording = True
            self._committed = False
            self._threat_events.clear()
            self._max_threat_score = 0.0
            
            logger.info(f"Evidence session started: {self._session_id}")
            return self._session_id
    
    def stop_session(self) -> Optional[str]:
        """Stop current session and return session ID"""
        with self._lock:
            self._is_recording = False
            session_id = self._session_id
            logger.info(f"Evidence session stopped: {session_id}")
            return session_id
    
    def add_frame(self, frame: np.ndarray, threat_score: float = 0.0, 
                  annotations: List[str] = None):
        """
        Add video frame to evidence buffer
        
        Args:
            frame: BGR numpy array
            threat_score: Current threat score (0-10)
            annotations: List of annotations for this frame
        """
        if not self._is_recording:
            return
        
        with self._lock:
            evidence_frame = EvidenceFrame(
                timestamp=time.time(),
                frame_data=frame.copy(),
                threat_score=threat_score,
                annotations=annotations or []
            )
            self._frame_buffer.append(evidence_frame)
            
            # Update max threat
            if threat_score > self._max_threat_score:
                self._max_threat_score = threat_score
            
            # Auto-commit on high threat
            if threat_score >= self.auto_commit_threshold and not self._committed:
                self._auto_commit()
    
    def add_audio(self, audio_data: np.ndarray, sample_rate: int = 16000,
                  transcript: str = ""):
        """
        Add audio chunk to evidence buffer
        
        Args:
            audio_data: Audio samples (numpy array)
            sample_rate: Audio sample rate
            transcript: Optional transcript of this audio
        """
        if not self._is_recording:
            return
        
        with self._lock:
            duration = len(audio_data) / sample_rate
            chunk = EvidenceAudioChunk(
                timestamp=time.time(),
                audio_data=audio_data.copy(),
                duration_seconds=duration,
                transcript=transcript
            )
            self._audio_buffer.append(chunk)
    
    def record_threat(self, threat_type: str, threat_score: float, 
                      description: str, transcript: str = ""):
        """
        Record a threat detection event
        
        Args:
            threat_type: Type of threat (authority, coercion, financial, uniform)
            threat_score: Threat score (0-10)
            description: Human-readable description
            transcript: Associated audio transcript
        """
        with self._lock:
            event = ThreatEvent(
                timestamp=time.time(),
                threat_type=threat_type,
                threat_score=threat_score,
                description=description,
                evidence_frame_idx=len(self._frame_buffer) - 1,
                audio_transcript=transcript
            )
            self._threat_events.append(event)
            
            logger.info(f"Threat recorded: {threat_type} (score: {threat_score})")
    
    def _auto_commit(self):
        """Auto-commit evidence when high threat detected"""
        if self._committed:
            return
        
        self._committed = True
        logger.warning("HIGH THREAT DETECTED - Auto-committing evidence buffer")
        
        # Save current buffer state
        try:
            self._save_buffer_snapshot()
        except Exception as e:
            logger.error(f"Auto-commit failed: {e}")
    
    def _save_buffer_snapshot(self):
        """Save current buffer to disk"""
        if not self._session_id:
            return
        
        session_dir = self.output_dir / self._session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Save key frames
        frames_dir = session_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        
        for i, frame in enumerate(self._frame_buffer):
            if frame.threat_score >= 5.0:  # Save frames with elevated threat
                frame_path = frames_dir / f"frame_{i:04d}_{frame.threat_score:.1f}.jpg"
                cv2.imwrite(str(frame_path), frame.frame_data)
        
        # Save threat log
        threat_log = {
            "session_id": self._session_id,
            "start_time": self._session_start.isoformat() if self._session_start else None,
            "snapshot_time": datetime.now().isoformat(),
            "max_threat_score": self._max_threat_score,
            "threat_events": [
                {
                    "timestamp": e.timestamp,
                    "type": e.threat_type,
                    "score": e.threat_score,
                    "description": e.description,
                    "transcript": e.audio_transcript
                }
                for e in self._threat_events
            ]
        }
        
        with open(session_dir / "threat_log.json", 'w') as f:
            json.dump(threat_log, f, indent=2)
        
        logger.info(f"Evidence snapshot saved to {session_dir}")
    
    def generate_digital_fir(self, include_frames: bool = True) -> Optional[str]:
        """
        Generate Digital FIR (First Information Report) PDF
        
        Args:
            include_frames: Whether to include screenshot evidence
            
        Returns:
            Path to generated PDF, or None if generation failed
        """
        if not REPORTLAB_AVAILABLE:
            logger.warning("Cannot generate PDF - reportlab not installed")
            return self._generate_text_report()
        
        if not self._session_id:
            logger.error("No active session for FIR generation")
            return None
        
        try:
            return self._generate_pdf_report(include_frames)
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return self._generate_text_report()
    
    def _generate_pdf_report(self, include_frames: bool) -> str:
        """Generate PDF report using reportlab"""
        session_dir = self.output_dir / self._session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_path = session_dir / f"Digital_FIR_{self._session_id}.pdf"
        
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("🛡️ KAVALAN LITE - DIGITAL FIR", title_style))
        story.append(Paragraph("Suspected Digital Arrest Scam Evidence Report", styles['Heading2']))
        story.append(Spacer(1, 20))
        
        # Session Info
        story.append(Paragraph("<b>Session Information</b>", styles['Heading3']))
        session_data = [
            ["Report ID:", self._session_id],
            ["Start Time:", self._session_start.strftime("%Y-%m-%d %H:%M:%S") if self._session_start else "Unknown"],
            ["Report Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Maximum Threat Score:", f"{self._max_threat_score:.1f}/10"],
            ["Total Threats Detected:", str(len(self._threat_events))]
        ]
        
        table = Table(session_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Legal Notice
        story.append(Paragraph("<b>⚠️ IMPORTANT LEGAL INFORMATION</b>", styles['Heading3']))
        legal_text = """
        <b>"Digital Arrest" is NOT a legal concept in India.</b> No law enforcement agency 
        (CBI, ED, Police, NCB, or Courts) conducts arrests or interrogations via video call. 
        If you have been subjected to such demands:
        <br/><br/>
        1. <b>DO NOT transfer any money</b> - This is financial fraud<br/>
        2. <b>Disconnect immediately</b> - You are not legally obligated to stay on call<br/>
        3. <b>Report to Cyber Crime Portal</b> - cybercrime.gov.in or call 1930<br/>
        4. <b>Contact local police</b> - File an FIR with this evidence<br/>
        """
        story.append(Paragraph(legal_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Threat Events
        if self._threat_events:
            story.append(Paragraph("<b>Detected Threat Events</b>", styles['Heading3']))
            
            for i, event in enumerate(self._threat_events, 1):
                event_time = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
                story.append(Paragraph(
                    f"<b>Event {i}</b> [{event_time}] - {event.threat_type.upper()} "
                    f"(Score: {event.threat_score:.1f}/10)",
                    styles['Heading4']
                ))
                story.append(Paragraph(f"Description: {event.description}", styles['Normal']))
                if event.audio_transcript:
                    story.append(Paragraph(f"<i>Transcript: \"{event.audio_transcript}\"</i>", styles['Normal']))
                story.append(Spacer(1, 10))
        
        # Evidence Frames
        if include_frames and self._frame_buffer:
            story.append(Paragraph("<b>Visual Evidence (Key Frames)</b>", styles['Heading3']))
            
            # Get high-threat frames
            high_threat_frames = [f for f in self._frame_buffer if f.threat_score >= 5.0][:5]
            
            for frame in high_threat_frames:
                # Convert frame to image
                frame_time = datetime.fromtimestamp(frame.timestamp).strftime("%H:%M:%S")
                
                # Encode frame to bytes
                _, buffer = cv2.imencode('.jpg', frame.frame_data)
                img_bytes = io.BytesIO(buffer.tobytes())
                
                story.append(Paragraph(
                    f"Frame at {frame_time} - Threat Score: {frame.threat_score:.1f}",
                    styles['Normal']
                ))
                
                # Add image (scaled to fit)
                img = RLImage(img_bytes, width=4*inch, height=3*inch)
                story.append(img)
                
                if frame.annotations:
                    story.append(Paragraph(f"Annotations: {', '.join(frame.annotations)}", styles['Italic']))
                story.append(Spacer(1, 10))
        
        # Recommendations
        story.append(Paragraph("<b>Recommended Actions</b>", styles['Heading3']))
        recommendations = [
            "1. Save this report for your records",
            "2. Report this incident at cybercrime.gov.in",
            "3. Call the National Cyber Crime Helpline: 1930",
            "4. File an FIR at your local police station",
            "5. If money was transferred, contact your bank immediately",
            "6. Do not engage with the caller again"
        ]
        for rec in recommendations:
            story.append(Paragraph(rec, styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            "<i>Generated by Kavalan Lite - AI-Powered Scam Detection System</i>",
            styles['Italic']
        ))
        
        # Build PDF
        doc.build(story)
        logger.info(f"Digital FIR generated: {pdf_path}")
        
        return str(pdf_path)
    
    def _generate_text_report(self) -> str:
        """Generate plain text report as fallback"""
        if not self._session_id:
            return None
        
        session_dir = self.output_dir / self._session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = session_dir / f"Digital_FIR_{self._session_id}.txt"
        
        report_lines = [
            "=" * 60,
            "KAVALAN LITE - DIGITAL FIR",
            "Suspected Digital Arrest Scam Evidence Report",
            "=" * 60,
            "",
            "SESSION INFORMATION",
            "-" * 40,
            f"Report ID: {self._session_id}",
            f"Start Time: {self._session_start.strftime('%Y-%m-%d %H:%M:%S') if self._session_start else 'Unknown'}",
            f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Maximum Threat Score: {self._max_threat_score:.1f}/10",
            f"Total Threats Detected: {len(self._threat_events)}",
            "",
            "⚠️ IMPORTANT LEGAL INFORMATION",
            "-" * 40,
            '"Digital Arrest" is NOT a legal concept in India.',
            "No law enforcement agency conducts arrests via video call.",
            "",
            "DETECTED THREAT EVENTS",
            "-" * 40,
        ]
        
        for i, event in enumerate(self._threat_events, 1):
            event_time = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
            report_lines.extend([
                f"Event {i}: [{event_time}] {event.threat_type.upper()} (Score: {event.threat_score:.1f})",
                f"  Description: {event.description}",
                f"  Transcript: {event.audio_transcript}" if event.audio_transcript else "",
                ""
            ])
        
        report_lines.extend([
            "",
            "RECOMMENDED ACTIONS",
            "-" * 40,
            "1. Report at cybercrime.gov.in",
            "2. Call Cyber Crime Helpline: 1930",
            "3. File FIR at local police station",
            "4. Contact bank if money was transferred",
            "",
            "=" * 60,
            "Generated by Kavalan Lite",
        ])
        
        with open(report_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Text report generated: {report_path}")
        return str(report_path)
    
    def get_buffer_status(self) -> Dict:
        """Get current buffer status"""
        return {
            "session_id": self._session_id,
            "is_recording": self._is_recording,
            "frames_buffered": len(self._frame_buffer),
            "audio_chunks_buffered": len(self._audio_buffer),
            "threat_events": len(self._threat_events),
            "max_threat_score": self._max_threat_score,
            "auto_committed": self._committed
        }
    
    def clear_buffers(self):
        """Clear all buffers (call when starting fresh)"""
        with self._lock:
            self._frame_buffer.clear()
            self._audio_buffer.clear()
            self._threat_events.clear()
            self._max_threat_score = 0.0
            self._committed = False
            logger.info("Evidence buffers cleared")
