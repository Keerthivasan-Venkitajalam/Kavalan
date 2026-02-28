# Internationalization (i18n) Implementation

This directory contains the multi-language support implementation for the Kavalan browser extension.

## Supported Languages

The extension supports the following languages:

- **English** (`en`)
- **Hindi** (`hi`) - हिन्दी
- **Tamil** (`ta`) - தமிழ்
- **Telugu** (`te`) - తెలుగు
- **Malayalam** (`ml`) - മലയാളം
- **Kannada** (`kn`) - ಕನ್ನಡ

## Files

### `translations.ts`

Contains all translation strings for supported languages. Each language has a complete set of translations for:

- Application name and tagline
- Threat levels (low, moderate, high, critical)
- Detection status indicators
- Alert messages
- UI labels and buttons
- Preference settings
- Help text

### `useTranslation.ts`

React hook for accessing translations in UI components. Automatically loads the user's preferred language from storage and updates when the language preference changes.

**Usage:**

```typescript
import { useTranslation } from '../i18n/useTranslation';

function MyComponent() {
  const { t, language } = useTranslation();
  
  return <h1>{t.appName}</h1>;
}
```

### `alertMessages.ts`

Utility functions for getting localized alert messages based on threat level and user's preferred language.

**Functions:**

- `getLocalizedAlertMessage(threatLevel, language)` - Returns localized alert message
- `getLocalizedThreatLevel(threatLevel, language)` - Returns localized threat level text

**Usage:**

```typescript
import { getLocalizedAlertMessage } from '../i18n/alertMessages';

const message = getLocalizedAlertMessage('critical', 'hi');
// Returns: "गंभीर खतरा: तुरंत कॉल समाप्त करें"
```

## Adding a New Language

To add support for a new language:

1. Add the language code to the `Language` type in `translations.ts`
2. Add a complete translation object to the `translations` record
3. Update the `SUPPORTED_LANGUAGES` array in `PreferencesPanel.tsx`
4. Add the language name translations to all existing language objects

Example:

```typescript
// In translations.ts
export type Language = 'en' | 'hi' | 'ta' | 'te' | 'ml' | 'kn' | 'bn'; // Add 'bn' for Bengali

export const translations: Record<Language, Translations> = {
  // ... existing languages
  bn: {
    appName: 'কাভালান',
    appTagline: 'ডিজিটাল গ্রেপ্তার স্ক্যাম ডিটেক্টর',
    // ... complete all translation keys
  }
};
```

## Testing

The i18n implementation includes comprehensive tests:

### Property-Based Tests (`alert-localization.property.test.ts`)

Tests universal properties across all languages and threat levels:

- Non-empty messages for all combinations
- Different messages for different threat levels
- Consistency of messages
- Translation completeness
- Semantic preservation across languages

Run with: `npm test -- src/i18n/__tests__/alert-localization.property.test.ts`

### Unit Tests (`translations.test.ts`)

Tests specific examples and edge cases:

- Correct translations for each language
- Fallback to English for unsupported languages
- Translation completeness
- Alert message distinctness
- UI text consistency

Run with: `npm test -- src/i18n/__tests__/translations.test.ts`

## Architecture

The i18n system follows these principles:

1. **Centralized Translations**: All translations are in one place (`translations.ts`)
2. **Type Safety**: TypeScript ensures all translation keys exist
3. **Fallback Support**: Defaults to English if a language is not supported
4. **React Integration**: Custom hook for easy use in React components
5. **Storage Integration**: Reads user's language preference from Chrome storage
6. **Real-time Updates**: Listens for language changes and updates UI automatically

## Requirements Validation

This implementation validates **Requirement 6.5**:

> THE Browser_Extension SHALL display alerts in the user's preferred language

The implementation ensures:

- ✅ Alerts are displayed in the user's configured language
- ✅ All 6 supported languages have complete translations
- ✅ Alert messages are localized based on threat level
- ✅ UI updates automatically when language preference changes
- ✅ Fallback to English for unsupported languages
- ✅ Property-based tests validate correctness across all combinations
