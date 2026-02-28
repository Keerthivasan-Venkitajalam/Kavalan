/**
 * Encryption Utility
 * 
 * Provides AES-256-GCM encryption for media data using Web Crypto API.
 */

import { EncryptedPayload } from '../types';

// Encryption algorithm configuration
const ALGORITHM = 'AES-GCM';
const KEY_LENGTH = 256;
const IV_LENGTH = 12; // 96 bits for GCM

/**
 * Generate encryption key
 */
async function generateKey(): Promise<CryptoKey> {
  return await crypto.subtle.generateKey(
    {
      name: ALGORITHM,
      length: KEY_LENGTH
    },
    true, // extractable
    ['encrypt', 'decrypt']
  );
}

/**
 * Get or create encryption key from storage
 */
async function getEncryptionKey(): Promise<CryptoKey> {
  // Try to load existing key from storage
  const result = await chrome.storage.local.get(['encryptionKey']);
  
  if (result.encryptionKey) {
    // Import key from stored JWK
    return await crypto.subtle.importKey(
      'jwk',
      result.encryptionKey,
      { name: ALGORITHM, length: KEY_LENGTH },
      true,
      ['encrypt', 'decrypt']
    );
  }
  
  // Generate new key
  const key = await generateKey();
  
  // Export and store key
  const jwk = await crypto.subtle.exportKey('jwk', key);
  await chrome.storage.local.set({ encryptionKey: jwk });
  
  return key;
}

/**
 * Encrypt media data
 */
export async function encryptMedia(
  data: any,
  type: 'audio' | 'video'
): Promise<EncryptedPayload> {
  // Get encryption key
  const key = await getEncryptionKey();
  
  // Generate random IV
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
  
  // Convert data to TypedArray (Web Crypto API accepts TypedArray directly)
  let typedArray: Float32Array | Uint8ClampedArray;
  
  if (type === 'audio') {
    // Audio data is Float32Array or array
    const sourceArray = Array.isArray(data.data) ? data.data : Array.from(data.data);
    typedArray = new Float32Array(sourceArray);
  } else {
    // Video data is Uint8ClampedArray or array
    const sourceArray = Array.isArray(data.data) ? data.data : Array.from(data.data);
    typedArray = new Uint8ClampedArray(sourceArray);
  }
  
  // Handle empty data edge case
  if (typedArray.length === 0) {
    throw new Error('Cannot encrypt empty data');
  }
  
  // Encrypt data (Web Crypto API accepts TypedArray as BufferSource)
  const encrypted = await crypto.subtle.encrypt(
    {
      name: ALGORITHM,
      iv: iv
    },
    key,
    typedArray
  );
  
  // Ensure we have a valid ArrayBuffer
  if (!encrypted || encrypted.byteLength === 0) {
    throw new Error('Encryption failed: empty result');
  }
  
  // Get session ID from storage
  const settings = await chrome.storage.local.get(['sessionId']);
  
  // Create a proper Uint8Array from the iv buffer
  const ivArray = new Uint8Array(iv.buffer, iv.byteOffset, iv.byteLength);
  
  return {
    data: encrypted,
    iv: ivArray,
    timestamp: Date.now(),
    sessionId: settings.sessionId || '',
    type
  };
}

/**
 * Decrypt media data (for testing)
 */
export async function decryptMedia(
  encrypted: ArrayBuffer,
  iv: Uint8Array
): Promise<ArrayBuffer> {
  const key = await getEncryptionKey();
  
  const decrypted = await crypto.subtle.decrypt(
    {
      name: ALGORITHM,
      iv: iv as BufferSource
    },
    key,
    encrypted
  );
  
  return decrypted;
}

/**
 * Clear encryption key (for logout/reset)
 */
export async function clearEncryptionKey(): Promise<void> {
  await chrome.storage.local.remove(['encryptionKey']);
}
