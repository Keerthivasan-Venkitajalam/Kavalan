/**
 * Unit Tests for Translation System
 * 
 * Tests specific examples and edge cases for the i18n implementation
 */

import { describe, it, expect } from 'vitest';
import { 
  translations, 
  getTranslations, 
  t, 
  Language 
} from '../translations';

describe('Translation System', () => {
  describe('getTranslations', () => {
    it('should return English translations for "en" language code', () => {
      const trans = getTranslations('en');
      
      expect(trans.appName).toBe('Kavalan');
      expect(trans.appTagline).toBe('Digital Arrest Scam Detector');
      expect(trans.threatLevelCritical).toBe('CRITICAL');
    });

    it('should return Hindi translations for "hi" language code', () => {
      const trans = getTranslations('hi');
      
      expect(trans.appName).toBe('कावलन');
      expect(trans.threatLevelCritical).toBe('गंभीर');
    });

    it('should return Tamil translations for "ta" language code', () => {
      const trans = getTranslations('ta');
      
      expect(trans.appName).toBe('காவலன்');
      expect(trans.threatLevelCritical).toBe('முக்கியமான');
    });

    it('should return Telugu translations for "te" language code', () => {
      const trans = getTranslations('te');
      
      expect(trans.appName).toBe('కావలన్');
      expect(trans.threatLevelCritical).toBe('క్లిష్టమైన');
    });

    it('should return Malayalam translations for "ml" language code', () => {
      const trans = getTranslations('ml');
      
      expect(trans.appName).toBe('കാവലൻ');
      expect(trans.threatLevelCritical).toBe('നിർണായക');
    });

    it('should return Kannada translations for "kn" language code', () => {
      const trans = getTranslations('kn');
      
      expect(trans.appName).toBe('ಕಾವಲನ್');
      expect(trans.threatLevelCritical).toBe('ನಿರ್ಣಾಯಕ');
    });

    it('should fallback to English for unsupported language', () => {
      const trans = getTranslations('fr' as Language);
      
      expect(trans.appName).toBe('Kavalan');
      expect(trans.appTagline).toBe('Digital Arrest Scam Detector');
    });
  });

  describe('t function', () => {
    it('should return correct translation for given language and key', () => {
      expect(t('en', 'appName')).toBe('Kavalan');
      expect(t('hi', 'appName')).toBe('कावलन');
      expect(t('ta', 'appName')).toBe('காவலன்');
    });

    it('should fallback to English for unsupported language', () => {
      expect(t('invalid' as Language, 'appName')).toBe('Kavalan');
    });
  });

  describe('Translation Completeness', () => {
    const requiredKeys: (keyof typeof translations.en)[] = [
      'appName',
      'appTagline',
      'threatLevelLow',
      'threatLevelModerate',
      'threatLevelHigh',
      'threatLevelCritical',
      'detectionStatus',
      'audioDetection',
      'visualDetection',
      'livenessDetection',
      'noActiveSession',
      'recentAlerts',
      'criticalThreatMessage',
      'highRiskMessage',
      'moderateRiskMessage',
      'safeMessage',
      'recentTranscript',
      'endCall',
      'reportThreat',
      'endCallConfirm',
      'threatReported',
      'protectedBy',
      'preferences',
      'language',
      'selectLanguage',
      'alertVolume',
      'adjustVolume',
      'stealthMode',
      'stealthModeHelp',
      'autoReport',
      'autoReportHelp',
      'savePreferences',
      'saving',
      'saved',
      'languageEnglish',
      'languageHindi',
      'languageTamil',
      'languageTelugu',
      'languageMalayalam',
      'languageKannada',
    ];

    it('should have all required keys in English translations', () => {
      const englishKeys = Object.keys(translations.en);
      
      requiredKeys.forEach(key => {
        expect(englishKeys).toContain(key);
        expect(translations.en[key]).toBeTruthy();
      });
    });

    it('should have all required keys in all supported languages', () => {
      const languages: Language[] = ['en', 'hi', 'ta', 'te', 'ml', 'kn'];
      
      languages.forEach(lang => {
        const trans = translations[lang];
        
        requiredKeys.forEach(key => {
          expect(trans[key]).toBeTruthy();
          expect(typeof trans[key]).toBe('string');
          expect(trans[key].length).toBeGreaterThan(0);
        });
      });
    });
  });

  describe('Alert Messages', () => {
    it('should have distinct messages for each threat level in English', () => {
      const { criticalThreatMessage, highRiskMessage, moderateRiskMessage, safeMessage } = translations.en;
      
      const messages = [criticalThreatMessage, highRiskMessage, moderateRiskMessage, safeMessage];
      const uniqueMessages = new Set(messages);
      
      expect(uniqueMessages.size).toBe(4);
    });

    it('should have distinct threat level labels in English', () => {
      const { threatLevelLow, threatLevelModerate, threatLevelHigh, threatLevelCritical } = translations.en;
      
      const levels = [threatLevelLow, threatLevelModerate, threatLevelHigh, threatLevelCritical];
      const uniqueLevels = new Set(levels);
      
      expect(uniqueLevels.size).toBe(4);
    });

    it('should have appropriate urgency in critical threat messages', () => {
      const languages: Language[] = ['en', 'hi', 'ta', 'te', 'ml', 'kn'];
      
      languages.forEach(lang => {
        const trans = translations[lang];
        
        // Critical message should be different from safe message
        expect(trans.criticalThreatMessage).not.toBe(trans.safeMessage);
        
        // Critical message should not be empty
        expect(trans.criticalThreatMessage.length).toBeGreaterThan(0);
      });
    });
  });

  describe('UI Text', () => {
    it('should have consistent button labels across languages', () => {
      const languages: Language[] = ['en', 'hi', 'ta', 'te', 'ml', 'kn'];
      
      languages.forEach(lang => {
        const trans = translations[lang];
        
        expect(trans.endCall).toBeTruthy();
        expect(trans.reportThreat).toBeTruthy();
        expect(trans.savePreferences).toBeTruthy();
      });
    });

    it('should have help text for all preference options', () => {
      const languages: Language[] = ['en', 'hi', 'ta', 'te', 'ml', 'kn'];
      
      languages.forEach(lang => {
        const trans = translations[lang];
        
        expect(trans.selectLanguage).toBeTruthy();
        expect(trans.adjustVolume).toBeTruthy();
        expect(trans.stealthModeHelp).toBeTruthy();
        expect(trans.autoReportHelp).toBeTruthy();
      });
    });
  });

  describe('Language Names', () => {
    it('should have all language names in all supported languages', () => {
      const languages: Language[] = ['en', 'hi', 'ta', 'te', 'ml', 'kn'];
      
      languages.forEach(lang => {
        const trans = translations[lang];
        
        expect(trans.languageEnglish).toBeTruthy();
        expect(trans.languageHindi).toBeTruthy();
        expect(trans.languageTamil).toBeTruthy();
        expect(trans.languageTelugu).toBeTruthy();
        expect(trans.languageMalayalam).toBeTruthy();
        expect(trans.languageKannada).toBeTruthy();
      });
    });
  });
});
