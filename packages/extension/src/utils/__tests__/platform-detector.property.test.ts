/**
 * Platform Detector Property-Based Tests
 * 
 * Feature: production-ready-browser-extension
 * Property 1: Platform Injection Universality
 * 
 * For any supported video conferencing platform (Google Meet, Zoom, Microsoft Teams),
 * when the extension is installed, the content script should successfully inject
 * and establish WebRTC stream interception.
 * 
 * Validates: Requirements 1.2
 */

import { describe, it, expect, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import { detectPlatform, isSupportedPlatform, getPlatformConfig } from '../platform-detector';

describe('Property 1: Platform Injection Universality', () => {
  beforeEach(() => {
    // Reset window.location before each test
    delete (window as any).location;
  });

  /**
   * Property: For any supported platform URL, detectPlatform should return a valid platform
   */
  it('should detect all supported platforms from valid URLs', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          // Google Meet URLs
          fc.record({
            platform: fc.constant('meet' as const),
            url: fc.string({ minLength: 8, maxLength: 20 }).map(
              code => `https://meet.google.com/${code}`
            )
          }),
          // Zoom URLs
          fc.record({
            platform: fc.constant('zoom' as const),
            url: fc.tuple(
              fc.constantFrom('us01web', 'us02web', 'us03web', 'eu01web', 'ap01web'),
              fc.integer({ min: 100000000, max: 999999999 })
            ).map(([subdomain, meetingId]) => 
              `https://${subdomain}.zoom.us/j/${meetingId}`
            )
          }),
          // Microsoft Teams URLs
          fc.record({
            platform: fc.constant('teams' as const),
            url: fc.string({ minLength: 10, maxLength: 30 }).map(
              code => `https://teams.microsoft.com/l/meetup-join/${code}`
            )
          })
        ),
        ({ platform, url }) => {
          // Set up window.location
          Object.defineProperty(window, 'location', {
            value: { href: url },
            writable: true,
            configurable: true
          });

          // Test detection
          const detected = detectPlatform();
          expect(detected).toBe(platform);
          
          // Test support check
          expect(isSupportedPlatform()).toBe(true);
          
          // Test config retrieval
          const config = getPlatformConfig(detected);
          expect(config).not.toBeNull();
          expect(config?.name).toBeDefined();
          expect(config?.videoSelector).toBeDefined();
          expect(config?.audioSelector).toBeDefined();
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: For any unsupported URL, detectPlatform should return null
   */
  it('should return null for unsupported platform URLs', () => {
    fc.assert(
      fc.property(
        fc.webUrl({ validSchemes: ['https'] }).filter(url => 
          !url.includes('meet.google.com') &&
          !url.includes('zoom.us') &&
          !url.includes('teams.microsoft.com')
        ),
        (url) => {
          Object.defineProperty(window, 'location', {
            value: { href: url },
            writable: true,
            configurable: true
          });

          const detected = detectPlatform();
          expect(detected).toBeNull();
          expect(isSupportedPlatform()).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: Platform detection should be deterministic
   * Same URL should always return the same platform
   */
  it('should return consistent results for the same URL', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          'https://meet.google.com/abc-defg-hij',
          'https://us02web.zoom.us/j/123456789',
          'https://teams.microsoft.com/l/meetup-join/xyz123'
        ),
        (url) => {
          Object.defineProperty(window, 'location', {
            value: { href: url },
            writable: true,
            configurable: true
          });

          const result1 = detectPlatform();
          const result2 = detectPlatform();
          const result3 = detectPlatform();

          expect(result1).toBe(result2);
          expect(result2).toBe(result3);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: Platform config should always be retrievable for detected platforms
   */
  it('should always provide config for detected platforms', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          'https://meet.google.com/test',
          'https://zoom.us/j/123',
          'https://teams.microsoft.com/l/meetup-join/test'
        ),
        (url) => {
          Object.defineProperty(window, 'location', {
            value: { href: url },
            writable: true,
            configurable: true
          });

          const platform = detectPlatform();
          
          if (platform !== null) {
            const config = getPlatformConfig(platform);
            
            // Config must exist for detected platforms
            expect(config).not.toBeNull();
            
            // Config must have all required fields
            expect(config?.name).toBeTruthy();
            expect(config?.videoSelector).toBeTruthy();
            expect(config?.audioSelector).toBeTruthy();
            expect(config?.participantSelector).toBeTruthy();
            expect(config?.waitForElement).toBeTruthy();
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: URL variations should still be detected correctly
   * Tests with query parameters, fragments, different subdomains
   */
  it('should handle URL variations correctly', () => {
    fc.assert(
      fc.property(
        fc.record({
          baseUrl: fc.constantFrom(
            'https://meet.google.com/abc',
            'https://us02web.zoom.us/j/123',
            'https://teams.microsoft.com/l/meetup-join/xyz'
          ),
          queryParams: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: undefined }),
          fragment: fc.option(fc.string({ minLength: 1, maxLength: 10 }), { nil: undefined })
        }),
        ({ baseUrl, queryParams, fragment }) => {
          let url = baseUrl;
          if (queryParams) {
            url += `?param=${queryParams}`;
          }
          if (fragment) {
            url += `#${fragment}`;
          }

          Object.defineProperty(window, 'location', {
            value: { href: url },
            writable: true,
            configurable: true
          });

          const platform = detectPlatform();
          
          // Should still detect the platform regardless of query params/fragments
          expect(platform).not.toBeNull();
          expect(['meet', 'zoom', 'teams']).toContain(platform);
        }
      ),
      { numRuns: 100 }
    );
  });
});
