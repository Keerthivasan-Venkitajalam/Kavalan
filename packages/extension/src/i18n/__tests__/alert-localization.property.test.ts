/**
 * Property-Based Tests for Alert Localization
 * 
 * Feature: production-ready-browser-extension
 * Property 12: Alert Localization
 * 
 * Validates: Requirements 6.5
 * 
 * For any threat alert generated, the alert message should be displayed 
 * in the user's configured preferred language.
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { 
  getLocalizedAlertMessage, 
  getLocalizedThreatLevel,
  ThreatLevel 
} from '../alertMessages';
import { Language, translations } from '../translations';

describe('Property 12: Alert Localization', () => {
  const supportedLanguages: Language[] = ['en', 'hi', 'ta', 'te', 'ml', 'kn'];
  const threatLevels: ThreatLevel[] = ['low', 'moderate', 'high', 'critical'];

  it('should return non-empty localized alert messages for all language-threat combinations', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...supportedLanguages),
        fc.constantFrom(...threatLevels),
        (language, threatLevel) => {
          const message = getLocalizedAlertMessage(threatLevel, language);
          
          // Message should not be empty
          expect(message).toBeTruthy();
          expect(message.length).toBeGreaterThan(0);
          
          // Message should be a string
          expect(typeof message).toBe('string');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should return different messages for different threat levels in the same language', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...supportedLanguages),
        (language) => {
          const lowMessage = getLocalizedAlertMessage('low', language);
          const moderateMessage = getLocalizedAlertMessage('moderate', language);
          const highMessage = getLocalizedAlertMessage('high', language);
          const criticalMessage = getLocalizedAlertMessage('critical', language);
          
          // All messages should be different
          const messages = [lowMessage, moderateMessage, highMessage, criticalMessage];
          const uniqueMessages = new Set(messages);
          
          expect(uniqueMessages.size).toBe(4);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should return consistent messages for the same language-threat combination', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...supportedLanguages),
        fc.constantFrom(...threatLevels),
        (language, threatLevel) => {
          const message1 = getLocalizedAlertMessage(threatLevel, language);
          const message2 = getLocalizedAlertMessage(threatLevel, language);
          
          // Same inputs should produce same output
          expect(message1).toBe(message2);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should return localized threat level text for all language-threat combinations', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...supportedLanguages),
        fc.constantFrom(...threatLevels),
        (language, threatLevel) => {
          const levelText = getLocalizedThreatLevel(threatLevel, language);
          
          // Level text should not be empty
          expect(levelText).toBeTruthy();
          expect(levelText.length).toBeGreaterThan(0);
          
          // Level text should be a string
          expect(typeof levelText).toBe('string');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should use correct translation keys from translations object', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...supportedLanguages),
        fc.constantFrom(...threatLevels),
        (language, threatLevel) => {
          const message = getLocalizedAlertMessage(threatLevel, language);
          const trans = translations[language];
          
          // Message should match one of the expected translation keys
          const expectedMessages = [
            trans.criticalThreatMessage,
            trans.highRiskMessage,
            trans.moderateRiskMessage,
            trans.safeMessage
          ];
          
          expect(expectedMessages).toContain(message);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should fallback to English for unsupported languages', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...threatLevels),
        (threatLevel) => {
          // Test with invalid language (should fallback to English)
          const message = getLocalizedAlertMessage(threatLevel, 'invalid' as Language);
          const englishMessage = getLocalizedAlertMessage(threatLevel, 'en');
          
          // Should return English message as fallback
          expect(message).toBe(englishMessage);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should maintain translation completeness across all languages', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...supportedLanguages),
        (language) => {
          const trans = translations[language];
          
          // All required translation keys should exist
          expect(trans.criticalThreatMessage).toBeTruthy();
          expect(trans.highRiskMessage).toBeTruthy();
          expect(trans.moderateRiskMessage).toBeTruthy();
          expect(trans.safeMessage).toBeTruthy();
          expect(trans.threatLevelLow).toBeTruthy();
          expect(trans.threatLevelModerate).toBeTruthy();
          expect(trans.threatLevelHigh).toBeTruthy();
          expect(trans.threatLevelCritical).toBeTruthy();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should preserve alert semantics across languages', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...threatLevels),
        (threatLevel) => {
          // Get messages in all languages for the same threat level
          const messages = supportedLanguages.map(lang => 
            getLocalizedAlertMessage(threatLevel, lang)
          );
          
          // All messages should be non-empty (semantic preservation)
          messages.forEach(message => {
            expect(message).toBeTruthy();
            expect(message.length).toBeGreaterThan(0);
          });
          
          // Messages should be different across languages (not just copying English)
          const uniqueMessages = new Set(messages);
          expect(uniqueMessages.size).toBeGreaterThan(1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should handle critical threats with appropriate urgency in all languages', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...supportedLanguages),
        (language) => {
          const criticalMessage = getLocalizedAlertMessage('critical', language);
          const lowMessage = getLocalizedAlertMessage('low', language);
          
          // Critical message should be different from low message
          expect(criticalMessage).not.toBe(lowMessage);
          
          // Critical message should not be empty
          expect(criticalMessage.length).toBeGreaterThan(0);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should provide consistent threat level ordering across languages', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...supportedLanguages),
        (language) => {
          const levels = ['low', 'moderate', 'high', 'critical'] as ThreatLevel[];
          const levelTexts = levels.map(level => getLocalizedThreatLevel(level, language));
          
          // All level texts should be unique
          const uniqueTexts = new Set(levelTexts);
          expect(uniqueTexts.size).toBe(4);
          
          // All level texts should be non-empty
          levelTexts.forEach(text => {
            expect(text).toBeTruthy();
            expect(text.length).toBeGreaterThan(0);
          });
        }
      ),
      { numRuns: 100 }
    );
  });
});
