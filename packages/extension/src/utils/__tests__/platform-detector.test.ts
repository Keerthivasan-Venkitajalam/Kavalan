/**
 * Platform Detector Tests
 * 
 * Unit tests for platform detection functionality.
 */

import { describe, it, expect } from 'vitest';
import { detectPlatform, isSupportedPlatform, getPlatformConfig } from '../platform-detector';

describe('Platform Detector', () => {
  describe('detectPlatform', () => {
    it('should detect Google Meet', () => {
      // Mock window.location
      Object.defineProperty(window, 'location', {
        value: { href: 'https://meet.google.com/abc-defg-hij' },
        writable: true
      });
      
      const platform = detectPlatform();
      expect(platform).toBe('meet');
    });
    
    it('should detect Zoom', () => {
      Object.defineProperty(window, 'location', {
        value: { href: 'https://us02web.zoom.us/j/123456789' },
        writable: true
      });
      
      const platform = detectPlatform();
      expect(platform).toBe('zoom');
    });
    
    it('should detect Microsoft Teams', () => {
      Object.defineProperty(window, 'location', {
        value: { href: 'https://teams.microsoft.com/l/meetup-join/123' },
        writable: true
      });
      
      const platform = detectPlatform();
      expect(platform).toBe('teams');
    });
    
    it('should return null for unsupported platforms', () => {
      Object.defineProperty(window, 'location', {
        value: { href: 'https://example.com' },
        writable: true
      });
      
      const platform = detectPlatform();
      expect(platform).toBeNull();
    });
  });
  
  describe('isSupportedPlatform', () => {
    it('should return true for supported platforms', () => {
      Object.defineProperty(window, 'location', {
        value: { href: 'https://meet.google.com/abc-defg-hij' },
        writable: true
      });
      
      expect(isSupportedPlatform()).toBe(true);
    });
    
    it('should return false for unsupported platforms', () => {
      Object.defineProperty(window, 'location', {
        value: { href: 'https://example.com' },
        writable: true
      });
      
      expect(isSupportedPlatform()).toBe(false);
    });
  });
  
  describe('getPlatformConfig', () => {
    it('should return config for Google Meet', () => {
      const config = getPlatformConfig('meet');
      
      expect(config).not.toBeNull();
      expect(config?.name).toBe('Google Meet');
      expect(config?.videoSelector).toBeDefined();
      expect(config?.audioSelector).toBeDefined();
    });
    
    it('should return config for Zoom', () => {
      const config = getPlatformConfig('zoom');
      
      expect(config).not.toBeNull();
      expect(config?.name).toBe('Zoom');
    });
    
    it('should return config for Microsoft Teams', () => {
      const config = getPlatformConfig('teams');
      
      expect(config).not.toBeNull();
      expect(config?.name).toBe('Microsoft Teams');
    });
    
    it('should return null for unsupported platform', () => {
      const config = getPlatformConfig(null);
      expect(config).toBeNull();
    });
  });
});
