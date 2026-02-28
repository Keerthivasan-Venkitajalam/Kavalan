/**
 * Background Service Worker
 * 
 * Orchestrates communication between content script and backend API.
 * Handles encryption, WebSocket connections, and alert management.
 */

import { EncryptedPayload, ThreatAlert, DetectionStatus } from '../types';
import { encryptMedia } from '../utils/encryption';
import { getLocalizedAlertMessage } from '../i18n/alertMessages';
import { Language } from '../i18n/translations';

// WebSocket connection to backend
let wsConnection: WebSocket | null = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY_BASE = 1000; // 1 second

// Session state
let currentSessionId: string | null = null;
let detectionStatus: DetectionStatus = {
  audioActive: false,
  visualActive: false,
  livenessActive: false,
  lastUpdate: Date.now()
};

/**
 * Initialize background service worker
 */
chrome.runtime.onInstalled.addListener(() => {
  console.log('Kavalan extension installed');
  
  // Initialize default settings
  chrome.storage.local.set({
    preferences: {
      language: 'en',
      alertVolume: 0.8,
      stealthMode: false,
      autoReport: true
    }
  });
});

/**
 * Handle messages from content script
 */
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  switch (message.type) {
    case 'MEDIA_CAPTURED':
      handleMediaCapture(message.payload)
        .then(() => sendResponse({ success: true }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true; // Keep channel open for async response
      
    case 'SESSION_STARTED':
      handleSessionStart(message.sessionId)
        .then(() => sendResponse({ success: true }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'SESSION_ENDED':
      handleSessionEnd()
        .then(() => sendResponse({ success: true }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'GET_STATUS':
      sendResponse({ status: detectionStatus });
      break;
      
    default:
      console.warn('Unknown message type:', message.type);
  }
});

/**
 * Handle media capture from content script
 */
async function handleMediaCapture(payload: any): Promise<void> {
  try {
    // Encrypt media data
    const encrypted = await encryptMedia(payload.data, payload.type);
    
    // Send to backend API
    await sendToBackend(encrypted);
    
    // Update detection status
    updateDetectionStatus(payload.type);
  } catch (error) {
    console.error('Error handling media capture:', error);
    throw error;
  }
}

/**
 * Handle session start
 */
async function handleSessionStart(sessionId: string): Promise<void> {
  currentSessionId = sessionId;
  
  // Connect WebSocket for real-time alerts
  await connectWebSocket();
  
  // Reset detection status
  detectionStatus = {
    audioActive: true,
    visualActive: true,
    livenessActive: true,
    lastUpdate: Date.now()
  };
}

/**
 * Handle session end
 */
async function handleSessionEnd(): Promise<void> {
  // Disconnect WebSocket
  if (wsConnection) {
    wsConnection.close();
    wsConnection = null;
  }
  
  currentSessionId = null;
  
  // Reset detection status
  detectionStatus = {
    audioActive: false,
    visualActive: false,
    livenessActive: false,
    lastUpdate: Date.now()
  };
}

/**
 * Send encrypted media to backend API
 */
async function sendToBackend(payload: EncryptedPayload): Promise<void> {
  const settings = await chrome.storage.local.get(['apiEndpoint', 'authToken']);
  const endpoint = settings.apiEndpoint || 'https://api.kavalan.in';
  
  const response = await fetch(`${endpoint}/api/v1/analyze/media`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${settings.authToken || ''}`
    },
    body: JSON.stringify(payload)
  });
  
  if (!response.ok) {
    throw new Error(`Backend API error: ${response.status}`);
  }
}

/**
 * Connect WebSocket for real-time alerts
 */
async function connectWebSocket(): Promise<void> {
  const settings = await chrome.storage.local.get(['apiEndpoint', 'authToken']);
  const endpoint = settings.apiEndpoint || 'wss://api.kavalan.in';
  const wsUrl = `${endpoint}/ws?session=${currentSessionId}&token=${settings.authToken || ''}`;
  
  try {
    wsConnection = new WebSocket(wsUrl);
    
    wsConnection.onopen = () => {
      console.log('WebSocket connected');
      reconnectAttempts = 0;
    };
    
    wsConnection.onmessage = (event) => {
      const alert: ThreatAlert = JSON.parse(event.data);
      handleThreatAlert(alert);
    };
    
    wsConnection.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    wsConnection.onclose = () => {
      console.log('WebSocket disconnected');
      
      // Attempt reconnection with exponential backoff
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS && currentSessionId) {
        const delay = RECONNECT_DELAY_BASE * Math.pow(2, reconnectAttempts);
        reconnectAttempts++;
        
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
        setTimeout(() => connectWebSocket(), delay);
      }
    };
  } catch (error) {
    console.error('Failed to connect WebSocket:', error);
    throw error;
  }
}

/**
 * Handle threat alert from backend
 */
async function handleThreatAlert(alert: ThreatAlert): Promise<void> {
  console.log('Threat alert received:', alert);
  
  // Get user's preferred language
  const result = await chrome.storage.local.get(['preferences']);
  const language = (result.preferences?.language || 'en') as Language;
  
  // Get localized alert message
  const localizedMessage = getLocalizedAlertMessage(alert.level, language);
  
  // Create localized alert
  const localizedAlert: ThreatAlert = {
    ...alert,
    message: localizedMessage
  };
  
  // Show notification if threat level is high or critical
  if (alert.level === 'high' || alert.level === 'critical') {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: '', // Empty string for now, will be replaced with actual icon
      title: 'Kavalan Alert',
      message: localizedMessage,
      priority: 2
    });
  }
  
  // Update badge
  chrome.action.setBadgeText({ text: alert.level === 'critical' ? '!' : '' });
  chrome.action.setBadgeBackgroundColor({ 
    color: alert.level === 'critical' ? '#FF0000' : '#FFA500' 
  });
  
  // Store localized alert in local storage for popup
  chrome.storage.local.get(['alerts'], (result) => {
    const alerts = result.alerts || [];
    alerts.push(localizedAlert);
    
    // Keep only last 10 alerts
    if (alerts.length > 10) {
      alerts.shift();
    }
    
    chrome.storage.local.set({ alerts });
  });
}

/**
 * Update detection status
 */
function updateDetectionStatus(mediaType: 'audio' | 'video'): void {
  if (mediaType === 'audio') {
    detectionStatus.audioActive = true;
  } else if (mediaType === 'video') {
    detectionStatus.visualActive = true;
    detectionStatus.livenessActive = true;
  }
  
  detectionStatus.lastUpdate = Date.now();
}

// Export for testing
export {
  handleMediaCapture,
  handleSessionStart,
  handleSessionEnd,
  connectWebSocket,
  handleThreatAlert
};
