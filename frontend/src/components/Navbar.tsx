import React from 'react';
import { Language, translations } from '../i18n/translations';
import { UserProfile } from '../api/client';

interface NavbarProps {
  user: UserProfile | null;
  currentLang: Language;
  onLanguageChange: (l: Language) => void;
  onLogout: () => void;
  selectedFlatId?: string;
  onSelectFlat?: (id: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  currentLang,
  onLanguageChange,
  onLogout,
  selectedFlatId,
  onSelectFlat,
}) => {
  const t = translations[currentLang];

  return (
    <header style={{
      background: '#ffffff',
      borderBottom: '1px solid var(--border)',
      position: 'sticky',
      top: 0,
      zIndex: 40,
      padding: '0.75rem 1rem'
    }}>
      <div style={{
        maxWidth: '1000px',
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.5rem'
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'var(--primary)',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            fontSize: '1.1rem'
          }}>
            T1
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-main)', lineHeight: 1.2 }}>
              {t.app_title}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Company A, Pune
            </div>
          </div>
        </div>

        {/* Controls: Flat selector, Language, Logout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {user && user.flats && user.flats.length > 0 && onSelectFlat && (
            <select
              value={selectedFlatId}
              onChange={(e) => onSelectFlat(e.target.value)}
              style={{
                padding: '0.35rem 0.6rem',
                borderRadius: '6px',
                border: '1px solid var(--border)',
                background: '#f1f5f9',
                fontWeight: 600,
                fontSize: '0.85rem'
              }}
            >
              {user.flats.map((f) => (
                <option key={f.flat_id} value={f.flat_id}>
                  {f.flat_number} ({f.member_type})
                </option>
              ))}
            </select>
          )}

          {/* Language Switcher */}
          <div style={{ display: 'flex', background: '#f1f5f9', borderRadius: '6px', padding: '2px' }}>
            {(['en', 'mr', 'hi'] as Language[]).map((lang) => (
              <button
                key={lang}
                onClick={() => onLanguageChange(lang)}
                style={{
                  border: 'none',
                  background: currentLang === lang ? '#ffffff' : 'transparent',
                  color: currentLang === lang ? 'var(--primary)' : 'var(--text-muted)',
                  fontWeight: currentLang === lang ? 700 : 500,
                  fontSize: '0.78rem',
                  padding: '3px 7px',
                  borderRadius: '4px',
                  boxShadow: currentLang === lang ? '0 1px 2px rgba(0,0,0,0.08)' : 'none'
                }}
              >
                {lang === 'en' ? 'EN' : lang === 'mr' ? 'मराठी' : 'हिंदी'}
              </button>
            ))}
          </div>

          {user && (
            <button
              onClick={onLogout}
              style={{
                border: '1px solid var(--border)',
                background: '#ffffff',
                color: 'var(--text-muted)',
                fontSize: '0.8rem',
                padding: '0.35rem 0.65rem',
                borderRadius: '6px',
                fontWeight: 500
              }}
            >
              {t.logout}
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
