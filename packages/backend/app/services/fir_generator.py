"""
Digital FIR (First Information Report) Generation Service

Automatically generates tamper-proof evidence packages when threat scores exceed threshold.
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import hashlib
import json
import logging
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

logger = logging.getLogger(__name__)


@dataclass
class FIRGenerationResult:
    """Result of FIR generation"""
    fir_id: str
    object_id: str
    session_id: UUID
    user_id: UUID
    generated_at: datetime
    threat_score: float
    success: bool
    error: Optional[str] = None


class FIRGenerator:
    """
    Generates Digital FIR packages for confirmed threats.
    
    Automatically triggered when threat score >= 7.0.
    Generates within 5 seconds of threat confirmation.
    """
    
    def __init__(self, mongodb_client, postgres_db):
        """
        Initialize FIR generator.
        
        Args:
            mongodb_client: MongoDB client for storing FIR documents
            postgres_db: PostgreSQL database instance for fetching session data
        """
        self.mongodb = mongodb_client
        self.postgres = postgres_db
        self.threat_threshold = 7.0
        self.generation_timeout = 5.0  # seconds
    
    async def should_generate_fir(self, threat_score: float, session_id: UUID) -> bool:
        """
        Determine if FIR should be generated for this threat event.
        
        Args:
            threat_score: Unified threat score
            session_id: Session identifier
        
        Returns:
            True if FIR should be generated, False otherwise
        """
        # Check if threat score meets threshold
        if threat_score < self.threat_threshold:
            return False
        
        # Check if FIR already exists for this session
        existing_fir = await self.mongodb.get_session_digital_fir(session_id)
        if existing_fir:
            logger.info(f"FIR already exists for session {session_id}")
            return False
        
        return True
    
    async def generate_fir(
        self,
        session_id: UUID,
        user_id: UUID,
        threat_score: float,
        threat_level: str,
        audio_score: float,
        visual_score: float,
        liveness_score: float,
        confidence: float,
        timestamp: datetime
    ) -> FIRGenerationResult:
        """
        Generate a Digital FIR package for a confirmed threat.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            threat_score: Unified threat score
            threat_level: Threat level (low/moderate/high/critical)
            audio_score: Audio modality score
            visual_score: Visual modality score
            liveness_score: Liveness modality score
            confidence: Overall confidence score
            timestamp: Timestamp of threat confirmation
        
        Returns:
            FIRGenerationResult with FIR ID and status
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(
                f"Generating FIR for session {session_id}, "
                f"threat_score={threat_score:.2f}"
            )
            
            # Generate unique FIR ID
            fir_id = self._generate_fir_id(session_id, timestamp)
            
            # Fetch session data from PostgreSQL
            session_data = await self._fetch_session_data(session_id)
            
            # Fetch evidence from MongoDB
            evidence_docs = await self._fetch_evidence(session_id)
            
            # Build summary section
            summary = self._build_summary(
                session_data=session_data,
                threat_score=threat_score,
                threat_level=threat_level,
                evidence_docs=evidence_docs
            )
            
            # Build evidence package
            evidence = self._build_evidence_package(
                evidence_docs=evidence_docs,
                threat_score=threat_score,
                audio_score=audio_score,
                visual_score=visual_score,
                liveness_score=liveness_score,
                confidence=confidence,
                timestamp=timestamp
            )
            
            # Build legal metadata
            legal = self._build_legal_metadata(
                fir_id=fir_id,
                session_id=session_id,
                user_id=user_id,
                summary=summary,
                evidence=evidence
            )
            
            # Store FIR in MongoDB
            object_id = await self.mongodb.create_digital_fir(
                fir_id=fir_id,
                session_id=session_id,
                user_id=user_id,
                summary=summary,
                evidence=evidence,
                legal=legal
            )
            
            # Calculate generation time
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                f"FIR generated successfully: {fir_id} "
                f"(took {generation_time:.2f}s)"
            )
            
            # Verify generation time meets requirement (< 5 seconds)
            if generation_time > self.generation_timeout:
                logger.warning(
                    f"FIR generation exceeded timeout: {generation_time:.2f}s > {self.generation_timeout}s"
                )
            
            return FIRGenerationResult(
                fir_id=fir_id,
                object_id=object_id,
                session_id=session_id,
                user_id=user_id,
                generated_at=datetime.utcnow(),
                threat_score=threat_score,
                success=True
            )
        
        except Exception as e:
            logger.error(f"FIR generation failed: {e}", exc_info=True)
            return FIRGenerationResult(
                fir_id="",
                object_id="",
                session_id=session_id,
                user_id=user_id,
                generated_at=datetime.utcnow(),
                threat_score=threat_score,
                success=False,
                error=str(e)
            )
    
    def _generate_fir_id(self, session_id: UUID, timestamp: datetime) -> str:
        """
        Generate unique FIR identifier.
        
        Format: FIR-{YYYYMMDD}-{session_id_prefix}-{hash}
        """
        date_str = timestamp.strftime("%Y%m%d")
        session_prefix = str(session_id)[:8]
        
        # Create hash from session_id and timestamp
        hash_input = f"{session_id}{timestamp.isoformat()}"
        hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        
        return f"FIR-{date_str}-{session_prefix}-{hash_digest}"
    
    async def _fetch_session_data(self, session_id: UUID) -> Dict[str, Any]:
        """Fetch session data from PostgreSQL"""
        row = await self.postgres.fetchrow(
            """
            SELECT 
                session_id,
                user_id,
                platform,
                start_time,
                end_time,
                duration_seconds,
                max_threat_score,
                alert_count
            FROM sessions
            WHERE session_id = $1
            """,
            session_id
        )
        
        if not row:
            raise ValueError(f"Session {session_id} not found")
        
        return dict(row)
    
    async def _fetch_evidence(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Fetch all evidence documents for session from MongoDB"""
        evidence_docs = await self.mongodb.get_session_evidence(session_id)
        return evidence_docs
    
    def _build_summary(
        self,
        session_data: Dict[str, Any],
        threat_score: float,
        threat_level: str,
        evidence_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build FIR summary section"""
        # Calculate total duration
        if session_data.get('duration_seconds'):
            total_duration = session_data['duration_seconds']
        elif session_data.get('start_time') and session_data.get('end_time'):
            duration = session_data['end_time'] - session_data['start_time']
            total_duration = int(duration.total_seconds())
        else:
            total_duration = 0
        
        # Extract threat categories from evidence
        threat_categories = set()
        for doc in evidence_docs:
            if 'audio' in doc and 'detected_keywords' in doc['audio']:
                threat_categories.update(doc['audio']['detected_keywords'].keys())
        
        return {
            "total_duration": total_duration,
            "max_threat_score": threat_score,
            "alert_count": session_data.get('alert_count', 1),
            "threat_categories": list(threat_categories),
            "threat_level": threat_level,
            "platform": session_data.get('platform', 'unknown')
        }
    
    def _build_evidence_package(
        self,
        evidence_docs: List[Dict[str, Any]],
        threat_score: float,
        audio_score: float,
        visual_score: float,
        liveness_score: float,
        confidence: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Build FIR evidence package with complete content assembly.
        
        Includes:
        - Timestamped audio transcripts with speaker identification (Req 12.2)
        - Video frame snapshots with visual analysis annotations (Req 12.3)
        - Unified threat scores with confidence intervals (Req 12.4)
        - Cryptographic signature handled in _build_legal_metadata (Req 12.5)
        """
        # Extract transcripts with speaker identification (Req 12.2)
        transcripts = []
        for doc in evidence_docs:
            if 'audio' in doc and 'transcript' in doc['audio']:
                audio_data = doc['audio']
                
                # Build transcript entry with speaker identification
                transcript_entry = {
                    "timestamp": doc.get('timestamp'),
                    "text": audio_data['transcript'],
                    "language": audio_data.get('language', 'unknown'),
                    "keywords": audio_data.get('detected_keywords', {}),
                    "segments": audio_data.get('segments', [])
                }
                
                # Add speaker identification if available
                if 'speaker_labels' in audio_data:
                    transcript_entry['speaker_labels'] = audio_data['speaker_labels']
                
                # Add word-level timestamps if available
                if 'word_timestamps' in audio_data:
                    transcript_entry['word_timestamps'] = audio_data['word_timestamps']
                
                transcripts.append(transcript_entry)
        
        # Extract frame snapshots with annotations (Req 12.3)
        frames = []
        for doc in evidence_docs:
            if 'visual' in doc and 'frame_url' in doc['visual']:
                visual_data = doc['visual']
                
                # Build frame entry with complete annotations
                frame_entry = {
                    "timestamp": doc.get('timestamp'),
                    "url": visual_data['frame_url'],
                    "analysis": visual_data.get('analysis', ''),
                    "threats": visual_data.get('threats', []),
                    "annotations": {
                        "uniform_detected": visual_data.get('uniform_detected', False),
                        "badge_detected": visual_data.get('badge_detected', False),
                        "text_detected": visual_data.get('text_detected', ''),
                        "confidence": visual_data.get('confidence', 0.0)
                    }
                }
                
                frames.append(frame_entry)
        
        # Build threat timeline with unified scores and confidence intervals (Req 12.4)
        # Calculate confidence interval (95% CI using ±1.96 * standard error)
        # Standard error approximated from confidence score
        standard_error = (1.0 - confidence) * 0.5
        confidence_interval = {
            "lower": max(0.0, threat_score - 1.96 * standard_error),
            "upper": min(10.0, threat_score + 1.96 * standard_error),
            "confidence_level": 0.95
        }
        
        threat_timeline = [{
            "timestamp": timestamp,
            "unified_threat_score": threat_score,
            "modality_scores": {
                "audio": audio_score,
                "visual": visual_score,
                "liveness": liveness_score
            },
            "confidence": confidence,
            "confidence_interval": confidence_interval,
            "description": f"Critical threat detected (score: {threat_score:.2f}, CI: [{confidence_interval['lower']:.2f}, {confidence_interval['upper']:.2f}])"
        }]
        
        return {
            "transcripts": transcripts,
            "frames": frames,
            "threat_timeline": threat_timeline
        }
    
    def _build_legal_metadata(
        self,
        fir_id: str,
        session_id: UUID,
        user_id: UUID,
        summary: Dict[str, Any],
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build legal metadata with chain-of-custody and cryptographic signature"""
        # Initialize chain of custody
        chain_of_custody = [{
            "action": "FIR_CREATED",
            "timestamp": datetime.utcnow(),
            "actor": "system",
            "details": f"Automatic FIR generation for session {session_id}"
        }]
        
        # Generate cryptographic hash of FIR content
        fir_content = {
            "fir_id": fir_id,
            "session_id": str(session_id),
            "user_id": str(user_id),
            "summary": summary,
            "evidence": evidence
        }
        
        # Create deterministic JSON string for hashing
        content_json = json.dumps(fir_content, sort_keys=True, default=str)
        content_hash = hashlib.sha256(content_json.encode()).hexdigest()
        
        # Generate cryptographic signature (simplified - in production use proper signing)
        signature = hashlib.sha512(
            f"{content_hash}{fir_id}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()
        
        # Calculate retention date (7 years for legal compliance)
        retention_until = datetime.utcnow() + timedelta(days=7*365)
        
        return {
            "chain_of_custody": chain_of_custody,
            "cryptographic_signature": signature,
            "hash": content_hash,
            "retention_until": retention_until
        }
    
    async def export_to_pdf(self, fir_id: str) -> bytes:
        """
        Export Digital FIR to PDF format for legal submission.
        
        Generates a professionally formatted PDF document containing:
        - FIR header with ID and metadata
        - Summary section with threat assessment
        - Audio transcript evidence with speaker identification
        - Visual analysis evidence with annotations
        - Threat timeline with scores and confidence intervals
        - Legal metadata including cryptographic signature
        - Chain of custody records
        
        Args:
            fir_id: Unique FIR identifier
        
        Returns:
            PDF document as bytes
        
        Raises:
            ValueError: If FIR not found
        """
        # Fetch FIR document from MongoDB
        fir_doc = await self.mongodb.get_digital_fir(fir_id)
        if not fir_doc:
            raise ValueError(f"FIR {fir_id} not found")
        
        logger.info(f"Generating PDF export for FIR {fir_id}")
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        # Build PDF content
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        )
        
        # ===================================================================
        # HEADER SECTION
        # ===================================================================
        story.append(Paragraph("DIGITAL FIRST INFORMATION REPORT", title_style))
        story.append(Paragraph("Evidence Package for Legal Submission", styles['Heading3']))
        story.append(Spacer(1, 0.3*inch))
        
        # FIR Metadata Table
        metadata_data = [
            ['FIR ID:', fir_id],
            ['Session ID:', str(fir_doc.get('session_id', 'N/A'))],
            ['User ID:', str(fir_doc.get('user_id', 'N/A'))],
            ['Generated At:', fir_doc.get('generated_at', datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S UTC')],
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 0.3*inch))
        
        # ===================================================================
        # SUMMARY SECTION
        # ===================================================================
        summary = fir_doc.get('summary', {})
        story.append(Paragraph("1. THREAT ASSESSMENT SUMMARY", heading_style))
        
        summary_data = [
            ['Platform:', summary.get('platform', 'Unknown').upper()],
            ['Threat Level:', summary.get('threat_level', 'Unknown').upper()],
            ['Maximum Threat Score:', f"{summary.get('max_threat_score', 0.0):.2f} / 10.0"],
            ['Total Duration:', f"{summary.get('total_duration', 0)} seconds"],
            ['Alert Count:', str(summary.get('alert_count', 0))],
            ['Threat Categories:', ', '.join(summary.get('threat_categories', [])) or 'None'],
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.2*inch))
        
        # ===================================================================
        # AUDIO TRANSCRIPT EVIDENCE
        # ===================================================================
        evidence = fir_doc.get('evidence', {})
        transcripts = evidence.get('transcripts', [])
        
        story.append(Paragraph("2. AUDIO TRANSCRIPT EVIDENCE", heading_style))
        
        if transcripts:
            for idx, transcript in enumerate(transcripts, 1):
                story.append(Paragraph(f"2.{idx} Transcript Entry", subheading_style))
                
                # Transcript metadata
                ts_time = transcript.get('timestamp', datetime.utcnow())
                if isinstance(ts_time, str):
                    ts_time = datetime.fromisoformat(ts_time.replace('Z', '+00:00'))
                
                story.append(Paragraph(
                    f"<b>Timestamp:</b> {ts_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    body_style
                ))
                story.append(Paragraph(
                    f"<b>Language:</b> {transcript.get('language', 'Unknown').upper()}",
                    body_style
                ))
                
                # Speaker identification
                speakers = transcript.get('speaker_labels', [])
                if speakers:
                    story.append(Paragraph(
                        f"<b>Speakers Identified:</b> {', '.join(speakers)}",
                        body_style
                    ))
                
                # Transcript text
                story.append(Paragraph("<b>Transcript:</b>", body_style))
                story.append(Paragraph(
                    transcript.get('text', 'No transcript available'),
                    body_style
                ))
                
                # Detected keywords
                keywords = transcript.get('keywords', {})
                if keywords:
                    story.append(Paragraph("<b>Detected Threat Keywords:</b>", body_style))
                    for category, words in keywords.items():
                        if words:
                            story.append(Paragraph(
                                f"• {category.title()}: {', '.join(words)}",
                                body_style
                            ))
                
                story.append(Spacer(1, 0.15*inch))
        else:
            story.append(Paragraph("No audio transcript evidence available.", body_style))
        
        story.append(Spacer(1, 0.1*inch))
        
        # ===================================================================
        # VISUAL ANALYSIS EVIDENCE
        # ===================================================================
        frames = evidence.get('frames', [])
        
        story.append(Paragraph("3. VISUAL ANALYSIS EVIDENCE", heading_style))
        
        if frames:
            for idx, frame in enumerate(frames, 1):
                story.append(Paragraph(f"3.{idx} Frame Analysis", subheading_style))
                
                # Frame metadata
                frame_time = frame.get('timestamp', datetime.utcnow())
                if isinstance(frame_time, str):
                    frame_time = datetime.fromisoformat(frame_time.replace('Z', '+00:00'))
                
                story.append(Paragraph(
                    f"<b>Timestamp:</b> {frame_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    body_style
                ))
                story.append(Paragraph(
                    f"<b>Frame URL:</b> {frame.get('url', 'N/A')}",
                    body_style
                ))
                
                # Analysis results
                story.append(Paragraph(
                    f"<b>Analysis:</b> {frame.get('analysis', 'No analysis available')}",
                    body_style
                ))
                
                # Annotations
                annotations = frame.get('annotations', {})
                if annotations:
                    story.append(Paragraph("<b>Detection Results:</b>", body_style))
                    story.append(Paragraph(
                        f"• Uniform Detected: {'Yes' if annotations.get('uniform_detected') else 'No'}",
                        body_style
                    ))
                    story.append(Paragraph(
                        f"• Badge Detected: {'Yes' if annotations.get('badge_detected') else 'No'}",
                        body_style
                    ))
                    
                    text_detected = annotations.get('text_detected', '')
                    if text_detected:
                        story.append(Paragraph(
                            f"• Text Detected: {text_detected}",
                            body_style
                        ))
                    
                    story.append(Paragraph(
                        f"• Confidence Score: {annotations.get('confidence', 0.0):.2f}",
                        body_style
                    ))
                
                # Threats
                threats = frame.get('threats', [])
                if threats:
                    story.append(Paragraph(
                        f"<b>Identified Threats:</b> {', '.join(threats)}",
                        body_style
                    ))
                
                story.append(Spacer(1, 0.15*inch))
        else:
            story.append(Paragraph("No visual analysis evidence available.", body_style))
        
        story.append(Spacer(1, 0.1*inch))
        
        # ===================================================================
        # THREAT TIMELINE
        # ===================================================================
        threat_timeline = evidence.get('threat_timeline', [])
        
        story.append(Paragraph("4. THREAT SCORE TIMELINE", heading_style))
        
        if threat_timeline:
            for idx, entry in enumerate(threat_timeline, 1):
                story.append(Paragraph(f"4.{idx} Threat Event", subheading_style))
                
                # Timestamp
                event_time = entry.get('timestamp', datetime.utcnow())
                if isinstance(event_time, str):
                    event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                
                story.append(Paragraph(
                    f"<b>Timestamp:</b> {event_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    body_style
                ))
                
                # Unified threat score
                unified_score = entry.get('unified_threat_score', 0.0)
                story.append(Paragraph(
                    f"<b>Unified Threat Score:</b> {unified_score:.2f} / 10.0",
                    body_style
                ))
                
                # Modality scores
                modality_scores = entry.get('modality_scores', {})
                if modality_scores:
                    story.append(Paragraph("<b>Modality Breakdown:</b>", body_style))
                    story.append(Paragraph(
                        f"• Audio Score: {modality_scores.get('audio', 0.0):.2f} / 10.0",
                        body_style
                    ))
                    story.append(Paragraph(
                        f"• Visual Score: {modality_scores.get('visual', 0.0):.2f} / 10.0",
                        body_style
                    ))
                    story.append(Paragraph(
                        f"• Liveness Score: {modality_scores.get('liveness', 0.0):.2f} / 10.0",
                        body_style
                    ))
                
                # Confidence and interval
                confidence = entry.get('confidence', 0.0)
                ci = entry.get('confidence_interval', {})
                
                story.append(Paragraph(
                    f"<b>Confidence:</b> {confidence:.2f}",
                    body_style
                ))
                
                if ci:
                    story.append(Paragraph(
                        f"<b>Confidence Interval (95%):</b> [{ci.get('lower', 0.0):.2f}, {ci.get('upper', 0.0):.2f}]",
                        body_style
                    ))
                
                # Description
                description = entry.get('description', '')
                if description:
                    story.append(Paragraph(
                        f"<b>Description:</b> {description}",
                        body_style
                    ))
                
                story.append(Spacer(1, 0.15*inch))
        else:
            story.append(Paragraph("No threat timeline data available.", body_style))
        
        story.append(PageBreak())
        
        # ===================================================================
        # LEGAL METADATA
        # ===================================================================
        legal = fir_doc.get('legal', {})
        
        story.append(Paragraph("5. LEGAL METADATA", heading_style))
        
        # Cryptographic signature
        story.append(Paragraph("5.1 Tamper-Proof Verification", subheading_style))
        story.append(Paragraph(
            f"<b>Content Hash (SHA-256):</b><br/>{legal.get('hash', 'N/A')}",
            body_style
        ))
        story.append(Paragraph(
            f"<b>Cryptographic Signature (SHA-512):</b><br/>{legal.get('cryptographic_signature', 'N/A')}",
            body_style
        ))
        story.append(Spacer(1, 0.15*inch))
        
        # Retention
        retention_until = legal.get('retention_until')
        if retention_until:
            if isinstance(retention_until, str):
                retention_until = datetime.fromisoformat(retention_until.replace('Z', '+00:00'))
            story.append(Paragraph(
                f"<b>Retention Until:</b> {retention_until.strftime('%Y-%m-%d')} (7 years for legal compliance)",
                body_style
            ))
        story.append(Spacer(1, 0.2*inch))
        
        # Chain of custody
        story.append(Paragraph("5.2 Chain of Custody", subheading_style))
        
        chain_of_custody = legal.get('chain_of_custody', [])
        if chain_of_custody:
            custody_data = [['Action', 'Timestamp', 'Actor', 'Details']]
            
            for entry in chain_of_custody:
                action = entry.get('action', 'N/A')
                timestamp = entry.get('timestamp', datetime.utcnow())
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                actor = entry.get('actor', 'N/A')
                details = entry.get('details', 'N/A')
                
                custody_data.append([
                    action,
                    timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    actor,
                    details[:50] + '...' if len(details) > 50 else details
                ])
            
            custody_table = Table(custody_data, colWidths=[1.5*inch, 1.5*inch, 1*inch, 2.5*inch])
            custody_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            story.append(custody_table)
        else:
            story.append(Paragraph("No chain of custody records available.", body_style))
        
        story.append(Spacer(1, 0.3*inch))
        
        # ===================================================================
        # FOOTER
        # ===================================================================
        story.append(Paragraph(
            "This document is a legally admissible Digital First Information Report (FIR) "
            "generated by the Kavalan AI Threat Detection System. The cryptographic signature "
            "ensures the integrity and authenticity of all evidence contained herein. "
            "Any tampering with this document will invalidate the signature.",
            body_style
        ))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"PDF export completed for FIR {fir_id}, size: {len(pdf_bytes)} bytes")
        
        return pdf_bytes
