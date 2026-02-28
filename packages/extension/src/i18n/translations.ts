/**
 * Translation Strings
 * 
 * Multi-language support for Hindi, English, Tamil, Telugu, Malayalam, Kannada
 */

export type Language = 'en' | 'hi' | 'ta' | 'te' | 'ml' | 'kn';

export interface Translations {
  // Header
  appName: string;
  appTagline: string;
  
  // Threat Levels
  threatLevel: string;
  score: string;
  threatLevelLow: string;
  threatLevelModerate: string;
  threatLevelHigh: string;
  threatLevelCritical: string;
  
  // Detection Status
  detectionStatus: string;
  audioDetection: string;
  visualDetection: string;
  livenessDetection: string;
  noActiveSession: string;
  active: string;
  inactive: string;
  
  // Alerts
  recentAlerts: string;
  alert: string;
  criticalThreatMessage: string;
  highRiskMessage: string;
  moderateRiskMessage: string;
  safeMessage: string;
  
  // Transcript
  recentTranscript: string;
  
  // Action Buttons
  actions: string;
  endCall: string;
  reportThreat: string;
  endCallConfirm: string;
  threatReported: string;
  
  // Footer
  protectedBy: string;
  
  // Preferences
  preferences: string;
  language: string;
  selectLanguage: string;
  alertVolume: string;
  adjustVolume: string;
  stealthMode: string;
  stealthModeHelp: string;
  autoReport: string;
  autoReportHelp: string;
  savePreferences: string;
  saving: string;
  saved: string;
  
  // Language Names
  languageEnglish: string;
  languageHindi: string;
  languageTamil: string;
  languageTelugu: string;
  languageMalayalam: string;
  languageKannada: string;
}

export const translations: Record<Language, Translations> = {
  en: {
    appName: 'Kavalan',
    appTagline: 'Digital Arrest Scam Detector',
    
    threatLevel: 'Threat Level',
    score: 'Score',
    threatLevelLow: 'LOW',
    threatLevelModerate: 'MODERATE',
    threatLevelHigh: 'HIGH',
    threatLevelCritical: 'CRITICAL',
    
    detectionStatus: 'Detection Status',
    audioDetection: 'Audio',
    visualDetection: 'Visual',
    livenessDetection: 'Liveness',
    noActiveSession: 'No active session',
    active: 'Active',
    inactive: 'Inactive',
    
    recentAlerts: 'Recent Alerts',
    alert: 'Alert',
    criticalThreatMessage: 'CRITICAL THREAT: Disconnect immediately',
    highRiskMessage: 'HIGH RISK: Potential scam detected',
    moderateRiskMessage: 'MODERATE: Suspicious activity',
    safeMessage: 'Safe - No threats detected',
    
    recentTranscript: 'Recent Transcript',
    
    actions: 'Actions',
    endCall: 'End Call',
    reportThreat: 'Report Threat',
    endCallConfirm: 'Are you sure you want to end this call?',
    threatReported: 'Threat reported to authorities',
    
    protectedBy: 'Protected by Kavalan AI',
    
    preferences: 'Preferences',
    language: 'Language',
    selectLanguage: 'Select your preferred language for alerts and interface',
    alertVolume: 'Alert Volume',
    adjustVolume: 'Adjust the volume of audio alerts',
    stealthMode: 'Stealth Mode',
    stealthModeHelp: 'Hide visual indicators during calls (alerts still active)',
    autoReport: 'Auto-Report Threats',
    autoReportHelp: 'Automatically report high-severity threats to authorities',
    savePreferences: 'Save Preferences',
    saving: 'Saving...',
    saved: 'Saved!',
    
    languageEnglish: 'English',
    languageHindi: 'हिन्दी (Hindi)',
    languageTamil: 'தமிழ் (Tamil)',
    languageTelugu: 'తెలుగు (Telugu)',
    languageMalayalam: 'മലയാളം (Malayalam)',
    languageKannada: 'ಕನ್ನಡ (Kannada)',
  },
  
  hi: {
    appName: 'कावलन',
    appTagline: 'डिजिटल गिरफ्तारी घोटाला डिटेक्टर',
    
    threatLevel: 'खतरे का स्तर',
    score: 'स्कोर',
    threatLevelLow: 'कम',
    threatLevelModerate: 'मध्यम',
    threatLevelHigh: 'उच्च',
    threatLevelCritical: 'गंभीर',
    
    detectionStatus: 'पहचान स्थिति',
    audioDetection: 'ऑडियो',
    visualDetection: 'दृश्य',
    livenessDetection: 'जीवंतता',
    noActiveSession: 'कोई सक्रिय सत्र नहीं',
    active: 'सक्रिय',
    inactive: 'निष्क्रिय',
    
    recentAlerts: 'हाल की चेतावनियाँ',
    alert: 'चेतावनी',
    criticalThreatMessage: 'गंभीर खतरा: तुरंत कॉल समाप्त करें',
    highRiskMessage: 'उच्च जोखिम: संभावित घोटाला पाया गया',
    moderateRiskMessage: 'मध्यम: संदिग्ध गतिविधि',
    safeMessage: 'सुरक्षित - कोई खतरा नहीं',
    
    recentTranscript: 'हाल की प्रतिलिपि',
    
    actions: 'कार्रवाई',
    endCall: 'कॉल समाप्त करें',
    reportThreat: 'खतरे की रिपोर्ट करें',
    endCallConfirm: 'क्या आप वाकई इस कॉल को समाप्त करना चाहते हैं?',
    threatReported: 'खतरे की सूचना अधिकारियों को दी गई',
    
    protectedBy: 'कावलन AI द्वारा सुरक्षित',
    
    preferences: 'प्राथमिकताएं',
    language: 'भाषा',
    selectLanguage: 'अलर्ट और इंटरफ़ेस के लिए अपनी पसंदीदा भाषा चुनें',
    alertVolume: 'अलर्ट वॉल्यूम',
    adjustVolume: 'ऑडियो अलर्ट की मात्रा समायोजित करें',
    stealthMode: 'स्टील्थ मोड',
    stealthModeHelp: 'कॉल के दौरान दृश्य संकेतक छिपाएं (अलर्ट अभी भी सक्रिय)',
    autoReport: 'स्वचालित रिपोर्ट',
    autoReportHelp: 'उच्च-गंभीरता वाले खतरों को स्वचालित रूप से रिपोर्ट करें',
    savePreferences: 'प्राथमिकताएं सहेजें',
    saving: 'सहेजा जा रहा है...',
    saved: 'सहेजा गया!',
    
    languageEnglish: 'English',
    languageHindi: 'हिन्दी',
    languageTamil: 'தமிழ்',
    languageTelugu: 'తెలుగు',
    languageMalayalam: 'മലയാളം',
    languageKannada: 'ಕನ್ನಡ',
  },
  
  ta: {
    appName: 'காவலன்',
    appTagline: 'டிஜிட்டல் கைது மோசடி கண்டறிதல்',
    
    threatLevel: 'அச்சுறுத்தல் நிலை',
    score: 'மதிப்பெண்',
    threatLevelLow: 'குறைவு',
    threatLevelModerate: 'மிதமான',
    threatLevelHigh: 'உயர்',
    threatLevelCritical: 'முக்கியமான',
    
    detectionStatus: 'கண்டறிதல் நிலை',
    audioDetection: 'ஆடியோ',
    visualDetection: 'காட்சி',
    livenessDetection: 'உயிர்ப்பு',
    noActiveSession: 'செயலில் உள்ள அமர்வு இல்லை',
    active: 'செயலில்',
    inactive: 'செயலற்ற',
    
    recentAlerts: 'சமீபத்திய எச்சரிக்கைகள்',
    alert: 'எச்சரிக்கை',
    criticalThreatMessage: 'முக்கிய அச்சுறுத்தல்: உடனடியாக துண்டிக்கவும்',
    highRiskMessage: 'அதிக ஆபத்து: சாத்தியமான மோசடி கண்டறியப்பட்டது',
    moderateRiskMessage: 'மிதமான: சந்தேகத்திற்குரிய செயல்பாடு',
    safeMessage: 'பாதுகாப்பானது - அச்சுறுத்தல்கள் இல்லை',
    
    recentTranscript: 'சமீபத்திய பிரதி',
    
    actions: 'செயல்கள்',
    endCall: 'அழைப்பை முடிக்கவும்',
    reportThreat: 'அச்சுறுத்தலை அறிவிக்கவும்',
    endCallConfirm: 'இந்த அழைப்பை முடிக்க விரும்புகிறீர்களா?',
    threatReported: 'அச்சுறுத்தல் அதிகாரிகளுக்கு தெரிவிக்கப்பட்டது',
    
    protectedBy: 'காவலன் AI மூலம் பாதுகாக்கப்பட்டது',
    
    preferences: 'விருப்பத்தேர்வுகள்',
    language: 'மொழி',
    selectLanguage: 'எச்சரிக்கைகள் மற்றும் இடைமுகத்திற்கு உங்கள் விருப்ப மொழியைத் தேர்ந்தெடுக்கவும்',
    alertVolume: 'எச்சரிக்கை ஒலி',
    adjustVolume: 'ஆடியோ எச்சரிக்கைகளின் ஒலியை சரிசெய்யவும்',
    stealthMode: 'மறைநிலை பயன்முறை',
    stealthModeHelp: 'அழைப்புகளின் போது காட்சி குறிகாட்டிகளை மறைக்கவும் (எச்சரிக்கைகள் இன்னும் செயலில்)',
    autoReport: 'தானியங்கி அறிக்கை',
    autoReportHelp: 'உயர்-தீவிரத்துவ அச்சுறுத்தல்களை தானாகவே அறிவிக்கவும்',
    savePreferences: 'விருப்பத்தேர்வுகளை சேமிக்கவும்',
    saving: 'சேமிக்கப்படுகிறது...',
    saved: 'சேமிக்கப்பட்டது!',
    
    languageEnglish: 'English',
    languageHindi: 'हिन्दी',
    languageTamil: 'தமிழ்',
    languageTelugu: 'తెలుగు',
    languageMalayalam: 'മലയാളം',
    languageKannada: 'ಕನ್ನಡ',
  },
  
  te: {
    appName: 'కావలన్',
    appTagline: 'డిజిటల్ అరెస్ట్ స్కామ్ డిటెక్టర్',
    
    threatLevel: 'ముప్పు స్థాయి',
    score: 'స్కోర్',
    threatLevelLow: 'తక్కువ',
    threatLevelModerate: 'మితమైన',
    threatLevelHigh: 'అధిక',
    threatLevelCritical: 'క్లిష్టమైన',
    
    detectionStatus: 'గుర్తింపు స్థితి',
    audioDetection: 'ఆడియో',
    visualDetection: 'దృశ్య',
    livenessDetection: 'జీవత్వం',
    noActiveSession: 'క్రియాశీల సెషన్ లేదు',
    active: 'క్రియాశీల',
    inactive: 'నిష్క్రియ',
    
    recentAlerts: 'ఇటీవలి హెచ్చరికలు',
    alert: 'హెచ్చరిక',
    criticalThreatMessage: 'క్లిష్టమైన ముప్పు: వెంటనే డిస్‌కనెక్ట్ చేయండి',
    highRiskMessage: 'అధిక ప్రమాదం: సంభావ్య స్కామ్ గుర్తించబడింది',
    moderateRiskMessage: 'మితమైన: అనుమానాస్పద కార్యాచరణ',
    safeMessage: 'సురక్షితం - ముప్పులు లేవు',
    
    recentTranscript: 'ఇటీవలి ట్రాన్స్‌క్రిప్ట్',
    
    actions: 'చర్యలు',
    endCall: 'కాల్ ముగించండి',
    reportThreat: 'ముప్పును నివేదించండి',
    endCallConfirm: 'మీరు ఖచ్చితంగా ఈ కాల్‌ను ముగించాలనుకుంటున్నారా?',
    threatReported: 'ముప్పు అధికారులకు నివేదించబడింది',
    
    protectedBy: 'కావలన్ AI ద్వారా రక్షించబడింది',
    
    preferences: 'ప్రాధాన్యతలు',
    language: 'భాష',
    selectLanguage: 'హెచ్చరికలు మరియు ఇంటర్‌ఫేస్ కోసం మీ ఇష్టమైన భాషను ఎంచుకోండి',
    alertVolume: 'హెచ్చరిక వాల్యూమ్',
    adjustVolume: 'ఆడియో హెచ్చరికల వాల్యూమ్‌ను సర్దుబాటు చేయండి',
    stealthMode: 'స్టెల్త్ మోడ్',
    stealthModeHelp: 'కాల్స్ సమయంలో దృశ్య సూచికలను దాచండి (హెచ్చరికలు ఇప్పటికీ క్రియాశీలంగా ఉన్నాయి)',
    autoReport: 'ఆటో-రిపోర్ట్',
    autoReportHelp: 'అధిక-తీవ్రత ముప్పులను స్వయంచాలకంగా నివేదించండి',
    savePreferences: 'ప్రాధాన్యతలను సేవ్ చేయండి',
    saving: 'సేవ్ చేస్తోంది...',
    saved: 'సేవ్ చేయబడింది!',
    
    languageEnglish: 'English',
    languageHindi: 'हिन्दी',
    languageTamil: 'தமிழ்',
    languageTelugu: 'తెలుగు',
    languageMalayalam: 'മലയാളം',
    languageKannada: 'ಕನ್ನಡ',
  },
  
  ml: {
    appName: 'കാവലൻ',
    appTagline: 'ഡിജിറ്റൽ അറസ്റ്റ് സ്കാം ഡിറ്റക്ടർ',
    
    threatLevel: 'ഭീഷണി നില',
    score: 'സ്കോർ',
    threatLevelLow: 'കുറവ്',
    threatLevelModerate: 'മിതമായ',
    threatLevelHigh: 'ഉയർന്ന',
    threatLevelCritical: 'നിർണായക',
    
    detectionStatus: 'കണ്ടെത്തൽ നില',
    audioDetection: 'ഓഡിയോ',
    visualDetection: 'ദൃശ്യ',
    livenessDetection: 'ജീവത്വം',
    noActiveSession: 'സജീവ സെഷൻ ഇല്ല',
    active: 'സജീവം',
    inactive: 'നിഷ്ക്രിയം',
    
    recentAlerts: 'സമീപകാല മുന്നറിയിപ്പുകൾ',
    alert: 'മുന്നറിയിപ്പ്',
    criticalThreatMessage: 'നിർണായക ഭീഷണി: ഉടൻ വിച്ഛേദിക്കുക',
    highRiskMessage: 'ഉയർന്ന അപകടസാധ്യത: സാധ്യമായ തട്ടിപ്പ് കണ്ടെത്തി',
    moderateRiskMessage: 'മിതമായ: സംശയാസ്പദമായ പ്രവർത്തനം',
    safeMessage: 'സുരക്ഷിതം - ഭീഷണികളൊന്നുമില്ല',
    
    recentTranscript: 'സമീപകാല ട്രാൻസ്ക്രിപ്റ്റ്',
    
    actions: 'പ്രവർത്തനങ്ങൾ',
    endCall: 'കോൾ അവസാനിപ്പിക്കുക',
    reportThreat: 'ഭീഷണി റിപ്പോർട്ട് ചെയ്യുക',
    endCallConfirm: 'ഈ കോൾ അവസാനിപ്പിക്കണമെന്ന് ഉറപ്പാണോ?',
    threatReported: 'ഭീഷണി അധികാരികളെ അറിയിച്ചു',
    
    protectedBy: 'കാവലൻ AI സംരക്ഷിച്ചത്',
    
    preferences: 'മുൻഗണനകൾ',
    language: 'ഭാഷ',
    selectLanguage: 'മുന്നറിയിപ്പുകൾക്കും ഇന്റർഫേസിനും നിങ്ങളുടെ ഇഷ്ട ഭാഷ തിരഞ്ഞെടുക്കുക',
    alertVolume: 'മുന്നറിയിപ്പ് വോളിയം',
    adjustVolume: 'ഓഡിയോ മുന്നറിയിപ്പുകളുടെ വോളിയം ക്രമീകരിക്കുക',
    stealthMode: 'സ്റ്റെൽത്ത് മോഡ്',
    stealthModeHelp: 'കോളുകളിൽ ദൃശ്യ സൂചകങ്ങൾ മറയ്ക്കുക (മുന്നറിയിപ്പുകൾ ഇപ്പോഴും സജീവം)',
    autoReport: 'ഓട്ടോ-റിപ്പോർട്ട്',
    autoReportHelp: 'ഉയർന്ന-തീവ്രത ഭീഷണികൾ സ്വയമേവ റിപ്പോർട്ട് ചെയ്യുക',
    savePreferences: 'മുൻഗണനകൾ സംരക്ഷിക്കുക',
    saving: 'സംരക്ഷിക്കുന്നു...',
    saved: 'സംരക്ഷിച്ചു!',
    
    languageEnglish: 'English',
    languageHindi: 'हिन्दी',
    languageTamil: 'தமிழ்',
    languageTelugu: 'తెలుగు',
    languageMalayalam: 'മലയാളം',
    languageKannada: 'ಕನ್ನಡ',
  },
  
  kn: {
    appName: 'ಕಾವಲನ್',
    appTagline: 'ಡಿಜಿಟಲ್ ಅರೆಸ್ಟ್ ಸ್ಕ್ಯಾಮ್ ಡಿಟೆಕ್ಟರ್',
    
    threatLevel: 'ಬೆದರಿಕೆ ಮಟ್ಟ',
    score: 'ಸ್ಕೋರ್',
    threatLevelLow: 'ಕಡಿಮೆ',
    threatLevelModerate: 'ಮಧ್ಯಮ',
    threatLevelHigh: 'ಹೆಚ್ಚು',
    threatLevelCritical: 'ನಿರ್ಣಾಯಕ',
    
    detectionStatus: 'ಪತ್ತೆ ಸ್ಥಿತಿ',
    audioDetection: 'ಆಡಿಯೋ',
    visualDetection: 'ದೃಶ್ಯ',
    livenessDetection: 'ಜೀವಂತಿಕೆ',
    noActiveSession: 'ಸಕ್ರಿಯ ಸೆಷನ್ ಇಲ್ಲ',
    active: 'ಸಕ್ರಿಯ',
    inactive: 'ನಿಷ್ಕ್ರಿಯ',
    
    recentAlerts: 'ಇತ್ತೀಚಿನ ಎಚ್ಚರಿಕೆಗಳು',
    alert: 'ಎಚ್ಚರಿಕೆ',
    criticalThreatMessage: 'ನಿರ್ಣಾಯಕ ಬೆದರಿಕೆ: ತಕ್ಷಣ ಸಂಪರ್ಕ ಕಡಿತಗೊಳಿಸಿ',
    highRiskMessage: 'ಹೆಚ್ಚಿನ ಅಪಾಯ: ಸಂಭಾವ್ಯ ವಂಚನೆ ಪತ್ತೆಯಾಗಿದೆ',
    moderateRiskMessage: 'ಮಧ್ಯಮ: ಅನುಮಾನಾಸ್ಪದ ಚಟುವಟಿಕೆ',
    safeMessage: 'ಸುರಕ್ಷಿತ - ಯಾವುದೇ ಬೆದರಿಕೆಗಳಿಲ್ಲ',
    
    recentTranscript: 'ಇತ್ತೀಚಿನ ಪ್ರತಿಲಿಪಿ',
    
    actions: 'ಕ್ರಿಯೆಗಳು',
    endCall: 'ಕರೆ ಕೊನೆಗೊಳಿಸಿ',
    reportThreat: 'ಬೆದರಿಕೆ ವರದಿ ಮಾಡಿ',
    endCallConfirm: 'ಈ ಕರೆಯನ್ನು ಕೊನೆಗೊಳಿಸಲು ನೀವು ಖಚಿತವಾಗಿ ಬಯಸುವಿರಾ?',
    threatReported: 'ಬೆದರಿಕೆಯನ್ನು ಅಧಿಕಾರಿಗಳಿಗೆ ವರದಿ ಮಾಡಲಾಗಿದೆ',
    
    protectedBy: 'ಕಾವಲನ್ AI ಮೂಲಕ ರಕ್ಷಿಸಲಾಗಿದೆ',
    
    preferences: 'ಆದ್ಯತೆಗಳು',
    language: 'ಭಾಷೆ',
    selectLanguage: 'ಎಚ್ಚರಿಕೆಗಳು ಮತ್ತು ಇಂಟರ್ಫೇಸ್‌ಗಾಗಿ ನಿಮ್ಮ ಆದ್ಯತೆಯ ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ',
    alertVolume: 'ಎಚ್ಚರಿಕೆ ವಾಲ್ಯೂಮ್',
    adjustVolume: 'ಆಡಿಯೋ ಎಚ್ಚರಿಕೆಗಳ ವಾಲ್ಯೂಮ್ ಅನ್ನು ಹೊಂದಿಸಿ',
    stealthMode: 'ಸ್ಟೆಲ್ತ್ ಮೋಡ್',
    stealthModeHelp: 'ಕರೆಗಳ ಸಮಯದಲ್ಲಿ ದೃಶ್ಯ ಸೂಚಕಗಳನ್ನು ಮರೆಮಾಡಿ (ಎಚ್ಚರಿಕೆಗಳು ಇನ್ನೂ ಸಕ್ರಿಯವಾಗಿವೆ)',
    autoReport: 'ಸ್ವಯಂ-ವರದಿ',
    autoReportHelp: 'ಹೆಚ್ಚಿನ-ತೀವ್ರತೆಯ ಬೆದರಿಕೆಗಳನ್ನು ಸ್ವಯಂಚಾಲಿತವಾಗಿ ವರದಿ ಮಾಡಿ',
    savePreferences: 'ಆದ್ಯತೆಗಳನ್ನು ಉಳಿಸಿ',
    saving: 'ಉಳಿಸಲಾಗುತ್ತಿದೆ...',
    saved: 'ಉಳಿಸಲಾಗಿದೆ!',
    
    languageEnglish: 'English',
    languageHindi: 'हिन्दी',
    languageTamil: 'தமிழ்',
    languageTelugu: 'తెలుగు',
    languageMalayalam: 'മലയാളം',
    languageKannada: 'ಕನ್ನಡ',
  },
};

/**
 * Get translations for a specific language
 */
export function getTranslations(language: Language): Translations {
  return translations[language] || translations.en;
}

/**
 * Get translated string
 */
export function t(language: Language, key: keyof Translations): string {
  const trans = getTranslations(language);
  return trans[key] || translations.en[key];
}
