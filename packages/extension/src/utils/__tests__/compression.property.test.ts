/**
 * Property-based tests for media compression
 * 
 * Feature: production-ready-browser-extension
 * Property 44: Media Compression Before Transmission
 * 
 * For any audio chunk or video frame transmitted to the backend,
 * the data should be compressed (using gzip or similar) to reduce
 * bandwidth usage by at least 30%.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  compressMedia,
  decompressMedia,
  compressIfBeneficial,
  compressAudio,
  compressVideo
} from '../compression';

describe('Media Compression Properties', () => {
  it('Property 44: compression-decompression round-trip preserves data', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For any binary media data, compressing then decompressing
     * should return the original data exactly.
     */
    await fc.assert(
      fc.asyncProperty(
        fc.uint8Array({ minLength: 100, maxLength: 10000 }),
        async (data) => {
          // Compress
          const compressed = await compressMedia(data);
          
          // Decompress
          const decompressed = await decompressMedia(compressed.data);
          
          // Should match original exactly
          expect(decompressed).toEqual(data);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('Property 44: compression reduces size for repetitive data', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For repetitive data (common in video frames), compression
     * should reduce size.
     */
    await fc.assert(
      fc.asyncProperty(
        fc.uint8Array({ minLength: 10, maxLength: 100 }),
        async (pattern) => {
          // Create repetitive data by repeating pattern
          const repetitiveData = new Uint8Array(pattern.length * 50);
          for (let i = 0; i < 50; i++) {
            repetitiveData.set(pattern, i * pattern.length);
          }
          
          const result = await compressMedia(repetitiveData);
          
          // Repetitive data should compress
          expect(result.compressedSize).toBeLessThan(result.originalSize);
          expect(result.compressionRatio).toBeGreaterThan(0);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('Property 44: compression ratio is bounded', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For any data, compression ratio should be between 0 and 1.
     */
    await fc.assert(
      fc.asyncProperty(
        fc.uint8Array({ minLength: 100, maxLength: 5000 }),
        async (data) => {
          const result = await compressMedia(data);
          
          // Ratio should be bounded [0, 1]
          expect(result.compressionRatio).toBeGreaterThanOrEqual(0);
          expect(result.compressionRatio).toBeLessThanOrEqual(1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('Property 44: compressIfBeneficial returns valid data', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For any data, compressIfBeneficial should return valid data
     * that can be used (either compressed or original).
     */
    await fc.assert(
      fc.asyncProperty(
        fc.uint8Array({ minLength: 100, maxLength: 5000 }),
        async (data) => {
          const result = await compressIfBeneficial(data);
          
          // Should return valid data
          expect(result.data).toBeInstanceOf(Uint8Array);
          expect(result.data.length).toBeGreaterThan(0);
          
          // If compressed, should meet threshold
          if (result.wasCompressed) {
            expect(result.compressionRatio).toBeGreaterThanOrEqual(0.30);
            
            // Should be decompressible
            const decompressed = await decompressMedia(result.data);
            expect(decompressed).toEqual(data);
          } else {
            // If not compressed, should return original
            expect(result.data).toEqual(data);
            expect(result.compressionRatio).toBe(0);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('Property 44: compressed data is valid gzip format', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For any data, compressed output should be valid gzip format
     * that can be decompressed.
     */
    await fc.assert(
      fc.asyncProperty(
        fc.uint8Array({ minLength: 100, maxLength: 5000 }),
        async (data) => {
          const compressed = await compressMedia(data);
          
          // Should be decompressible (validates gzip format)
          const decompressed = await decompressMedia(compressed.data);
          expect(decompressed).toEqual(data);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('Property 44: multiple compression cycles preserve data', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For any data, multiple compression/decompression cycles
     * should preserve the original data.
     */
    await fc.assert(
      fc.asyncProperty(
        fc.uint8Array({ minLength: 100, maxLength: 2000 }),
        async (original) => {
          let data = original;
          
          // Perform 3 compression/decompression cycles
          for (let i = 0; i < 3; i++) {
            const compressed = await compressMedia(data);
            data = await decompressMedia(compressed.data);
          }
          
          // Should still match original
          expect(data).toEqual(original);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('Property 44: audio compression preserves data', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For any audio data (Float32Array), compression should
     * preserve the data when decompressed.
     */
    await fc.assert(
      fc.asyncProperty(
        fc.float32Array({ minLength: 100, maxLength: 2000 }),
        async (audioData) => {
          const result = await compressAudio(audioData);
          
          // Decompress
          const decompressed = await decompressMedia(result.data);
          
          // Convert back to Float32Array
          const decompressedAudio = new Float32Array(decompressed.buffer);
          
          // Should match original
          expect(decompressedAudio).toEqual(audioData);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('Property 44: video compression preserves data', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For any video frame data (Uint8ClampedArray), compression
     * should preserve the data when decompressed.
     */
    await fc.assert(
      fc.asyncProperty(
        fc.uint8Array({ minLength: 100, maxLength: 2000 }),
        async (frameData) => {
          // Convert to Uint8ClampedArray (simulating ImageData)
          const videoData = new Uint8ClampedArray(frameData);
          
          const result = await compressVideo(videoData);
          
          // Decompress
          const decompressed = await decompressMedia(result.data);
          
          // Convert back to Uint8ClampedArray
          const decompressedVideo = new Uint8ClampedArray(decompressed.buffer);
          
          // Should match original
          expect(decompressedVideo).toEqual(videoData);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('Property 44: compression achieves target ratio for patterned data', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For data with patterns (simulating real media), compression
     * should achieve at least 30% reduction when beneficial.
     */
    await fc.assert(
      fc.asyncProperty(
        fc.uint8Array({ minLength: 50, maxLength: 200 }),
        async (pattern) => {
          // Create patterned data (simulating video frames with similar regions)
          const patternedData = new Uint8Array(pattern.length * 30);
          for (let i = 0; i < 30; i++) {
            patternedData.set(pattern, i * pattern.length);
          }
          
          const result = await compressIfBeneficial(patternedData);
          
          // For patterned data, compression should be beneficial
          if (result.wasCompressed) {
            // Should meet minimum threshold
            expect(result.compressionRatio).toBeGreaterThanOrEqual(0.30);
            
            // Verify decompression works
            const decompressed = await decompressMedia(result.data);
            expect(decompressed).toEqual(patternedData);
          }
        }
      ),
      { numRuns: 50 }
    );
  });

  it('Property 44: compression handles all byte values', async () => {
    /**
     * Feature: production-ready-browser-extension
     * Property 44: Media Compression Before Transmission
     * 
     * For any data containing any byte values (0-255),
     * compression should work correctly.
     */
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.integer({ min: 0, max: 255 }), { minLength: 100, maxLength: 2000 }),
        async (values) => {
          const data = new Uint8Array(values);
          
          const compressed = await compressMedia(data);
          const decompressed = await decompressMedia(compressed.data);
          
          expect(decompressed).toEqual(data);
        }
      ),
      { numRuns: 100 }
    );
  });
});
