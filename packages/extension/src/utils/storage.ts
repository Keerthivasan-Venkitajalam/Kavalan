/**
 * Storage Utility
 * 
 * Manages user preferences and settings using Chrome Storage API.
 * Provides type-safe access to extension storage with persistence across browser sessions.
 */

import { UserPreferences, ExtensionSettings } from '../types';

/**
 * Default user preferences
 */
const DEFAULT_PREFERENCES: UserPreferences = {
  language: 'en',
  alertVolume: 0.8,
  stealthMode: false,
  autoReport: false,
};

/**
 * Storage keys
 */
const STORAGE_KEYS = {
  PREFERENCES: 'preferences',
  SETTINGS: 'settings',
  ALERTS: 'alerts',
  TRANSCRIPTS: 'transcripts',
  SESSION_ID: 'sessionId',
} as const;

/**
 * Get user preferences from storage
 */
export async function getPreferences(): Promise<UserPreferences> {
  try {
    const result = await chrome.storage.local.get([STORAGE_KEYS.PREFERENCES]);
    return result[STORAGE_KEYS.PREFERENCES] || DEFAULT_PREFERENCES;
  } catch (error) {
    console.error('Failed to get preferences:', error);
    return DEFAULT_PREFERENCES;
  }
}

/**
 * Save user preferences to storage
 */
export async function savePreferences(preferences: UserPreferences): Promise<boolean> {
  try {
    await chrome.storage.local.set({
      [STORAGE_KEYS.PREFERENCES]: preferences,
    });
    return true;
  } catch (error) {
    console.error('Failed to save preferences:', error);
    return false;
  }
}

/**
 * Update specific preference field
 */
export async function updatePreference<K extends keyof UserPreferences>(
  key: K,
  value: UserPreferences[K]
): Promise<boolean> {
  try {
    const preferences = await getPreferences();
    preferences[key] = value;
    return await savePreferences(preferences);
  } catch (error) {
    console.error('Failed to update preference:', error);
    return false;
  }
}

/**
 * Get extension settings
 */
export async function getSettings(): Promise<ExtensionSettings> {
  try {
    const result = await chrome.storage.local.get([STORAGE_KEYS.SETTINGS]);
    const settings = result[STORAGE_KEYS.SETTINGS] || {};
    
    // Ensure preferences exist
    if (!settings.preferences) {
      settings.preferences = DEFAULT_PREFERENCES;
    }
    
    return settings as ExtensionSettings;
  } catch (error) {
    console.error('Failed to get settings:', error);
    return {
      preferences: DEFAULT_PREFERENCES,
    };
  }
}

/**
 * Save extension settings
 */
export async function saveSettings(settings: ExtensionSettings): Promise<boolean> {
  try {
    await chrome.storage.local.set({
      [STORAGE_KEYS.SETTINGS]: settings,
    });
    return true;
  } catch (error) {
    console.error('Failed to save settings:', error);
    return false;
  }
}

/**
 * Reset preferences to defaults
 */
export async function resetPreferences(): Promise<boolean> {
  return await savePreferences(DEFAULT_PREFERENCES);
}

/**
 * Clear all storage (for testing/debugging)
 */
export async function clearStorage(): Promise<boolean> {
  try {
    await chrome.storage.local.clear();
    return true;
  } catch (error) {
    console.error('Failed to clear storage:', error);
    return false;
  }
}

/**
 * Get current session ID
 */
export async function getSessionId(): Promise<string | null> {
  try {
    const result = await chrome.storage.local.get([STORAGE_KEYS.SESSION_ID]);
    return result[STORAGE_KEYS.SESSION_ID] || null;
  } catch (error) {
    console.error('Failed to get session ID:', error);
    return null;
  }
}

/**
 * Set current session ID
 */
export async function setSessionId(sessionId: string): Promise<boolean> {
  try {
    await chrome.storage.local.set({
      [STORAGE_KEYS.SESSION_ID]: sessionId,
    });
    return true;
  } catch (error) {
    console.error('Failed to set session ID:', error);
    return false;
  }
}

/**
 * Listen for storage changes
 */
export function onStorageChange(
  callback: (changes: { [key: string]: chrome.storage.StorageChange }) => void
): void {
  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === 'local') {
      callback(changes);
    }
  });
}
