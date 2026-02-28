/**
 * Popup UI
 * 
 * React-based popup interface for displaying threat status and controls.
 */

import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { ThreatAlert, DetectionStatus } from '../types';
import { PreferencesPanel } from './PreferencesPanel';
import { useTranslation } from '../i18n/useTranslation';
import './popup.css';

const Popup: React.FC = () => {
  const { t } = useTranslation();
  const [status, setStatus] = useState<DetectionStatus | null>(null);
  const [alerts, setAlerts] = useState<ThreatAlert[]>([]);
  const [currentThreat, setCurrentThreat] = useState<number>(0);
  const [transcripts, setTranscripts] = useState<string[]>([]);
  const [showPreferences, setShowPreferences] = useState(false);

  useEffect(() => {
    // Load initial data
    loadStatus();
    loadAlerts();
    loadTranscripts();

    // Refresh every second
    const interval = setInterval(() => {
      loadStatus();
      loadAlerts();
      loadTranscripts();
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const loadStatus = async () => {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });
      setStatus(response.status);
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  };

  const loadAlerts = async () => {
    try {
      const result = await chrome.storage.local.get(['alerts']);
      const alertList = result.alerts || [];
      setAlerts(alertList);

      // Calculate current threat level
      if (alertList.length > 0) {
        const latestAlert = alertList[alertList.length - 1];
        setCurrentThreat(latestAlert.score);
      } else {
        setCurrentThreat(0);
      }
    } catch (error) {
      console.error('Failed to load alerts:', error);
    }
  };

  const loadTranscripts = async () => {
    try {
      const result = await chrome.storage.local.get(['transcripts']);
      const transcriptList = result.transcripts || [];
      setTranscripts(transcriptList);
    } catch (error) {
      console.error('Failed to load transcripts:', error);
    }
  };

  const handleEndCall = () => {
    if (confirm(t.endCallConfirm)) {
      // Close the current tab
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]?.id) {
          chrome.tabs.remove(tabs[0].id);
        }
      });
    }
  };

  const handleReportThreat = () => {
    // TODO: Implement threat reporting
    alert(t.threatReported);
  };

  const getThreatLevel = (): string => {
    if (currentThreat >= 8.5) return 'critical';
    if (currentThreat >= 7.0) return 'high';
    if (currentThreat >= 5.0) return 'moderate';
    return 'low';
  };

  const getThreatLevelText = (): string => {
    const level = getThreatLevel();
    switch (level) {
      case 'critical': return t.threatLevelCritical;
      case 'high': return t.threatLevelHigh;
      case 'moderate': return t.threatLevelModerate;
      default: return t.threatLevelLow;
    }
  };

  const getThreatColor = (): string => {
    const level = getThreatLevel();
    switch (level) {
      case 'critical': return '#DC2626';
      case 'high': return '#EA580C';
      case 'moderate': return '#F59E0B';
      default: return '#10B981';
    }
  };

  return (
    <div className="popup-container" role="main" aria-label={t.appName}>
      {showPreferences ? (
        <PreferencesPanel onClose={() => setShowPreferences(false)} />
      ) : (
        <>
          <header className="popup-header">
            <h1>{t.appName}</h1>
            <p>{t.appTagline}</p>
            <button
              className="settings-btn"
              onClick={() => setShowPreferences(true)}
              title={t.preferences}
              aria-label={t.preferences}
              type="button"
            >
              ⚙️
            </button>
          </header>

      <div className="threat-gauge" role="img" aria-label={`${t.threatLevel}: ${getThreatLevelText()}, ${t.score}: ${currentThreat.toFixed(1)}`}>
        <svg width="200" height="120" viewBox="0 0 200 120" aria-hidden="true">
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#E5E7EB"
            strokeWidth="20"
            strokeLinecap="round"
          />
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={getThreatColor()}
            strokeWidth="20"
            strokeLinecap="round"
            strokeDasharray={`${(currentThreat / 10) * 251.2} 251.2`}
          />
          <text
            x="100"
            y="90"
            textAnchor="middle"
            fontSize="32"
            fontWeight="bold"
            fill={getThreatColor()}
          >
            {currentThreat.toFixed(1)}
          </text>
          <text
            x="100"
            y="110"
            textAnchor="middle"
            fontSize="14"
            fill="#6B7280"
          >
            {getThreatLevelText()}
          </text>
        </svg>
      </div>

      <div className="detection-status" role="region" aria-label={t.detectionStatus}>
        <h2>{t.detectionStatus}</h2>
        {status ? (
          <div className="status-indicators" role="list">
            <div 
              className={`status-item ${status.audioActive ? 'active' : 'inactive'}`}
              role="listitem"
              aria-label={`${t.audioDetection}: ${status.audioActive ? t.active : t.inactive}`}
            >
              <span className="status-icon" aria-hidden="true">🎤</span>
              <span>{t.audioDetection}</span>
            </div>
            <div 
              className={`status-item ${status.visualActive ? 'active' : 'inactive'}`}
              role="listitem"
              aria-label={`${t.visualDetection}: ${status.visualActive ? t.active : t.inactive}`}
            >
              <span className="status-icon" aria-hidden="true">📹</span>
              <span>{t.visualDetection}</span>
            </div>
            <div 
              className={`status-item ${status.livenessActive ? 'active' : 'inactive'}`}
              role="listitem"
              aria-label={`${t.livenessDetection}: ${status.livenessActive ? t.active : t.inactive}`}
            >
              <span className="status-icon" aria-hidden="true">👤</span>
              <span>{t.livenessDetection}</span>
            </div>
          </div>
        ) : (
          <p className="no-session">{t.noActiveSession}</p>
        )}
      </div>

      {alerts.length > 0 && (
        <div className="recent-alerts" role="region" aria-label={t.recentAlerts}>
          <h2>{t.recentAlerts}</h2>
          <div className="alerts-list" role="list">
            {alerts.slice(-3).reverse().map((alert, index) => (
              <div 
                key={index} 
                className={`alert-item alert-${alert.level}`}
                role="listitem"
                aria-label={`${alert.level} ${t.alert}: ${alert.message}`}
              >
                <div className="alert-header">
                  <span className="alert-level">{alert.level.toUpperCase()}</span>
                  <span className="alert-time">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="alert-message">{alert.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {transcripts.length > 0 && (
        <div className="transcript-section" role="region" aria-label={t.recentTranscript}>
          <h2>{t.recentTranscript}</h2>
          <div className="transcript-list" role="list">
            {transcripts.slice(-5).reverse().map((transcript, index) => (
              <div key={index} className="transcript-item" role="listitem">
                <p>{transcript}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="action-buttons" role="group" aria-label={t.actions}>
        <button 
          className="btn btn-danger" 
          onClick={handleEndCall}
          aria-label={t.endCall}
          type="button"
        >
          {t.endCall}
        </button>
        <button 
          className="btn btn-primary" 
          onClick={handleReportThreat}
          aria-label={t.reportThreat}
          type="button"
        >
          {t.reportThreat}
        </button>
      </div>

      <footer className="popup-footer">
        <p>{t.protectedBy}</p>
      </footer>
        </>
      )}
    </div>
  );
};

// Mount React app
const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<Popup />);
}
