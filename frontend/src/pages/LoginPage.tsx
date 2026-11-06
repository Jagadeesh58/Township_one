import React, { useState } from 'react';
import { api, UserProfile } from '../api/client';
import { Language, translations } from '../i18n/translations';

interface LoginPageProps {
  lang: Language;
  onLoginSuccess: (user: UserProfile) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ lang, onLoginSuccess }) => {
  const t = translations[lang];
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'PHONE' | 'OTP'>('PHONE');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [demoHint, setDemoHint] = useState<string | null>(null);

  const handleRequestOtp = async (inputPhone?: string) => {
    const targetPhone = inputPhone || phone;
    if (!targetPhone) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.requestOtp(targetPhone);
      setPhone(targetPhone);
      setDemoHint(res.demo_hint || 'Demo OTP: 123456');
      setStep('OTP');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to request OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (inputOtp?: string) => {
    const targetOtp = inputOtp || otp;
    if (!targetOtp) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.verifyOtp(phone, targetOtp);
      onLoginSuccess(res.user);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to verify OTP');
    } finally {
      setLoading(false);
    }
  };

  // Quick 1-click login for reviewer convenience
  const handleQuickLogin = async (presetPhone: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      await api.requestOtp(presetPhone);
      const res = await api.verifyOtp(presetPhone, '123456');
      onLoginSuccess(res.user);
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      maxWidth: '460px',
      margin: '2rem auto',
      padding: '1.5rem',
      background: '#ffffff',
      borderRadius: 'var(--radius)',
      border: '1px solid var(--border)',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
    }}>
      <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
        <div style={{
          width: '48px',
          height: '48px',
          background: 'var(--primary)',
          color: '#fff',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 800,
          fontSize: '1.4rem',
          margin: '0 auto 0.75rem auto'
        }}>
          T1
        </div>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-main)' }}>
          {t.sign_in}
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
          {t.tagline}
        </p>
      </div>

      {step === 'PHONE' ? (
        <form onSubmit={(e) => { e.preventDefault(); handleRequestOtp(); }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-muted)' }}>
              {t.enter_phone}
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="e.g. 9876543210"
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '1rem'
              }}
            />
          </div>
          {errorMsg && (
            <div style={{ color: 'var(--danger)', fontSize: '0.82rem', marginBottom: '1rem', fontWeight: 500 }}>
              {errorMsg}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || !phone}
            style={{
              width: '100%',
              background: 'var(--primary)',
              color: '#ffffff',
              border: 'none',
              padding: '0.75rem',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '0.95rem',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Sending...' : t.send_otp}
          </button>
        </form>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); handleVerifyOtp(); }}>
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                {t.enter_otp}
              </label>
              <button
                type="button"
                onClick={() => setStep('PHONE')}
                style={{ background: 'none', border: 'none', color: 'var(--primary)', fontSize: '0.8rem', fontWeight: 500 }}
              >
                Change Number
              </button>
            </div>
            <input
              type="text"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              placeholder="123456"
              maxLength={6}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '1.2rem',
                textAlign: 'center',
                letterSpacing: '0.4em',
                fontWeight: 700
              }}
            />
            {demoHint && (
              <div style={{ fontSize: '0.75rem', color: '#15803d', marginTop: '0.4rem', textAlign: 'center', fontWeight: 600 }}>
                💡 {demoHint}
              </div>
            )}
          </div>
          {errorMsg && (
            <div style={{ color: 'var(--danger)', fontSize: '0.82rem', marginBottom: '1rem', fontWeight: 500 }}>
              {errorMsg}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || otp.length < 6}
            style={{
              width: '100%',
              background: 'var(--primary)',
              color: '#ffffff',
              border: 'none',
              padding: '0.75rem',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '0.95rem',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Verifying...' : t.verify_otp}
          </button>
        </form>
      )}

      {/* Reviewer Quick Sign-In Presets */}
      <div style={{ marginTop: '2rem', borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.75rem', letterSpacing: '0.05em' }}>
          {t.demo_accounts}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <button
            onClick={() => handleQuickLogin('9876543211')}
            disabled={loading}
            style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              padding: '0.5rem 0.75rem',
              borderRadius: '6px',
              textAlign: 'left',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#991b1b' }}>
                Swati Joshi (Tenant • T12-0408)
              </div>
              <div style={{ fontSize: '0.72rem', color: '#b91c1c' }}>
                Due: ₹6,370 (47d overdue) • 1 water leak complaint
              </div>
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#991b1b' }}>Login →</span>
          </button>

          <button
            onClick={() => handleQuickLogin('9876543210')}
            disabled={loading}
            style={{
              background: '#f0fdf4',
              border: '1px solid #bbf7d0',
              padding: '0.5rem 0.75rem',
              borderRadius: '6px',
              textAlign: 'left',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#166534' }}>
                Neeraj Kulkarni (Owner • T07-1203)
              </div>
              <div style={{ fontSize: '0.72rem', color: '#15803d' }}>
                Paid in full (₹7,475) • 0 overdue
              </div>
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#166534' }}>Login →</span>
          </button>

          <button
            onClick={() => handleQuickLogin('9876543212')}
            disabled={loading}
            style={{
              background: '#f8fafc',
              border: '1px solid var(--border)',
              padding: '0.5rem 0.75rem',
              borderRadius: '6px',
              textAlign: 'left',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-main)' }}>
                Aamir Shaikh (Owner • T21-1601)
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Partial Paid (₹5,000 / ₹10,660) • 18d overdue
              </div>
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)' }}>Login →</span>
          </button>

          <button
            onClick={() => handleQuickLogin('9876543220')}
            disabled={loading}
            style={{
              background: '#f1f5f9',
              border: '1px solid var(--border)',
              padding: '0.45rem 0.75rem',
              borderRadius: '6px',
              textAlign: 'left',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '0.82rem'
            }}
          >
            <span style={{ fontWeight: 600 }}>Ramesh Patil (Help Desk Staff)</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Login →</span>
          </button>
        </div>
      </div>
    </div>
  );
};
