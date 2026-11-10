import React, { useState } from 'react';
import { api, UserProfile } from '../api/client';
import { Language, translations } from '../i18n/translations';

interface LoginPageProps {
  lang: Language;
  onLoginSuccess: (user: UserProfile) => void;
  onLanguageChange?: (lang: Language) => void;
}

export type LoginTab = 'DEMO' | 'PASSWORD' | 'OTP';

export const LoginPage: React.FC<LoginPageProps> = ({ lang, onLoginSuccess, onLanguageChange }) => {
  const t = translations[lang];
  const [activeTab, setActiveTab] = useState<LoginTab>('DEMO');

  // Password Login state
  const [passwordPhone, setPasswordPhone] = useState('9876543210');
  const [password, setPassword] = useState('123456');

  // OTP Login state
  const [phone, setPhone] = useState('9876543210');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'PHONE' | 'OTP'>('PHONE');
  const [demoHint, setDemoHint] = useState<string | null>(null);

  // Common UI state
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 1-Click Demo Login
  const handleQuickLogin = async (presetPhone: string) => {
    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      // First try direct password login (fastest, 1 roundtrip)
      try {
        const res = await api.loginWithPassword(presetPhone, '123456');
        onLoginSuccess(res.user);
        return;
      } catch (pwdErr) {
        // Fallback to OTP request + verify
        await api.requestOtp(presetPhone);
        const res = await api.verifyOtp(presetPhone, '123456');
        onLoginSuccess(res.user);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Password Form Submit
  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanPhone = passwordPhone.trim();
    const cleanPassword = password.trim();
    if (!cleanPhone || !cleanPassword) {
      setErrorMsg('Please enter both mobile number and password.');
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await api.loginWithPassword(cleanPhone, cleanPassword);
      onLoginSuccess(res.user);
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed. For demo accounts, use password 123456.');
    } finally {
      setLoading(false);
    }
  };

  // OTP Request
  const handleRequestOtp = async (inputPhone?: string) => {
    const targetPhone = (inputPhone || phone).trim();
    if (!targetPhone) {
      setErrorMsg('Please enter a valid 10-digit mobile number.');
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await api.requestOtp(targetPhone);
      setPhone(targetPhone);
      setDemoHint(res.demo_hint || null);
      setStep('OTP');
      if (res.demo_hint) {
        setSuccessMsg(res.demo_hint);
      } else {
        setSuccessMsg('OTP code 123456 generated for evaluation.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to request OTP');
    } finally {
      setLoading(false);
    }
  };

  // OTP Verify
  const handleVerifyOtp = async (inputOtp?: string) => {
    const targetOtp = (inputOtp || otp).trim();
    if (!targetOtp) {
      setErrorMsg('Please enter the 6-digit OTP code.');
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.verifyOtp(phone.trim(), targetOtp);
      onLoginSuccess(res.user);
    } catch (err: any) {
      setErrorMsg(err.message || 'Invalid OTP code. Please use 123456 or try Password Login.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      maxWidth: '520px',
      margin: '2rem auto',
      padding: '1.75rem',
      background: '#ffffff',
      borderRadius: '12px',
      border: '1px solid var(--border)',
      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)'
    }}>
      {/* Top Header & Branding */}
      <div style={{ textAlign: 'center', marginBottom: '1.25rem' }}>
        <div style={{
          width: '52px',
          height: '52px',
          background: 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)',
          color: '#ffffff',
          borderRadius: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 800,
          fontSize: '1.5rem',
          margin: '0 auto 0.75rem auto',
          boxShadow: '0 4px 6px -1px rgba(30, 64, 175, 0.3)'
        }}>
          T1
        </div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-main)', margin: '0 0 0.25rem 0' }}>
          {t.app_title}
        </h1>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
          {t.tagline}
        </p>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.4rem',
          marginTop: '0.5rem',
          background: '#f1f5f9',
          padding: '0.2rem 0.65rem',
          borderRadius: '999px',
          fontSize: '0.72rem',
          color: '#475569',
          fontWeight: 600
        }}>
          <span>📍 Pune, MH</span>
          <span>•</span>
          <span>2,400 Flats</span>
          <span>•</span>
          <span>28 Towers</span>
          <span>•</span>
          <span>4 Gates</span>
        </div>
      </div>

      {/* Language Switcher if provided */}
      {onLanguageChange && (
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', background: '#f1f5f9', borderRadius: '8px', padding: '2px' }}>
            {(['en', 'mr', 'hi'] as Language[]).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => onLanguageChange(l)}
                style={{
                  border: 'none',
                  background: lang === l ? '#ffffff' : 'transparent',
                  color: lang === l ? 'var(--primary)' : 'var(--text-muted)',
                  fontWeight: lang === l ? 700 : 500,
                  fontSize: '0.78rem',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  boxShadow: lang === l ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                  cursor: 'pointer'
                }}
              >
                {l === 'en' ? 'English' : l === 'mr' ? 'मराठी' : 'हिंदी'}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Login Mode Selector Tabs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: '4px',
        background: '#f1f5f9',
        borderRadius: '10px',
        padding: '3px',
        marginBottom: '1.25rem'
      }}>
        <button
          type="button"
          onClick={() => { setActiveTab('DEMO'); setErrorMsg(null); }}
          style={{
            border: 'none',
            background: activeTab === 'DEMO' ? '#ffffff' : 'transparent',
            color: activeTab === 'DEMO' ? 'var(--primary)' : 'var(--text-muted)',
            fontWeight: activeTab === 'DEMO' ? 700 : 600,
            fontSize: '0.82rem',
            padding: '0.55rem 0.25rem',
            borderRadius: '8px',
            cursor: 'pointer',
            boxShadow: activeTab === 'DEMO' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.3rem'
          }}
        >
          <span>⚡</span>
          <span>{t.login_mode_demo}</span>
        </button>

        <button
          type="button"
          onClick={() => { setActiveTab('PASSWORD'); setErrorMsg(null); }}
          style={{
            border: 'none',
            background: activeTab === 'PASSWORD' ? '#ffffff' : 'transparent',
            color: activeTab === 'PASSWORD' ? 'var(--primary)' : 'var(--text-muted)',
            fontWeight: activeTab === 'PASSWORD' ? 700 : 600,
            fontSize: '0.82rem',
            padding: '0.55rem 0.25rem',
            borderRadius: '8px',
            cursor: 'pointer',
            boxShadow: activeTab === 'PASSWORD' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.3rem'
          }}
        >
          <span>🔑</span>
          <span>{t.login_mode_password}</span>
        </button>

        <button
          type="button"
          onClick={() => { setActiveTab('OTP'); setErrorMsg(null); }}
          style={{
            border: 'none',
            background: activeTab === 'OTP' ? '#ffffff' : 'transparent',
            color: activeTab === 'OTP' ? 'var(--primary)' : 'var(--text-muted)',
            fontWeight: activeTab === 'OTP' ? 700 : 600,
            fontSize: '0.82rem',
            padding: '0.55rem 0.25rem',
            borderRadius: '8px',
            cursor: 'pointer',
            boxShadow: activeTab === 'OTP' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.3rem'
          }}
        >
          <span>📲</span>
          <span>{t.login_mode_otp}</span>
        </button>
      </div>

      {/* Common Alerts */}
      {errorMsg && (
        <div style={{
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
          padding: '0.65rem 0.85rem',
          color: '#b91c1c',
          fontSize: '0.82rem',
          fontWeight: 600,
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem'
        }}>
          <span>⚠️</span>
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div style={{
          background: '#f0fdf4',
          border: '1px solid #bbf7d0',
          borderRadius: '8px',
          padding: '0.65rem 0.85rem',
          color: '#166534',
          fontSize: '0.82rem',
          fontWeight: 600,
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem'
        }}>
          <span>💡</span>
          <span>{successMsg}</span>
        </div>
      )}

      {/* TAB 1: 1-CLICK DEMO ROLES */}
      {activeTab === 'DEMO' && (
        <div>
          <div style={{
            fontSize: '0.78rem',
            fontWeight: 700,
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            marginBottom: '0.75rem',
            letterSpacing: '0.05em'
          }}>
            Select a Role to Sign In (1-Click)
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {/* Resident Owner */}
            <button
              type="button"
              onClick={() => handleQuickLogin('9876543210')}
              disabled={loading}
              style={{
                background: '#f0fdf4',
                border: '1.5px solid #bbf7d0',
                padding: '0.75rem 0.9rem',
                borderRadius: '8px',
                textAlign: 'left',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1,
                transition: 'transform 0.1s ease, box-shadow 0.1s ease'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#166534' }}>
                    Neeraj Kulkarni
                  </span>
                  <span style={{
                    fontSize: '0.68rem',
                    background: '#dcfce7',
                    color: '#15803d',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: 700
                  }}>
                    OWNER • T07-1203
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: '#15803d', marginTop: '0.15rem' }}>
                  Paid in full (₹7,475) • 0 overdue • Visitor approvals & amenities
                </div>
              </div>
              <span style={{
                fontSize: '0.8rem',
                fontWeight: 800,
                color: '#166534',
                background: '#ffffff',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid #bbf7d0'
              }}>
                Login →
              </span>
            </button>

            {/* Resident Tenant */}
            <button
              type="button"
              onClick={() => handleQuickLogin('9876543211')}
              disabled={loading}
              style={{
                background: '#fef2f2',
                border: '1.5px solid #fecaca',
                padding: '0.75rem 0.9rem',
                borderRadius: '8px',
                textAlign: 'left',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#991b1b' }}>
                    Swati Joshi
                  </span>
                  <span style={{
                    fontSize: '0.68rem',
                    background: '#fee2e2',
                    color: '#b91c1c',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: 700
                  }}>
                    TENANT • T12-0408
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: '#b91c1c', marginTop: '0.15rem' }}>
                  Due: ₹6,370 (47d overdue) • 1 active water leak complaint
                </div>
              </div>
              <span style={{
                fontSize: '0.8rem',
                fontWeight: 800,
                color: '#991b1b',
                background: '#ffffff',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid #fecaca'
              }}>
                Login →
              </span>
            </button>

            {/* Managing Committee */}
            <button
              type="button"
              onClick={() => handleQuickLogin('9876543212')}
              disabled={loading}
              style={{
                background: '#f8fafc',
                border: '1.5px solid var(--border)',
                padding: '0.75rem 0.9rem',
                borderRadius: '8px',
                textAlign: 'left',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.9rem', color: 'var(--text-main)' }}>
                    Aamir Shaikh
                  </span>
                  <span style={{
                    fontSize: '0.68rem',
                    background: '#e2e8f0',
                    color: '#334155',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: 700
                  }}>
                    COMMITTEE • T21-1601
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                  Dues ageing audit, notice publisher & society governance
                </div>
              </div>
              <span style={{
                fontSize: '0.8rem',
                fontWeight: 800,
                color: 'var(--primary)',
                background: '#ffffff',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid var(--border)'
              }}>
                Login →
              </span>
            </button>

            {/* Security Guard */}
            <button
              type="button"
              onClick={() => handleQuickLogin('9876543213')}
              disabled={loading}
              style={{
                background: '#eff6ff',
                border: '1.5px solid #bfdbfe',
                padding: '0.75rem 0.9rem',
                borderRadius: '8px',
                textAlign: 'left',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#1e40af' }}>
                    Ramesh Shinde
                  </span>
                  <span style={{
                    fontSize: '0.68rem',
                    background: '#dbeafe',
                    color: '#1d4ed8',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: 700
                  }}>
                    GUARD • GATE 1
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: '#2563eb', marginTop: '0.15rem' }}>
                  Gate terminal: Visitor entry, offline queue & guest QR codes
                </div>
              </div>
              <span style={{
                fontSize: '0.8rem',
                fontWeight: 800,
                color: '#1e40af',
                background: '#ffffff',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid #bfdbfe'
              }}>
                Login →
              </span>
            </button>

            {/* Accounts Officer */}
            <button
              type="button"
              onClick={() => handleQuickLogin('9876543214')}
              disabled={loading}
              style={{
                background: '#f5f3ff',
                border: '1.5px solid #ddd6fe',
                padding: '0.75rem 0.9rem',
                borderRadius: '8px',
                textAlign: 'left',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#5b21b6' }}>
                    Suresh Nair
                  </span>
                  <span style={{
                    fontSize: '0.68rem',
                    background: '#ede9fe',
                    color: '#6d28d9',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: 700
                  }}>
                    ACCOUNTS OFFICER
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: '#6d28d9', marginTop: '0.15rem' }}>
                  Bank statement CSV auto-match & ledger posting workspace
                </div>
              </div>
              <span style={{
                fontSize: '0.8rem',
                fontWeight: 800,
                color: '#5b21b6',
                background: '#ffffff',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid #ddd6fe'
              }}>
                Login →
              </span>
            </button>

            {/* Help Desk Staff */}
            <button
              type="button"
              onClick={() => handleQuickLogin('9876543220')}
              disabled={loading}
              style={{
                background: '#fffbeb',
                border: '1.5px solid #fde68a',
                padding: '0.75rem 0.9rem',
                borderRadius: '8px',
                textAlign: 'left',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#92400e' }}>
                    Ramesh Patil
                  </span>
                  <span style={{
                    fontSize: '0.68rem',
                    background: '#fef3c7',
                    color: '#b45309',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: 700
                  }}>
                    HELP DESK STAFF
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: '#b45309', marginTop: '0.15rem' }}>
                  SLA ticket queue, AI incident classification & emergency alerts
                </div>
              </div>
              <span style={{
                fontSize: '0.8rem',
                fontWeight: 800,
                color: '#92400e',
                background: '#ffffff',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid #fde68a'
              }}>
                Login →
              </span>
            </button>
          </div>
        </div>
      )}

      {/* TAB 2: PASSWORD LOGIN */}
      {activeTab === 'PASSWORD' && (
        <form onSubmit={handlePasswordLogin}>
          <div style={{
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: '8px',
            padding: '0.75rem 0.85rem',
            marginBottom: '1rem',
            fontSize: '0.8rem',
            color: '#1e40af',
            lineHeight: 1.4
          }}>
            <div style={{ fontWeight: 700, marginBottom: '0.2rem' }}>
              💡 Direct Password Sign-In
            </div>
            <div>
              All demo users accept password <code style={{ background: '#dbeafe', padding: '1px 5px', borderRadius: '4px', fontWeight: 700 }}>123456</code> or <code style={{ background: '#dbeafe', padding: '1px 5px', borderRadius: '4px', fontWeight: 700 }}>demo123</code>. You can also enter any 10-digit mobile number.
            </div>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem', color: 'var(--text-muted)' }}>
              {t.enter_phone}
            </label>
            <input
              type="tel"
              value={passwordPhone}
              onChange={(e) => setPasswordPhone(e.target.value)}
              placeholder="e.g. 9876543210"
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '1rem',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                {t.password}
              </label>
              <button
                type="button"
                onClick={() => { setPasswordPhone('9876543210'); setPassword('123456'); }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--primary)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {t.autofill_demo_password}
              </button>
            </div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t.password_placeholder}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                fontSize: '1rem',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !passwordPhone || !password}
            style={{
              width: '100%',
              background: 'var(--primary)',
              color: '#ffffff',
              border: 'none',
              padding: '0.75rem',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '0.95rem',
              cursor: 'pointer',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Signing in...' : t.sign_in_with_password}
          </button>
        </form>
      )}

      {/* TAB 3: MOBILE OTP LOGIN */}
      {activeTab === 'OTP' && (
        <div>
          <div style={{
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
            borderRadius: '8px',
            padding: '0.75rem 0.85rem',
            marginBottom: '1rem',
            fontSize: '0.8rem',
            color: '#166534',
            lineHeight: 1.4
          }}>
            <div style={{ fontWeight: 700, marginBottom: '0.2rem' }}>
              📱 {t.demo_otp_banner}
            </div>
            <div>
              In evaluation mode, OTP generation is simulated. The code is fixed to <strong style={{ color: '#15803d' }}>123456</strong>.
            </div>
          </div>

          {step === 'PHONE' ? (
            <form onSubmit={(e) => { e.preventDefault(); handleRequestOtp(); }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem', color: 'var(--text-muted)' }}>
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
                    fontSize: '1rem',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              {/* Quick Preset Buttons */}
              <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Demo numbers:</span>
                <button
                  type="button"
                  onClick={() => setPhone('9876543210')}
                  style={{
                    background: '#f1f5f9',
                    border: '1px solid var(--border)',
                    borderRadius: '4px',
                    padding: '2px 6px',
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  9876543210 (Owner)
                </button>
                <button
                  type="button"
                  onClick={() => setPhone('9876543211')}
                  style={{
                    background: '#f1f5f9',
                    border: '1px solid var(--border)',
                    borderRadius: '4px',
                    padding: '2px 6px',
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  9876543211 (Tenant)
                </button>
              </div>

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
                  cursor: 'pointer',
                  opacity: loading ? 0.7 : 1
                }}
              >
                {loading ? 'Generating OTP...' : t.send_otp}
              </button>
            </form>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); handleVerifyOtp(); }}>
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                    {t.enter_otp} (Sent to {phone})
                  </label>
                  <button
                    type="button"
                    onClick={() => { setStep('PHONE'); setOtp(''); setErrorMsg(null); }}
                    style={{ background: 'none', border: 'none', color: 'var(--primary)', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
                  >
                    Change Number
                  </button>
                </div>

                {/* Big Visible Demo Code Box */}
                <div style={{
                  background: '#f0fdf4',
                  border: '1.5px solid #86efac',
                  borderRadius: '8px',
                  padding: '0.65rem 0.85rem',
                  marginBottom: '0.75rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: '#166534', fontWeight: 700 }}>
                      DEMO OTP CODE:
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 900, color: '#15803d', letterSpacing: '0.15em' }}>
                      123456
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setOtp('123456')}
                    style={{
                      background: '#15803d',
                      color: '#ffffff',
                      border: 'none',
                      padding: '0.35rem 0.65rem',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    {t.autofill_demo_otp}
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
                    fontSize: '1.3rem',
                    textAlign: 'center',
                    letterSpacing: '0.4em',
                    fontWeight: 700,
                    boxSizing: 'border-box'
                  }}
                />

                {demoHint && (
                  <div style={{ fontSize: '0.75rem', color: '#15803d', marginTop: '0.4rem', textAlign: 'center', fontWeight: 600 }}>
                    💡 {demoHint}
                  </div>
                )}
              </div>

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
                  cursor: 'pointer',
                  opacity: loading ? 0.7 : 1
                }}
              >
                {loading ? 'Verifying...' : t.verify_otp}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
};
