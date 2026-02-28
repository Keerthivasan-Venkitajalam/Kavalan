/**
 * TypeScript Type Definitions
 * 
 * Shared types for the browser extension.
 */

// Media types
export interface AudioChunk {
  data: Float32Array;
  sampleRate: number;
  timestamp: number;
  duration: number;
}

export interface VideoFrame {
  imageData: ImageData;
  timestamp: number;
  width: number;
  height: number;
}

// Encryption types
export interface EncryptedPayload {
  data: ArrayBuffer;
  iv: Uint8Array;
  timestamp: number;
  sessionId: string;
  type: 'audio' | 'video';
}

// Alert types
export interface ThreatAlert {
  score: number;
  level: 'low' | 'moderate' | 'high' | 'critical';
  message: string;
  timestamp: number;
  modalities: {
    audio: number;
    visual: number;
    liveness: number;
  };
}

// Detection status
export interface DetectionStatus {
  audioActive: boolean;
  visualActive: boolean;
  livenessActive: boolean;
  lastUpdate: number;
}

// Platform types
export type Platform = 'meet' | 'zoom' | 'teams' | null;

// User preferences
export interface UserPreferences {
  language: string;
  alertVolume: number;
  stealthMode: boolean;
  autoReport: boolean;
}

// Extension settings
export interface ExtensionSettings {
  userId?: string;
  sessionId?: string;
  apiEndpoint?: string;
  authToken?: string;
  preferences: UserPreferences;
  cachedPatterns?: ThreatPattern[];
  lastSync?: number;
}

// Threat pattern
export interface ThreatPattern {
  category: string;
  keywords: string[];
  weight: number;
  language: string;
}

// Message types for chrome.runtime.sendMessage
export type MessageType =
  | 'MEDIA_CAPTURED'
  | 'SESSION_STARTED'
  | 'SESSION_ENDED'
  | 'GET_STATUS';

export interface Message {
  type: MessageType;
  payload?: any;
  sessionId?: string;
}

// Response types
export interface MessageResponse {
  success: boolean;
  error?: string;
  status?: DetectionStatus;
}
