/**
 * Property-Based Tests for Storage Utility
 * 
 * Feature: production-ready-browser-extension
 * Property 3: Preference Persistence Round-Trip
 * 
 * For any valid user preference configuration, saving preferences then reloading
 * the extension should restore the exact same preference values.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import fc from 'fast-check';
import { UserPreferences } from '../../types';
import {
  getPreferences,
  savePreferences,
  updatePreference,
  resetPreferences,
} from '../storage';

// Mock chrome.storage API
const mockStorage = new Map<string, any>();

beforeEach(() => {
  mockStorage.clear();
  
  // Mock chrome.storage.local
  global.chrome = {
    storage: {
      local: {
        get: vi.fn((keys: string[]) => {
          const result: any = {};
          keys.forEach((key) => {
            if (mockStorage.has(key)) {
              result[key] = mockStorage.get(key);
            }
          });
          return Promise.resolve(result);
        }),
        set: vi.fn((items: any) => {
          Object.entries(items).forEach(([key, value]) => {
            mockStorage.set(key, value);
          });
          return Promise.resolve();
        }),
        clear: vi.fn(() => {
          mockStorage.clear();
          return Promise.resolve();
        }),
      },
      onChanged: {
        addListener: vi.fn(),
      },
    },
  } as any;
});

// Arbitrary generator for UserPreferences
const userPreferencesArbitrary = fc.record({
  language: fc.constantFrom('en', 'hi', 'ta', 'te', 'ml', 'kn'),
  alertVolume: fc.double({ min: 0, max: 1 }),
  stealthMode: fc.boolean(),
  autoReport: fc.boolean(),
});

describe('Property 3: Preference Persistence Round-Trip', () => {
  it('should preserve preferences after save and load cycle', async () => {
    await fc.assert(
      fc.asyncProperty(userPreferencesArbitrary, async (preferences) => {
        // Save preferences
        const saveSuccess = await savePreferences(preferences);
        expect(saveSuccess).toBe(true);

        // Load preferences
        const loadedPreferences = await getPreferences();

        // Verify round-trip preserves all values
        expect(loadedPreferences.language).toBe(preferences.language);
        expect(loadedPreferences.alertVolume).toBeCloseTo(preferences.alertVolume, 10);
        expect(loadedPreferences.stealthMode).toBe(preferences.stealthMode);
        expect(loadedPreferences.autoReport).toBe(preferences.autoReport);
      }),
      { numRuns: 100 }
    );
  });

  it('should preserve preferences after multiple save cycles', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(userPreferencesArbitrary, { minLength: 2, maxLength: 5 }),
        async (preferencesList) => {
          let lastPreferences: UserPreferences | null = null;

          // Save each preference configuration
          for (const preferences of preferencesList) {
            await savePreferences(preferences);
            lastPreferences = preferences;
          }

          // Load and verify only the last saved preferences are present
          const loadedPreferences = await getPreferences();
          expect(loadedPreferences).toEqual(lastPreferences);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should preserve individual preference updates', async () => {
    await fc.assert(
      fc.asyncProperty(
        userPreferencesArbitrary,
        fc.constantFrom<keyof UserPreferences>('language', 'alertVolume', 'stealthMode', 'autoReport'),
        async (initialPreferences, fieldToUpdate) => {
          // Save initial preferences
          await savePreferences(initialPreferences);

          // Generate new value for the field
          let newValue: any;
          if (fieldToUpdate === 'language') {
            newValue = 'hi';
          } else if (fieldToUpdate === 'alertVolume') {
            newValue = 0.5;
          } else {
            newValue = !initialPreferences[fieldToUpdate];
          }

          // Update single field
          await updatePreference(fieldToUpdate, newValue);

          // Load and verify
          const loadedPreferences = await getPreferences();
          expect(loadedPreferences[fieldToUpdate]).toEqual(newValue);

          // Verify other fields remain unchanged
          const otherFields = Object.keys(initialPreferences).filter(
            (key) => key !== fieldToUpdate
          ) as (keyof UserPreferences)[];

          otherFields.forEach((field) => {
            if (field === 'alertVolume') {
              expect(loadedPreferences[field]).toBeCloseTo(
                initialPreferences[field] as number,
                10
              );
            } else {
              expect(loadedPreferences[field]).toEqual(initialPreferences[field]);
            }
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should reset to defaults correctly', async () => {
    await fc.assert(
      fc.asyncProperty(userPreferencesArbitrary, async (preferences) => {
        // Save custom preferences
        await savePreferences(preferences);

        // Reset to defaults
        await resetPreferences();

        // Load and verify defaults
        const loadedPreferences = await getPreferences();
        expect(loadedPreferences.language).toBe('en');
        expect(loadedPreferences.alertVolume).toBe(0.8);
        expect(loadedPreferences.stealthMode).toBe(false);
        expect(loadedPreferences.autoReport).toBe(false);
      }),
      { numRuns: 100 }
    );
  });

  it('should handle concurrent save operations', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(userPreferencesArbitrary, { minLength: 3, maxLength: 10 }),
        async (preferencesList) => {
          // Save all preferences concurrently
          const savePromises = preferencesList.map((prefs) => savePreferences(prefs));
          await Promise.all(savePromises);

          // Load preferences
          const loadedPreferences = await getPreferences();

          // Verify loaded preferences match one of the saved configurations
          const matches = preferencesList.some((prefs) => {
            return (
              prefs.language === loadedPreferences.language &&
              Math.abs(prefs.alertVolume - loadedPreferences.alertVolume) < 0.0001 &&
              prefs.stealthMode === loadedPreferences.stealthMode &&
              prefs.autoReport === loadedPreferences.autoReport
            );
          });

          expect(matches).toBe(true);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should preserve preferences across storage clear and restore', async () => {
    await fc.assert(
      fc.asyncProperty(userPreferencesArbitrary, async (preferences) => {
        // Save preferences
        await savePreferences(preferences);

        // Simulate storage backup
        const backup = await getPreferences();

        // Clear storage
        await chrome.storage.local.clear();

        // Restore from backup
        await savePreferences(backup);

        // Load and verify
        const loadedPreferences = await getPreferences();
        expect(loadedPreferences).toEqual(preferences);
      }),
      { numRuns: 100 }
    );
  });

  it('should handle edge case values correctly', async () => {
    const edgeCases: UserPreferences[] = [
      // Minimum volume
      { language: 'en', alertVolume: 0, stealthMode: false, autoReport: false },
      // Maximum volume
      { language: 'en', alertVolume: 1, stealthMode: false, autoReport: false },
      // All features enabled
      { language: 'hi', alertVolume: 0.5, stealthMode: true, autoReport: true },
      // All features disabled
      { language: 'en', alertVolume: 0, stealthMode: false, autoReport: false },
    ];

    for (const preferences of edgeCases) {
      await savePreferences(preferences);
      const loaded = await getPreferences();
      expect(loaded).toEqual(preferences);
    }
  });
});
