/**
 * useTranslation Hook
 * 
 * React hook for accessing translations based on user's preferred language
 */

import { useState, useEffect } from 'react';
import { Language, Translations, getTranslations } from './translations';
import { getPreferences } from '../utils/storage';

/**
 * Hook to get translations for the current language
 */
export function useTranslation() {
  const [language, setLanguage] = useState<Language>('en');
  const [translations, setTranslations] = useState<Translations>(getTranslations('en'));

  useEffect(() => {
    loadLanguage();

    // Listen for language changes
    const handleStorageChange = (changes: { [key: string]: chrome.storage.StorageChange }) => {
      if (changes.preferences?.newValue?.language) {
        const newLang = changes.preferences.newValue.language as Language;
        setLanguage(newLang);
        setTranslations(getTranslations(newLang));
      }
    };

    chrome.storage.onChanged.addListener(handleStorageChange);

    return () => {
      chrome.storage.onChanged.removeListener(handleStorageChange);
    };
  }, []);

  const loadLanguage = async () => {
    const prefs = await getPreferences();
    const lang = prefs.language as Language;
    setLanguage(lang);
    setTranslations(getTranslations(lang));
  };

  return { t: translations, language };
}
