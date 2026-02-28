/**
 * Alert Message Localization
 * 
 * Provides localized alert messages based on threat level and user's preferred language
 */

import { Language, getTranslations } from './translations';

export type ThreatLevel = 'low' | 'moderate' | 'high' | 'critical';

/**
 * Get localized alert message based on threat level
 */
export function getLocalizedAlertMessage(
  threatLevel: ThreatLevel,
  language: Language
): string {
  const t = getTranslations(language);
  
  switch (threatLevel) {
    case 'critical':
      return t.criticalThreatMessage;
    case 'high':
      return t.highRiskMessage;
    case 'moderate':
      return t.moderateRiskMessage;
    default:
      return t.safeMessage;
  }
}

/**
 * Get localized threat level text
 */
export function getLocalizedThreatLevel(
  threatLevel: ThreatLevel,
  language: Language
): string {
  const t = getTranslations(language);
  
  switch (threatLevel) {
    case 'critical':
      return t.threatLevelCritical;
    case 'high':
      return t.threatLevelHigh;
    case 'moderate':
      return t.threatLevelModerate;
    default:
      return t.threatLevelLow;
  }
}
