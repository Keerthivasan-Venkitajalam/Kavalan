"""
Reporter module for Kavalan Lite
Handles database operations and alert logging
"""

import sqlite3
import logging
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
import json

logger = logging.getLogger(__name__)

@dataclass
class ScamReport:
    """Data model for scam incident reports"""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    final_score: float = 0.0
    visual_score: float = 0.0
    liveness_score: float = 0.0
    audio_score: float = 0.0
    detected_keywords: str = ""  # JSON string of detected keywords
    phone_number: Optional[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Set timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'final_score': self.final_score,
            'visual_score': self.visual_score,
            'liveness_score': self.liveness_score,
            'audio_score': self.audio_score,
            'detected_keywords': self.detected_keywords,
            'phone_number': self.phone_number,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ScamReport':
        """Create ScamReport from dictionary"""
        timestamp = None
        if data.get('timestamp'):
            timestamp = datetime.fromisoformat(data['timestamp'])
        
        return cls(
            id=data.get('id'),
            timestamp=timestamp,
            final_score=data.get('final_score', 0.0),
            visual_score=data.get('visual_score', 0.0),
            liveness_score=data.get('liveness_score', 0.0),
            audio_score=data.get('audio_score', 0.0),
            detected_keywords=data.get('detected_keywords', ''),
            phone_number=data.get('phone_number'),
            notes=data.get('notes')
        )

class Reporter:
    """
    Handles logging and database operations for scam detection incidents
    """
    
    def __init__(self, db_path: str = "database/kavalan.db", log_path: str = "logs/alerts.log"):
        """
        Initialize reporter with database and log file paths
        
        Args:
            db_path: Path to SQLite database file
            log_path: Path to alert log file
        """
        self.db_path = db_path
        self.log_path = log_path
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        # Initialize database
        self.init_database()
        
        # Set up file logger for alerts
        self.alert_logger = logging.getLogger('kavalan_alerts')
        self.alert_logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.alert_logger.handlers[:]:
            self.alert_logger.removeHandler(handler)
        
        # Add file handler
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.alert_logger.addHandler(file_handler)
        
        logger.info(f"Reporter initialized with db: {db_path}, log: {log_path}")
    
    def init_database(self) -> None:
        """Initialize SQLite database with required schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create scam_reports table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scam_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        final_score REAL NOT NULL,
                        visual_score REAL NOT NULL,
                        liveness_score REAL NOT NULL,
                        audio_score REAL NOT NULL,
                        detected_keywords TEXT,
                        phone_number TEXT,
                        notes TEXT
                    )
                ''')
                
                # Create indexes for better query performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON scam_reports(timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_final_score 
                    ON scam_reports(final_score)
                ''')
                
                conn.commit()
                logger.info("Database schema initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def log_alert(self, fusion_result, additional_info: dict = None) -> None:
        """
        Log alert to file with detailed information
        
        Args:
            fusion_result: FusionResult object from fusion engine
            additional_info: Optional dictionary with extra information
        """
        try:
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'final_score': fusion_result.final_score,
                'visual_score': fusion_result.visual_score,
                'liveness_score': fusion_result.liveness_score,
                'audio_score': fusion_result.audio_score,
                'is_alert': fusion_result.is_alert,
                'alert_message': fusion_result.alert_message
            }
            
            if additional_info:
                alert_data.update(additional_info)
            
            # Log as JSON for structured logging
            self.alert_logger.info(json.dumps(alert_data, ensure_ascii=False))
            
            logger.debug(f"Alert logged: score={fusion_result.final_score:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
    
    def save_report(self, report: ScamReport) -> int:
        """
        Save scam report to database
        
        Args:
            report: ScamReport object to save
            
        Returns:
            ID of the saved report
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO scam_reports 
                    (timestamp, final_score, visual_score, liveness_score, 
                     audio_score, detected_keywords, phone_number, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report.timestamp,
                    report.final_score,
                    report.visual_score,
                    report.liveness_score,
                    report.audio_score,
                    report.detected_keywords,
                    report.phone_number,
                    report.notes
                ))
                
                report_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Report saved with ID: {report_id}")
                return report_id
                
        except sqlite3.Error as e:
            logger.error(f"Failed to save report: {e}")
            raise
    
    def get_reports(self, limit: int = 100, min_score: float = 0.0) -> List[ScamReport]:
        """
        Retrieve recent reports from database
        
        Args:
            limit: Maximum number of reports to retrieve
            min_score: Minimum final score to filter by
            
        Returns:
            List of ScamReport objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, timestamp, final_score, visual_score, liveness_score,
                           audio_score, detected_keywords, phone_number, notes
                    FROM scam_reports
                    WHERE final_score >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (min_score, limit))
                
                reports = []
                for row in cursor.fetchall():
                    report = ScamReport(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]) if row[1] else None,
                        final_score=row[2],
                        visual_score=row[3],
                        liveness_score=row[4],
                        audio_score=row[5],
                        detected_keywords=row[6] or "",
                        phone_number=row[7],
                        notes=row[8]
                    )
                    reports.append(report)
                
                logger.debug(f"Retrieved {len(reports)} reports")
                return reports
                
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve reports: {e}")
            return []
    
    def get_report_by_id(self, report_id: int) -> Optional[ScamReport]:
        """
        Get specific report by ID
        
        Args:
            report_id: ID of the report to retrieve
            
        Returns:
            ScamReport object or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, timestamp, final_score, visual_score, liveness_score,
                           audio_score, detected_keywords, phone_number, notes
                    FROM scam_reports
                    WHERE id = ?
                ''', (report_id,))
                
                row = cursor.fetchone()
                if row:
                    return ScamReport(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]) if row[1] else None,
                        final_score=row[2],
                        visual_score=row[3],
                        liveness_score=row[4],
                        audio_score=row[5],
                        detected_keywords=row[6] or "",
                        phone_number=row[7],
                        notes=row[8]
                    )
                
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve report {report_id}: {e}")
            return None
    
    def get_statistics(self) -> dict:
        """
        Get database statistics
        
        Returns:
            Dictionary with statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total reports
                cursor.execute('SELECT COUNT(*) FROM scam_reports')
                total_reports = cursor.fetchone()[0]
                
                # High-risk reports (score > 8)
                cursor.execute('SELECT COUNT(*) FROM scam_reports WHERE final_score > 8.0')
                high_risk_reports = cursor.fetchone()[0]
                
                # Average score
                cursor.execute('SELECT AVG(final_score) FROM scam_reports')
                avg_score = cursor.fetchone()[0] or 0.0
                
                # Latest report timestamp
                cursor.execute('SELECT MAX(timestamp) FROM scam_reports')
                latest_timestamp = cursor.fetchone()[0]
                
                return {
                    'total_reports': total_reports,
                    'high_risk_reports': high_risk_reports,
                    'average_score': round(avg_score, 2),
                    'latest_report': latest_timestamp,
                    'alert_rate': round((high_risk_reports / total_reports * 100) if total_reports > 0 else 0, 1)
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'total_reports': 0,
                'high_risk_reports': 0,
                'average_score': 0.0,
                'latest_report': None,
                'alert_rate': 0.0
            }