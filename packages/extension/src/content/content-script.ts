/**
 * Content Script
 * 
 * Injects into video conferencing pages and intercepts WebRTC streams.
 * Captures audio and video for threat analysis.
 */

import { detectPlatform } from '../utils/platform-detector';
import { AudioChunk, VideoFrame } from '../types';

// Session state
let sessionId: string | null = null;
let isMonitoring = false;
let audioContext: AudioContext | null = null;
let videoFrameInterval: number | null = null;

// Frame capture rate (1 FPS)
const FRAME_CAPTURE_INTERVAL = 1000; // 1 second

/**
 * Initialize content script
 */
function init(): void {
  console.log('Kavalan content script initialized');
  
  // Detect platform
  const platform = detectPlatform();
  console.log('Detected platform:', platform);
  
  if (!platform) {
    console.warn('Unsupported platform');
    return;
  }
  
  // Wait for page to load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setupWebRTCInterception());
  } else {
    setupWebRTCInterception();
  }
}

/**
 * Setup WebRTC stream interception
 */
function setupWebRTCInterception(): void {
  // Hook into getUserMedia
  const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  
  navigator.mediaDevices.getUserMedia = async function(constraints: MediaStreamConstraints): Promise<MediaStream> {
    console.log('getUserMedia called with constraints:', constraints);
    
    // Call original function
    const stream = await originalGetUserMedia(constraints);
    
    // Start monitoring if not already active
    if (!isMonitoring && (constraints.audio || constraints.video)) {
      startMonitoring(stream);
    }
    
    return stream;
  };
  
  // Hook into RTCPeerConnection
  const originalRTCPeerConnection = window.RTCPeerConnection;
  
  window.RTCPeerConnection = function(configuration?: RTCConfiguration): RTCPeerConnection {
    console.log('RTCPeerConnection created');
    
    const pc = new originalRTCPeerConnection(configuration);
    
    // Monitor track events
    pc.addEventListener('track', (event) => {
      console.log('Track received:', event.track.kind);
      
      if (event.streams && event.streams[0]) {
        if (!isMonitoring) {
          startMonitoring(event.streams[0]);
        }
      }
    });
    
    return pc;
  } as any;
  
  console.log('WebRTC interception setup complete');
}

/**
 * Start monitoring media streams
 */
function startMonitoring(stream: MediaStream): void {
  if (isMonitoring) {
    return;
  }
  
  isMonitoring = true;
  sessionId = generateSessionId();
  
  console.log('Starting monitoring for session:', sessionId);
  
  // Notify background service worker
  chrome.runtime.sendMessage({
    type: 'SESSION_STARTED',
    sessionId
  });
  
  // Setup audio capture
  const audioTracks = stream.getAudioTracks();
  if (audioTracks.length > 0) {
    setupAudioCapture(stream);
  }
  
  // Setup video capture
  const videoTracks = stream.getVideoTracks();
  if (videoTracks.length > 0) {
    setupVideoCapture(stream);
  }
  
  // Monitor stream end
  stream.addEventListener('inactive', () => {
    stopMonitoring();
  });
}

/**
 * Setup audio capture
 */
function setupAudioCapture(stream: MediaStream): void {
  try {
    audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    
    processor.onaudioprocess = (event) => {
      const audioData = event.inputBuffer.getChannelData(0);
      
      // Create audio chunk
      const chunk: AudioChunk = {
        data: new Float32Array(audioData),
        sampleRate: audioContext!.sampleRate,
        timestamp: Date.now(),
        duration: audioData.length / audioContext!.sampleRate
      };
      
      // Send to background service worker
      sendMediaToBackground(chunk, 'audio');
    };
    
    source.connect(processor);
    processor.connect(audioContext.destination);
    
    console.log('Audio capture setup complete');
  } catch (error) {
    console.error('Failed to setup audio capture:', error);
  }
}

/**
 * Setup video capture
 */
function setupVideoCapture(stream: MediaStream): void {
  try {
    const videoTrack = stream.getVideoTracks()[0];
    const video = document.createElement('video');
    video.srcObject = new MediaStream([videoTrack]);
    video.play();
    
    // Capture frames at 1 FPS
    videoFrameInterval = window.setInterval(() => {
      captureVideoFrame(video);
    }, FRAME_CAPTURE_INTERVAL);
    
    console.log('Video capture setup complete');
  } catch (error) {
    console.error('Failed to setup video capture:', error);
  }
}

/**
 * Capture video frame
 */
function captureVideoFrame(video: HTMLVideoElement): void {
  try {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }
    
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Get image data
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    
    // Create video frame
    const frame: VideoFrame = {
      imageData,
      timestamp: Date.now(),
      width: canvas.width,
      height: canvas.height
    };
    
    // Send to background service worker
    sendMediaToBackground(frame, 'video');
  } catch (error) {
    console.error('Failed to capture video frame:', error);
  }
}

/**
 * Send media to background service worker
 */
function sendMediaToBackground(data: AudioChunk | VideoFrame, type: 'audio' | 'video'): void {
  // Convert to serializable format
  let payload: any;
  
  if (type === 'audio') {
    const audioChunk = data as AudioChunk;
    payload = {
      data: Array.from(audioChunk.data),
      sampleRate: audioChunk.sampleRate,
      timestamp: audioChunk.timestamp,
      duration: audioChunk.duration
    };
  } else {
    const videoFrame = data as VideoFrame;
    payload = {
      data: Array.from(videoFrame.imageData.data),
      width: videoFrame.width,
      height: videoFrame.height,
      timestamp: videoFrame.timestamp
    };
  }
  
  chrome.runtime.sendMessage({
    type: 'MEDIA_CAPTURED',
    payload: {
      ...payload,
      type,
      sessionId
    }
  });
}

/**
 * Stop monitoring
 */
function stopMonitoring(): void {
  if (!isMonitoring) {
    return;
  }
  
  console.log('Stopping monitoring');
  
  isMonitoring = false;
  
  // Cleanup audio
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
  
  // Cleanup video
  if (videoFrameInterval) {
    clearInterval(videoFrameInterval);
    videoFrameInterval = null;
  }
  
  // Notify background service worker
  chrome.runtime.sendMessage({
    type: 'SESSION_ENDED'
  });
  
  sessionId = null;
}

/**
 * Generate session ID
 */
function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Initialize
init();

// Export for testing
export {
  setupWebRTCInterception,
  startMonitoring,
  stopMonitoring,
  captureVideoFrame
};
