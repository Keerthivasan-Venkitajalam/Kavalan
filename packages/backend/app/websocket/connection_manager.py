"""
WebSocket connection manager for real-time alerts
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for real-time threat alerts"""
    
    def __init__(self):
        # Map session_id to set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map WebSocket to session_id for cleanup
        self.connection_sessions: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        self.connection_sessions[websocket] = session_id
        
        logger.info(
            f"WebSocket connected for session {session_id}. "
            f"Total connections: {len(self.active_connections[session_id])}"
        )
        
        # Send connection confirmation
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        session_id = self.connection_sessions.get(websocket)
        
        if session_id and session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            
            # Clean up empty session
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
            
            logger.info(f"WebSocket disconnected for session {session_id}")
        
        if websocket in self.connection_sessions:
            del self.connection_sessions[websocket]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_session(self, message: dict, session_id: str):
        """Broadcast a message to all connections for a session"""
        if session_id not in self.active_connections:
            logger.warning(f"No active connections for session {session_id}")
            return
        
        # Create a copy to avoid modification during iteration
        connections = list(self.active_connections[session_id])
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(
                    f"Failed to broadcast to connection in session {session_id}: {e}"
                )
                self.disconnect(connection)
    
    async def send_threat_alert(
        self,
        session_id: str,
        threat_score: float,
        threat_level: str,
        message: str,
        modality_scores: dict,
        explanation: list,
        confidence: float
    ):
        """Send a threat alert to all connections for a session"""
        alert = {
            "type": "threat_alert",
            "session_id": session_id,
            "threat_score": threat_score,
            "threat_level": threat_level,
            "message": message,
            "modality_scores": modality_scores,
            "explanation": explanation,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_session(alert, session_id)
        logger.info(
            f"Threat alert sent to session {session_id}: "
            f"level={threat_level}, score={threat_score}"
        )
    
    async def send_status_update(
        self,
        session_id: str,
        status: str,
        details: dict = None
    ):
        """Send a status update to all connections for a session"""
        update = {
            "type": "status_update",
            "session_id": session_id,
            "status": status,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_session(update, session_id)
    
    def get_connection_count(self, session_id: str = None) -> int:
        """Get the number of active connections"""
        if session_id:
            return len(self.active_connections.get(session_id, set()))
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_active_sessions(self) -> list:
        """Get list of session IDs with active connections"""
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()
