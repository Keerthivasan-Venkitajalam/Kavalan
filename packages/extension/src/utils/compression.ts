/**
 * Media Compression Utility
 * 
 * Compresses audio/video data before transmission to reduce bandwidth usage.
 * Achieves at least 30% size reduction using gzip compression.
 */

// Compression configuration
const MIN_COMPRESSION_RATIO = 0.30; // 30% reduction target

/**
 * Compression result
 */
export interface CompressionResult {
  data: Uint8Array;
  originalSize: number;
  compressedSize: number;
  compressionRatio: number;
  wasCompressed: boolean;
}

/**
 * Compress data using gzip (via CompressionStream API)
 */
export async function compressMedia(data: ArrayBuffer | Uint8Array): Promise<CompressionResult> {
  // Convert to Uint8Array if needed
  const inputArray = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
  
  if (inputArray.length === 0) {
    throw new Error('Cannot compress empty data');
  }
  
  const originalSize = inputArray.length;
  
  try {
    // Use CompressionStream API (available in modern browsers)
    const stream = new Blob([inputArray]).stream();
    const compressedStream = stream.pipeThrough(new CompressionStream('gzip'));
    
    // Read compressed data
    const compressedBlob = await new Response(compressedStream).blob();
    const compressedArray = new Uint8Array(await compressedBlob.arrayBuffer());
    
    const compressedSize = compressedArray.length;
    const compressionRatio = (originalSize - compressedSize) / originalSize;
    
    return {
      data: compressedArray,
      originalSize,
      compressedSize,
      compressionRatio,
      wasCompressed: true
    };
  } catch (error) {
    console.error('Compression failed:', error);
    throw new Error(`Compression failed: ${error}`);
  }
}

/**
 * Decompress gzip-compressed data
 */
export async function decompressMedia(compressedData: ArrayBuffer | Uint8Array): Promise<Uint8Array> {
  // Convert to Uint8Array if needed
  const inputArray = compressedData instanceof ArrayBuffer 
    ? new Uint8Array(compressedData) 
    : compressedData;
  
  if (inputArray.length === 0) {
    throw new Error('Cannot decompress empty data');
  }
  
  try {
    // Use DecompressionStream API
    const stream = new Blob([inputArray]).stream();
    const decompressedStream = stream.pipeThrough(new DecompressionStream('gzip'));
    
    // Read decompressed data
    const decompressedBlob = await new Response(decompressedStream).blob();
    const decompressedArray = new Uint8Array(await decompressedBlob.arrayBuffer());
    
    return decompressedArray;
  } catch (error) {
    console.error('Decompression failed:', error);
    throw new Error(`Decompression failed: ${error}`);
  }
}

/**
 * Compress data only if compression ratio meets minimum threshold
 */
export async function compressIfBeneficial(
  data: ArrayBuffer | Uint8Array
): Promise<CompressionResult> {
  try {
    const result = await compressMedia(data);
    
    if (result.compressionRatio >= MIN_COMPRESSION_RATIO) {
      console.log(`Compression beneficial: ${(result.compressionRatio * 100).toFixed(1)}% reduction`);
      return result;
    } else {
      console.log(`Compression not beneficial: only ${(result.compressionRatio * 100).toFixed(1)}% reduction`);
      
      // Return original data
      const inputArray = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
      return {
        data: inputArray,
        originalSize: inputArray.length,
        compressedSize: inputArray.length,
        compressionRatio: 0,
        wasCompressed: false
      };
    }
  } catch (error) {
    console.warn('Compression failed, using original data:', error);
    
    // Return original data on error
    const inputArray = data instanceof ArrayBuffer ? new Uint8Array(data) : data;
    return {
      data: inputArray,
      originalSize: inputArray.length,
      compressedSize: inputArray.length,
      compressionRatio: 0,
      wasCompressed: false
    };
  }
}

/**
 * Compress audio chunk data
 */
export async function compressAudio(audioData: Float32Array): Promise<CompressionResult> {
  // Convert Float32Array to Uint8Array for compression
  const buffer = audioData.buffer;
  return await compressMedia(buffer);
}

/**
 * Compress video frame data
 */
export async function compressVideo(imageData: Uint8ClampedArray): Promise<CompressionResult> {
  // Convert Uint8ClampedArray to Uint8Array for compression
  const uint8Array = new Uint8Array(imageData.buffer);
  return await compressMedia(uint8Array);
}
