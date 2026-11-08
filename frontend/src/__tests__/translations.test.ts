import { describe, it, expect } from 'vitest';
import { translations, Language } from '../i18n/translations';

describe('Trilingual Completeness and Parity', () => {
  const enKeys = Object.keys(translations.en).sort();
  const mrKeys = Object.keys(translations.mr).sort();
  const hiKeys = Object.keys(translations.hi).sort();

  it('contains at least 30 comprehensive translation keys in English', () => {
    expect(enKeys.length).toBeGreaterThanOrEqual(30);
  });

  it('maintains strict key parity between English and Marathi dictionaries', () => {
    expect(mrKeys).toEqual(enKeys);
  });

  it('maintains strict key parity between English and Hindi dictionaries', () => {
    expect(hiKeys).toEqual(enKeys);
  });

  it.each(['en', 'mr', 'hi'] as Language[])('contains non-empty, meaningful strings for all %s keys', (lang) => {
    const dict = translations[lang];
    for (const [key, value] of Object.entries(dict)) {
      expect(typeof value).toBe('string');
      expect(value.trim().length, `Empty translation for key "${key}" in language "${lang}"`).toBeGreaterThan(0);
    }
  });
});
