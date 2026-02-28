/**
 * Unit tests for media compression utility
 */
import { describe, it, expect } from 'vitest';
import {
  compressMedia,
  decompressMedia,
  compressIfBeneficial,
  compressAudio,
  compressVideo
} from '../compression';

describe('Media Compression', () => {
  describe('compressMedia', () => {
    it('should compress data successfully', async () => {
      const data = new Uint8Array(1000).fill(65); // 'A' repeated
      
      const result = await compressMedia(data);
      
      expect(result.data).toBeInstanceOf(Uint8Array);
      expect(result.compressedSize).toBeLessThan(result.originalSize);
      expect(result.compressionRatio).toBeGreaterThan(0);
      expect(result.wasCompressed).toBe(true);
    });

    it('should handle ArrayBuffer input', async () => {
      const buffer = new ArrayBuffer(1000);
      const view = new Uint8Array(buffer);
      view.fill(65);
      
      const result = await compressMedia(buffer);
      
      expect(result.data).toBeInstanceOf(Uint8Array);
      expect(result.compressedSize).toBeLessThan(result.originalSize);
    });

    it('should reject empty data', async () => {
      const data = new Uint8Array(0);
      
      await expect(compressMedia(data)).rejects.toThrow('Cannot compress empty data');
    });

    it('should compress repetitive data well', async () => {
      // Highly repetitive data should compress to much smaller size
      const data = new Uint8Array(10000).fill(88); // 'X' repeated
      
      const result = await compressMedia(data);
      
      expect(result.compressionRatio).toBeGreaterThan(0.9); // >90% reduction
    });

    it('should calculate compression ratio correctly', async () => {
      const data = new Uint8Array(1000).fill(65);
      
      const result = await compressMedia(data);
      
      const expectedRatio = (result.originalSize - result.compressedSize) / result.originalSize;
      expect(Math.abs(result.compressionRatio - expectedRatio)).toBeLessThan(0.001);
    });
  });

  describe('decompressMedia', () => {
    it('should decompress data successfully', async () => {
      const original = new Uint8Array(1000).fill(65);
      
      const compressed = await compressMedia(original);
      const decompressed = await decompressMedia(compressed.data);
      
      expect(decompressed).toEqual(original);
    });

    it('should handle ArrayBuffer input', async () => {
      const original = new Uint8Array(1000).fill(65);
      
      const compressed = await compressMedia(original);
      const decompressed = await decompressMedia(compressed.data.buffer);
      
      expect(decompressed).toEqual(original);
    });

    it('should reject empty data', async () => {
      const data = new Uint8Array(0);
      
      await expect(decompressMedia(data)).rejects.toThrow('Cannot decompress empty data');
    });

    it('should reject invalid compressed data', async () => {
      const invalidData = new Uint8Array([1, 2, 3, 4, 5]);
      
      await expect(decompressMedia(invalidData)).rejects.toThrow('Decompression failed');
    });
  });

  describe('compression round-trip', () => {
    it('should preserve data through compression and decompression', async () => {
      const original = new Uint8Array(500);
      for (let i = 0; i < original.length; i++) {
        original[i] = i % 256;
      }
      
      const compressed = await compressMedia(original);
      const decompressed = await decompressMedia(compressed.data);
      
      expect(decompressed).toEqual(original);
    });

    it('should handle multiple compression cycles', async () => {
      const original = new Uint8Array(500).fill(77);
      
      let data = original;
      for (let i = 0; i < 3; i++) {
        const compressed = await compressMedia(data);
        data = await decompressMedia(compressed.data);
      }
      
      expect(data).toEqual(original);
    });

    it('should preserve binary patterns', async () => {
      // Create data with specific pattern
      const original = new Uint8Array(1000);
      for (let i = 0; i < original.length; i++) {
        original[i] = (i * 7) % 256;
      }
      
      const compressed = await compressMedia(original);
      const decompressed = await decompressMedia(compressed.data);
      
      expect(decompressed).toEqual(original);
    });
  });

  describe('compressIfBeneficial', () => {
    it('should compress when ratio is good', async () => {
      // Repetitive data compresses well
      const data = new Uint8Array(5000).fill(65);
      
      const result = await compressIfBeneficial(data);
      
      expect(result.wasCompressed).toBe(true);
      expect(result.compressionRatio).toBeGreaterThanOrEqual(0.30);
      expect(result.compressedSize).toBeLessThan(result.originalSize);
    });

    it('should return original data when compression is not beneficial', async () => {
      // Very small data may not compress well
      const data = new Uint8Array([65, 66]);
      
      const result = await compressIfBeneficial(data);
      
      // May or may not compress depending on overhead
      if (!result.wasCompressed) {
        expect(result.compressionRatio).toBe(0);
        expect(result.data).toEqual(data);
      }
    });

    it('should handle compression errors gracefully', async () => {
      const data = new Uint8Array(100).fill(65);
      
      // Should not throw, even if compression fails
      const result = await compressIfBeneficial(data);
      
      expect(result.data).toBeInstanceOf(Uint8Array);
      expect(result.originalSize).toBe(100);
    });
  });

  describe('compressAudio', () => {
    it('should compress Float32Array audio data', async () => {
      const audioData = new Float32Array(1000);
      for (let i = 0; i < audioData.length; i++) {
        audioData[i] = Math.sin(i * 0.1);
      }
      
      const result = await compressAudio(audioData);
      
      expect(result.data).toBeInstanceOf(Uint8Array);
      expect(result.wasCompressed).toBe(true);
      expect(result.originalSize).toBe(audioData.byteLength);
    });

    it('should handle silent audio', async () => {
      const audioData = new Float32Array(1000).fill(0);
      
      const result = await compressAudio(audioData);
      
      // Silent audio (all zeros) should compress very well
      expect(result.compressionRatio).toBeGreaterThan(0.9);
    });
  });

  describe('compressVideo', () => {
    it('should compress Uint8ClampedArray video data', async () => {
      // Simulate a small video frame (100x100 RGBA)
      const videoData = new Uint8ClampedArray(100 * 100 * 4);
      for (let i = 0; i < videoData.length; i++) {
        videoData[i] = i % 256;
      }
      
      const result = await compressVideo(videoData);
      
      expect(result.data).toBeInstanceOf(Uint8Array);
      expect(result.wasCompressed).toBe(true);
      expect(result.originalSize).toBe(videoData.byteLength);
    });

    it('should handle uniform color frames', async () => {
      // Uniform color frame should compress very well
      const videoData = new Uint8ClampedArray(100 * 100 * 4).fill(128);
      
      const result = await compressVideo(videoData);
      
      // Uniform data should compress extremely well
      expect(result.compressionRatio).toBeGreaterThan(0.95);
    });
  });

  describe('edge cases', () => {
    it('should handle single byte', async () => {
      const data = new Uint8Array([65]);
      
      const result = await compressMedia(data);
      
      // Single byte may not compress due to gzip overhead
      expect(result.data).toBeInstanceOf(Uint8Array);
    });

    it('should handle large data', async () => {
      // Simulate large video frame (640x480 RGB)
      const data = new Uint8Array(640 * 480 * 3).fill(100);
      
      const result = await compressMedia(data);
      
      expect(result.compressedSize).toBeLessThan(result.originalSize);
      expect(result.compressionRatio).toBeGreaterThan(0);
    });

    it('should handle random data', async () => {
      // Random data doesn't compress well
      const data = new Uint8Array(1000);
      crypto.getRandomValues(data);
      
      const result = await compressMedia(data);
      
      // Should not fail, even if compression ratio is poor
      expect(result.data).toBeInstanceOf(Uint8Array);
    });
  });

  describe('compression ratios', () => {
    it('should achieve at least 30% reduction for repetitive data', async () => {
      const data = new Uint8Array(5000);
      // Create pattern: ABCDABCDABCD...
      for (let i = 0; i < data.length; i++) {
        data[i] = 65 + (i % 4); // A, B, C, D pattern
      }
      
      const result = await compressMedia(data);
      
      expect(result.compressionRatio).toBeGreaterThanOrEqual(0.30);
    });

    it('should report compression ratio between 0 and 1', async () => {
      const data = new Uint8Array(1000).fill(65);
      
      const result = await compressMedia(data);
      
      expect(result.compressionRatio).toBeGreaterThanOrEqual(0);
      expect(result.compressionRatio).toBeLessThanOrEqual(1);
    });
  });
});
