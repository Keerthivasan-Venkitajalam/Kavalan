/**
 * Encryption Property-Based Tests
 * 
 * Feature: production-ready-browser-extension
 * Property 6: Media Encryption Before Transmission
 * 
 * For any captured audio chunk or video frame, the data must be encrypted
 * using AES-256-GCM before being transmitted to the backend API.
 * 
 * Validates: Requirements 2.6, 7.1
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as fc from 'fast-check';
import { encryptMedia, decryptMedia, clearEncryptionKey } from '../encryption';

// Mock chrome.storage API
const mockStorage = new Map<string, any>();

beforeEach(async () => {
  // Clear storage before each test
  mockStorage.clear();
  
  // Mock chrome.storage.local
  global.chrome = {
    storage: {
      local: {
        get: vi.fn((keys: string[] | string) => {
          const result: any = {};
          const keyArray = Array.isArray(keys) ? keys : [keys];
          
          keyArray.forEach(key => {
            if (mockStorage.has(key)) {
              result[key] = mockStorage.get(key);
            }
          });
          
          return Promise.resolve(result);
        }),
        set: vi.fn((items: any) => {
          Object.keys(items).forEach(key => {
            mockStorage.set(key, items[key]);
          });
          return Promise.resolve();
        }),
        remove: vi.fn((keys: string | string[]) => {
          const keyArray = Array.isArray(keys) ? keys : [keys];
          keyArray.forEach(key => mockStorage.delete(key));
          return Promise.resolve();
        })
      }
    }
  } as any;
  
  // Clear encryption key before each test
  await clearEncryptionKey();
});

describe('Property 6: Media Encryption Before Transmission', () => {
  /**
   * Property: For any audio data, encryption followed by decryption should return the original data
   * This validates the encryption round-trip works correctly
   */
  it('should correctly encrypt and decrypt audio data (round-trip)', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          // Generate random audio data
          data: fc.array(fc.float({ min: Math.fround(-1.0), max: Math.fround(1.0) }), { minLength: 100, maxLength: 4096 }),
          sampleRate: fc.constantFrom(8000, 16000, 44100, 48000),
          timestamp: fc.integer({ min: 1000000000000, max: 9999999999999 }),
          duration: fc.float({ min: Math.fround(0.1), max: Math.fround(5.0) })
        }),
        async (audioChunk) => {
          // Store session ID
          mockStorage.set('sessionId', 'test-session-123');
          
          // Encrypt audio data
          const encrypted = await encryptMedia(audioChunk, 'audio');
          
          // Validate encrypted payload structure
          expect(encrypted).toHaveProperty('data');
          expect(encrypted).toHaveProperty('iv');
          expect(encrypted).toHaveProperty('timestamp');
          expect(encrypted).toHaveProperty('sessionId');
          expect(encrypted).toHaveProperty('type');
          
          expect(encrypted.type).toBe('audio');
          expect(encrypted.sessionId).toBe('test-session-123');
          expect(encrypted.iv).toBeInstanceOf(Uint8Array);
          expect(encrypted.iv.length).toBe(12); // GCM IV is 96 bits = 12 bytes
          
          // Check encrypted data is ArrayBuffer-like (handles Node.js webcrypto differences)
          expect(encrypted.data).toBeDefined();
          expect(encrypted.data.byteLength).toBeGreaterThan(0);
          expect(typeof encrypted.data.byteLength).toBe('number');
          
          // Encrypted data should be different from original
          const originalBuffer = new Float32Array(audioChunk.data).buffer;
          const encryptedBytes = new Uint8Array(encrypted.data);
          const originalBytes = new Uint8Array(originalBuffer);
          expect(encryptedBytes).not.toEqual(originalBytes);
          
          // Decrypt the data
          const decrypted = await decryptMedia(encrypted.data, encrypted.iv);
          
          // Convert decrypted buffer back to Float32Array
          const decryptedArray = new Float32Array(decrypted);
          
          // Validate round-trip: decrypted data should match original
          expect(decryptedArray.length).toBe(audioChunk.data.length);
          
          // Compare values with small tolerance for floating point precision
          // Handle NaN values specially (NaN !== NaN in JavaScript)
          for (let i = 0; i < audioChunk.data.length; i++) {
            const original = audioChunk.data[i];
            const decrypted = decryptedArray[i];
            
            // Both NaN or both equal within tolerance
            if (Number.isNaN(original) && Number.isNaN(decrypted)) {
              continue; // Both NaN, this is correct
            } else if (Number.isNaN(original) || Number.isNaN(decrypted)) {
              throw new Error(`NaN mismatch at index ${i}: original=${original}, decrypted=${decrypted}`);
            } else {
              expect(Math.abs(decrypted - original)).toBeLessThan(0.0001);
            }
          }
        }
      ),
      { numRuns: 50 } // Reduced runs for crypto operations
    );
  });

  /**
   * Property: For any video frame data, encryption followed by decryption should return the original data
   */
  it('should correctly encrypt and decrypt video frame data (round-trip)', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          // Generate random video frame data (RGBA pixels)
          data: fc.array(fc.integer({ min: 0, max: 255 }), { minLength: 400, maxLength: 1024 }),
          width: fc.integer({ min: 10, max: 32 }),
          height: fc.integer({ min: 10, max: 32 }),
          timestamp: fc.integer({ min: 1000000000000, max: 9999999999999 })
        }),
        async (videoFrame) => {
          // Store session ID
          mockStorage.set('sessionId', 'test-session-456');
          
          // Encrypt video data
          const encrypted = await encryptMedia(videoFrame, 'video');
          
          // Validate encrypted payload structure
          expect(encrypted).toHaveProperty('data');
          expect(encrypted).toHaveProperty('iv');
          expect(encrypted).toHaveProperty('timestamp');
          expect(encrypted).toHaveProperty('sessionId');
          expect(encrypted).toHaveProperty('type');
          
          expect(encrypted.type).toBe('video');
          expect(encrypted.sessionId).toBe('test-session-456');
          expect(encrypted.iv).toBeInstanceOf(Uint8Array);
          expect(encrypted.iv.length).toBe(12);
          
          // Check encrypted data is ArrayBuffer-like (handles Node.js webcrypto differences)
          expect(encrypted.data).toBeDefined();
          expect(encrypted.data.byteLength).toBeGreaterThan(0);
          expect(typeof encrypted.data.byteLength).toBe('number');
          
          // Encrypted data should be different from original
          const originalBuffer = new Uint8ClampedArray(videoFrame.data).buffer;
          const encryptedBytes = new Uint8Array(encrypted.data);
          const originalBytes = new Uint8Array(originalBuffer);
          expect(encryptedBytes).not.toEqual(originalBytes);
          
          // Decrypt the data
          const decrypted = await decryptMedia(encrypted.data, encrypted.iv);
          
          // Convert decrypted buffer back to Uint8ClampedArray
          const decryptedArray = new Uint8ClampedArray(decrypted);
          
          // Validate round-trip: decrypted data should match original
          expect(decryptedArray.length).toBe(videoFrame.data.length);
          
          for (let i = 0; i < videoFrame.data.length; i++) {
            expect(decryptedArray[i]).toBe(videoFrame.data[i]);
          }
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Property: Each encryption should produce a unique IV (Initialization Vector)
   * IVs must never be reused with the same key for security
   */
  it('should generate unique IVs for each encryption', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.float({ min: Math.fround(-1.0), max: Math.fround(1.0) }), { minLength: 100, maxLength: 1000 }),
        async (audioData) => {
          mockStorage.set('sessionId', 'test-session');
          
          const audioChunk = { data: audioData };
          
          // Encrypt the same data multiple times
          const encrypted1 = await encryptMedia(audioChunk, 'audio');
          const encrypted2 = await encryptMedia(audioChunk, 'audio');
          const encrypted3 = await encryptMedia(audioChunk, 'audio');
          
          // IVs should all be different (compare as byte arrays)
          const iv1Bytes = Array.from(encrypted1.iv);
          const iv2Bytes = Array.from(encrypted2.iv);
          const iv3Bytes = Array.from(encrypted3.iv);
          
          // Check IVs are not identical
          const iv1Equals2 = iv1Bytes.every((byte, i) => byte === iv2Bytes[i]);
          const iv2Equals3 = iv2Bytes.every((byte, i) => byte === iv3Bytes[i]);
          const iv1Equals3 = iv1Bytes.every((byte, i) => byte === iv3Bytes[i]);
          
          expect(iv1Equals2).toBe(false);
          expect(iv2Equals3).toBe(false);
          expect(iv1Equals3).toBe(false);
          
          // Encrypted data should also be different due to different IVs
          const enc1Bytes = new Uint8Array(encrypted1.data);
          const enc2Bytes = new Uint8Array(encrypted2.data);
          const enc3Bytes = new Uint8Array(encrypted3.data);
          
          const enc1Equals2 = enc1Bytes.every((byte, i) => byte === enc2Bytes[i]);
          const enc2Equals3 = enc2Bytes.every((byte, i) => byte === enc3Bytes[i]);
          
          expect(enc1Equals2).toBe(false);
          expect(enc2Equals3).toBe(false);
        }
      ),
      { numRuns: 30 }
    );
  });

  /**
   * Property: Encryption key should be persistent across multiple operations
   * The same key should be reused for all encryptions in a session
   */
  it('should reuse the same encryption key across operations', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.tuple(
          fc.array(fc.float({ min: Math.fround(-1.0), max: Math.fround(1.0) }), { minLength: 100, maxLength: 500 }),
          fc.array(fc.float({ min: Math.fround(-1.0), max: Math.fround(1.0) }), { minLength: 100, maxLength: 500 })
        ),
        async ([audioData1, audioData2]) => {
          mockStorage.set('sessionId', 'test-session');
          
          // First encryption
          const encrypted1 = await encryptMedia({ data: audioData1 }, 'audio');
          
          // Check that key was stored
          const storedKey1 = mockStorage.get('encryptionKey');
          expect(storedKey1).toBeDefined();
          
          // Second encryption
          const encrypted2 = await encryptMedia({ data: audioData2 }, 'audio');
          
          // Key should still be the same
          const storedKey2 = mockStorage.get('encryptionKey');
          expect(storedKey2).toEqual(storedKey1);
          
          // Both encryptions should be decryptable with the same key
          const decrypted1 = await decryptMedia(encrypted1.data, encrypted1.iv);
          const decrypted2 = await decryptMedia(encrypted2.data, encrypted2.iv);
          
          expect(new Float32Array(decrypted1).length).toBe(audioData1.length);
          expect(new Float32Array(decrypted2).length).toBe(audioData2.length);
        }
      ),
      { numRuns: 30 }
    );
  });

  /**
   * Property: Encrypted data size should be reasonable
   * AES-GCM adds authentication tag (16 bytes) but shouldn't significantly increase size
   */
  it('should produce encrypted data with reasonable size overhead', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.float({ min: Math.fround(-1.0), max: Math.fround(1.0) }), { minLength: 100, maxLength: 2000 }),
        async (audioData) => {
          mockStorage.set('sessionId', 'test-session');
          
          const audioChunk = { data: audioData };
          const encrypted = await encryptMedia(audioChunk, 'audio');
          
          const originalSize = audioData.length * 4; // Float32 = 4 bytes per element
          const encryptedSize = encrypted.data.byteLength;
          
          // GCM adds 16-byte authentication tag
          // Encrypted size should be original size + 16 bytes (or slightly more due to padding)
          expect(encryptedSize).toBeGreaterThanOrEqual(originalSize);
          expect(encryptedSize).toBeLessThanOrEqual(originalSize + 32); // Allow some padding
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Property: Tampering with encrypted data should cause decryption to fail
   * This validates the authentication aspect of AES-GCM
   */
  it('should detect tampering with encrypted data', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.float({ min: Math.fround(-1.0), max: Math.fround(1.0) }), { minLength: 100, maxLength: 500 }),
        async (audioData) => {
          mockStorage.set('sessionId', 'test-session');
          
          const audioChunk = { data: audioData };
          const encrypted = await encryptMedia(audioChunk, 'audio');
          
          // Tamper with encrypted data by flipping a bit
          const tamperedData = new Uint8Array(encrypted.data);
          if (tamperedData.length > 0) {
            tamperedData[0] ^= 1; // Flip one bit
          }
          
          // Decryption should fail
          await expect(
            decryptMedia(tamperedData.buffer, encrypted.iv)
          ).rejects.toThrow();
        }
      ),
      { numRuns: 30 }
    );
  });

  /**
   * Property: Tampering with IV should cause decryption to fail or return wrong data
   */
  it('should detect tampering with IV', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.float({ min: Math.fround(-1.0), max: Math.fround(1.0) }), { minLength: 100, maxLength: 500 }),
        async (audioData) => {
          mockStorage.set('sessionId', 'test-session');
          
          const audioChunk = { data: audioData };
          const encrypted = await encryptMedia(audioChunk, 'audio');
          
          // Tamper with IV
          const tamperedIV = new Uint8Array(encrypted.iv);
          tamperedIV[0] ^= 1; // Flip one bit
          
          // Decryption should fail or return incorrect data
          try {
            const decrypted = await decryptMedia(encrypted.data, tamperedIV);
            const decryptedArray = new Float32Array(decrypted);
            
            // If it doesn't throw, the data should be corrupted
            let hasCorruption = false;
            for (let i = 0; i < Math.min(audioData.length, decryptedArray.length); i++) {
              if (Math.abs(decryptedArray[i] - audioData[i]) > 0.01) {
                hasCorruption = true;
                break;
              }
            }
            
            expect(hasCorruption).toBe(true);
          } catch (error) {
            // Expected: decryption should fail
            expect(error).toBeDefined();
          }
        }
      ),
      { numRuns: 30 }
    );
  });

  /**
   * Property: Encryption should preserve metadata (timestamp, sessionId, type)
   */
  it('should preserve metadata in encrypted payload', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          data: fc.array(fc.float({ min: Math.fround(-1.0), max: Math.fround(1.0) }), { minLength: 100, maxLength: 500 }),
          sessionId: fc.string({ minLength: 10, maxLength: 50 }),
          type: fc.constantFrom('audio' as const, 'video' as const)
        }),
        async ({ data, sessionId, type }) => {
          mockStorage.set('sessionId', sessionId);
          
          const chunk = { data };
          const encrypted = await encryptMedia(chunk, type);
          
          // Metadata should be preserved
          expect(encrypted.sessionId).toBe(sessionId);
          expect(encrypted.type).toBe(type);
          expect(encrypted.timestamp).toBeGreaterThan(0);
          expect(encrypted.timestamp).toBeLessThanOrEqual(Date.now());
        }
      ),
      { numRuns: 50 }
    );
  });
});
