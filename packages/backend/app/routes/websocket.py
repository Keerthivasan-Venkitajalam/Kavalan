"""
WebSocket endpoints for real-time alerts
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.websocket import manager
from jose import jwt, JWTError
from app.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def verify_websocket_token(token: str) -> dict:
    """Verify JWT token for WebSocket connection"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"WebSocket JWT verification failed: {e}")
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    session_id: str = Query(..., description="Session UUID")
):
    """
    WebSocket endpoint for real-time threat alerts.
    
    Clients connect with JWT token and session_id to receive:
    - Real-time threat alerts
    - Status updates
    - Connection lifecycle events
    
    **Requirements**: 4.5
    
    **Connection Lifecycle**:
    1. Client connects with token and session_id
    2. Server verifies token and accepts connection
    3. Server sends connection confirmation
    4. Server pushes threat alerts as they occur
    5. Client or server can close connection
    6. Server handles reconnection attempts
    
    **Message Types**:
    - `connection`: Connection status
    - `threat_alert`: Real-time threat detection
    - `status_update`: Session status changes
    - `error`: Error notifications
    """
    # Verify authentication
    user_data = await verify_websocket_token(token)
    
    if not user_data:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(f"WebSocket connection rejected: invalid token")
        return
    
    # Verify session belongs to user
    if user_data.get('session_id') != session_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(
            f"WebSocket connection rejected: session {session_id} "
            f"does not belong to user {user_data.get('user_id')}"
        )
        return
    
    # Accept connection
    await manager.connect(websocket, session_id)
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "ping":
                # Respond to ping with pong
                await manager.send_personal_message(
                    {"type": "pong", "timestamp": data.get("timestamp")},
                    websocket
                )
            
            elif message_type == "status_request":
                # Client requesting current status
                # TODO: Fetch from database and send
                await manager.send_personal_message(
                    {
                        "type": "status_response",
                        "session_id": session_id,
                        "status": "active"
                    },
                    websocket
                )
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected normally for session {session_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        manager.disconnect(websocket)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
