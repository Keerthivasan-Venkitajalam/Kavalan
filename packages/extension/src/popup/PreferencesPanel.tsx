/**
 * Preferences Panel Component
 * 
 * UI for managing user preferences (language, alert volume, stealth mode, auto-report).
 */

import React, { useState, useEffect } from 'react';
import { UserPreferences } from '../types';
import { getPreferences, savePreferences } from '../utils/storage';
import { useTranslation } from '../i18n/useTranslation';

interface PreferencesPanelProps {
  onClose: () => void;
}

const SUPPORTED_LANGUAGES = [
  { code: 'en', nameKey: 'languageEnglish' as const },
  { code: 'hi', nameKey: 'languageHindi' as const },
  { code: 'ta', nameKey: 'languageTamil' as const },
  { code: 'te', nameKey: 'languageTelugu' as const },
  { code: 'ml', nameKey: 'languageMalayalam' as const },
  { code: 'kn', nameKey: 'languageKannada' as const },
];

export const PreferencesPanel: React.FC<PreferencesPanelProps> = ({ onClose }) => {
  const { t } = useTranslation();
  const [preferences, setPreferences] = useState<UserPreferences>({
    language: 'en',
    alertVolume: 0.8,
    stealthMode: false,
    autoReport: false,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    const prefs = await getPreferences();
    setPreferences(prefs);
  };

  const handleSave = async () => {
    setSaving(true);
    const success = await savePreferences(preferences);
    setSaving(false);
    
    if (success) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  };

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setPreferences({ ...preferences, language: e.target.value });
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPreferences({ ...preferences, alertVolume: parseFloat(e.target.value) });
  };

  const handleStealthModeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPreferences({ ...preferences, stealthMode: e.target.checked });
  };

  const handleAutoReportChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPreferences({ ...preferences, autoReport: e.target.checked });
  };

  return (
    <div className="preferences-panel" role="dialog" aria-labelledby="preferences-title">
      <div className="preferences-header">
        <h2 id="preferences-title">{t.preferences}</h2>
        <button 
          className="close-btn" 
          onClick={onClose}
          aria-label="Close preferences"
          type="button"
        >✕</button>
      </div>

      <div className="preferences-content">
        <div className="preference-group">
          <label htmlFor="language">{t.language}</label>
          <select
            id="language"
            value={preferences.language}
            onChange={handleLanguageChange}
            className="preference-select"
            aria-describedby="language-help"
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {t[lang.nameKey]}
              </option>
            ))}
          </select>
          <p className="preference-help" id="language-help">
            {t.selectLanguage}
          </p>
        </div>

        <div className="preference-group">
          <label htmlFor="volume">{t.alertVolume}</label>
          <div className="volume-control">
            <input
              type="range"
              id="volume"
              min="0"
              max="1"
              step="0.1"
              value={preferences.alertVolume}
              onChange={handleVolumeChange}
              className="preference-slider"
              aria-label={`${t.alertVolume}: ${Math.round(preferences.alertVolume * 100)}%`}
              aria-describedby="volume-help"
            />
            <span className="volume-value" aria-hidden="true">{Math.round(preferences.alertVolume * 100)}%</span>
          </div>
          <p className="preference-help" id="volume-help">
            {t.adjustVolume}
          </p>
        </div>

        <div className="preference-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={preferences.stealthMode}
              onChange={handleStealthModeChange}
              className="preference-checkbox"
              aria-describedby="stealth-help"
            />
            <span>{t.stealthMode}</span>
          </label>
          <p className="preference-help" id="stealth-help">
            {t.stealthModeHelp}
          </p>
        </div>

        <div className="preference-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={preferences.autoReport}
              onChange={handleAutoReportChange}
              className="preference-checkbox"
              aria-describedby="autoreport-help"
            />
            <span>{t.autoReport}</span>
          </label>
          <p className="preference-help" id="autoreport-help">
            {t.autoReportHelp}
          </p>
        </div>
      </div>

      <div className="preferences-footer">
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving}
          aria-label={saving ? t.saving : saved ? t.saved : t.savePreferences}
          type="button"
        >
          {saving ? t.saving : saved ? t.saved : t.savePreferences}
        </button>
      </div>
    </div>
  );
};
