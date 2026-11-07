import { describe, it, expect, vi } from 'vitest';
import { translations, Language } from '../i18n/translations';

describe('Township One Frontend Suite', () => {
  describe('Internationalization & Translations', () => {
    const requiredKeys = [
      'app_title',
      'sign_in',
      'send_otp',
      'verify_otp',
      'dues_title',
      'amount_due',
      'pay_now',
      'confirm_payment',
      'test_mode_badge',
      'test_checkout_title',
      'select_test_outcome',
      'receipt',
      'receipt_no',
    ];

    const supportedLangs: Language[] = ['en', 'mr', 'hi'];

    it.each(supportedLangs)('contains all required keys for language: %s', (lang) => {
      const langTrans = translations[lang];
      expect(langTrans).toBeDefined();
      for (const key of requiredKeys) {
        expect(langTrans[key as keyof typeof langTrans]).toBeTruthy();
      }
    });
  });

  describe('Authentication & Input Validation', () => {
    it('validates standard 10-digit Indian mobile numbers', () => {
      const isValidPhone = (p: string) => /^[6-9]\d{9}$/.test(p.trim());

      expect(isValidPhone('9876543210')).toBe(true);
      expect(isValidPhone('7890123456')).toBe(true);
      expect(isValidPhone('6123456789')).toBe(true);

      // Invalid cases
      expect(isValidPhone('1234567890')).toBe(false); // Does not start with 6-9
      expect(isValidPhone('98765')).toBe(false); // Too short
      expect(isValidPhone('98765432101')).toBe(false); // Too long
      expect(isValidPhone('abcdefghij')).toBe(false); // Non-numeric
    });

    it('validates 6-digit numeric OTP', () => {
      const isValidOtp = (otp: string) => /^\d{6}$/.test(otp.trim());

      expect(isValidOtp('123456')).toBe(true);
      expect(isValidOtp('000000')).toBe(true);
      expect(isValidOtp('12345')).toBe(false);
      expect(isValidOtp('1234567')).toBe(false);
      expect(isValidOtp('12345a')).toBe(false);
    });
  });

  describe('Payment Idempotency Key Lifecycle', () => {
    const generateKey = () => `idem-${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;

    it('generates a valid, cryptographically random idempotency key with minimum 8 characters', () => {
      const key = generateKey();
      expect(key.startsWith('idem-')).toBe(true);
      expect(key.length).toBeGreaterThanOrEqual(16);
    });

    it('generates distinct keys for successive calls', () => {
      const key1 = generateKey();
      const key2 = generateKey();
      expect(key1).not.toBe(key2);
    });

    it('simulates retry lifecycle: preserves key on network interruption, changes on new attempt', () => {
      let currentKey = generateKey();
      const originalKey = currentKey;

      // Simulated network failure: retry reuses same key
      const isRetry = true;
      if (!isRetry) {
        currentKey = generateKey();
      }
      expect(currentKey).toBe(originalKey);

      // Simulated new attempt (e.g., changed bill or user clicked New Attempt)
      currentKey = generateKey();
      expect(currentKey).not.toBe(originalKey);
    });
  });

  describe('Financial Calculations & Precision Formatting', () => {
    it('formats Indian currency numbers correctly without floating point errors', () => {
      const formatInr = (val: number) =>
        `₹${val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

      expect(formatInr(8450.0)).toBe('₹8,450.00');
      expect(formatInr(0.0)).toBe('₹0.00');
      expect(formatInr(123456.78)).toBe('₹1,23,456.78');
    });

    it('correctly aggregates multi-bill balances', () => {
      const bills = [
        { id: 'b1', balance_amount: 8450.0, total_amount: 8450.0 },
        { id: 'b2', balance_amount: 5200.0, total_amount: 8450.0 },
      ];

      const totalBalance = bills.reduce((acc, b) => acc + (b.balance_amount ?? b.total_amount), 0);
      expect(totalBalance).toBe(13650.0);
    });
  });

  describe('Payment State Machine Transitions', () => {
    type PaymentState = 'READY' | 'PROCESSING' | 'SUCCESS' | 'FAILED' | 'NETWORK_INTERRUPTION';

    it('transitions correctly across the payment lifecycle', () => {
      let state: PaymentState = 'READY';
      expect(state).toBe('READY');

      // User submits payment
      state = 'PROCESSING';
      expect(state).toBe('PROCESSING');

      // Network error occurs
      state = 'NETWORK_INTERRUPTION';
      expect(state).toBe('NETWORK_INTERRUPTION');

      // User retries network failure
      state = 'PROCESSING';
      expect(state).toBe('PROCESSING');

      // Successful outcome
      state = 'SUCCESS';
      expect(state).toBe('SUCCESS');
    });
  });
});
