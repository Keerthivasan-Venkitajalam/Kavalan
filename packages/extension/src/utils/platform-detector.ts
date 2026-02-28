/**
 * Platform Detector
 * 
 * Detects the active video conferencing platform from URL patterns.
 */

import { Platform } from '../types';

// Platform URL patterns
const PLATFORM_PATTERNS: Record<string, RegExp> = {
  meet: /^https:\/\/meet\.google\.com\//,
  zoom: /^https:\/\/.*\.zoom\.us\//,
  teams: /^https:\/\/teams\.microsoft\.com\//
};

/**
 * Detect platform from current URL
 */
export function detectPlatform(): Platform {
  const url = window.location.href;
  
  for (const [platform, pattern] of Object.entries(PLATFORM_PATTERNS)) {
    if (pattern.test(url)) {
      return platform as Platform;
    }
  }
  
  return null;
}

/**
 * Check if current page is a supported platform
 */
export function isSupportedPlatform(): boolean {
  return detectPlatform() !== null;
}

/**
 * Get platform-specific configuration
 */
export function getPlatformConfig(platform: Platform): PlatformConfig | null {
  if (!platform) {
    return null;
  }
  
  const configs: Record<string, PlatformConfig> = {
    meet: {
      name: 'Google Meet',
      videoSelector: 'video[autoplay]',
      audioSelector: 'audio',
      participantSelector: '[data-participant-id]',
      waitForElement: 'div[data-meeting-title]'
    },
    zoom: {
      name: 'Zoom',
      videoSelector: 'video.video-element',
      audioSelector: 'audio',
      participantSelector: '.participants-item',
      waitForElement: '.meeting-info-container'
    },
    teams: {
      name: 'Microsoft Teams',
      videoSelector: 'video[class*="video"]',
      audioSelector: 'audio',
      participantSelector: '[data-tid="roster-item"]',
      waitForElement: '[data-tid="meeting-canvas"]'
    }
  };
  
  return configs[platform] || null;
}

/**
 * Wait for platform to be ready
 */
export async function waitForPlatformReady(platform: Platform): Promise<boolean> {
  const config = getPlatformConfig(platform);
  
  if (!config) {
    return false;
  }
  
  return new Promise((resolve) => {
    const checkElement = () => {
      const element = document.querySelector(config.waitForElement);
      
      if (element) {
        resolve(true);
      } else {
        setTimeout(checkElement, 500);
      }
    };
    
    checkElement();
    
    // Timeout after 30 seconds
    setTimeout(() => resolve(false), 30000);
  });
}

// Platform configuration interface
export interface PlatformConfig {
  name: string;
  videoSelector: string;
  audioSelector: string;
  participantSelector: string;
  waitForElement: string;
}
