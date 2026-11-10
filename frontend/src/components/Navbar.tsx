import React from 'react';
import { Language, translations } from '../i18n/translations';
import { UserProfile } from '../api/client';
import { NotificationBell } from './NotificationBell';

export type NavTab = 'home' | 'complaints' | 'amenities' | 'accounts' | 'helpdesk' | 'guard' | 'committee' | 'notices' | 'notice-management';

interface NavbarProps {
  user: UserProfile | null;
  currentLang: Language;
  onLanguageChange: (l: Language) => void;
  onLogout: () => void;
  selectedFlatId?: string;
  onSelectFlat?: (id: string) => void;
  activeTab?: NavTab;
  onTabChange?: (tab: NavTab) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  currentLang,
  onLanguageChange,
  onLogout,
  selectedFlatId,
  onSelectFlat,
  activeTab = 'home',
  onTabChange,
}) => {
  const t = translations[currentLang];

  const userRoles = user?.roles?.map((r) => r.role_code) || [];
  const isAccounts = userRoles.includes('ACCOUNTS') || userRoles.includes('ADMIN');
  const isHelpdesk = userRoles.includes('HELPDESK') || userRoles.includes('ADMIN') || userRoles.includes('COMMITTEE') || userRoles.includes('MANAGEMENT');
  const isGuard = userRoles.includes('GUARD') || userRoles.includes('ADMIN');
  const isCommittee = userRoles.includes('COMMITTEE') || userRoles.includes('ADMIN') || userRoles.includes('MANAGEMENT');
  const hasFlats = user?.flats && user.flats.length > 0;

  return (
    <header style={{
      background: '#ffffff',
      borderBottom: '1px solid var(--border)',
      position: 'sticky',
      top: 0,
      zIndex: 40,
      padding: '0.6rem 1rem'
    }}>
      <div style={{
        maxWidth: '1100px',
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.6rem'
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
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
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Company A, Pune
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        {user && onTabChange && (
          <nav style={{ display: 'flex', gap: '0.3rem', alignItems: 'center', flexWrap: 'wrap' }}>
            {hasFlats && (
              <>
                <button
                  onClick={() => onTabChange('home')}
                  style={{
                    border: 'none',
                    background: activeTab === 'home' ? '#f1f5f9' : 'transparent',
                    color: activeTab === 'home' ? 'var(--primary)' : 'var(--text-muted)',
                    fontWeight: activeTab === 'home' ? 700 : 500,
                    padding: '0.35rem 0.65rem',
                    borderRadius: '6px',
                    fontSize: '0.82rem',
                    cursor: 'pointer',
                  }}
                >
                  🏠 {t.home}
                </button>
                <button
                  onClick={() => onTabChange('amenities')}
                  style={{
                    border: 'none',
                    background: activeTab === 'amenities' ? '#f1f5f9' : 'transparent',
                    color: activeTab === 'amenities' ? 'var(--primary)' : 'var(--text-muted)',
                    fontWeight: activeTab === 'amenities' ? 700 : 500,
                    padding: '0.35rem 0.65rem',
                    borderRadius: '6px',
                    fontSize: '0.82rem',
                    cursor: 'pointer',
                  }}
                >
                  🏊 {t.amenities}
                </button>
                <button
                  onClick={() => onTabChange('notices')}
                  style={{
                    border: 'none',
                    background: activeTab === 'notices' ? '#f1f5f9' : 'transparent',
                    color: activeTab === 'notices' ? 'var(--primary)' : 'var(--text-muted)',
                    fontWeight: activeTab === 'notices' ? 700 : 500,
                    padding: '0.35rem 0.65rem',
                    borderRadius: '6px',
                    fontSize: '0.82rem',
                    cursor: 'pointer',
                  }}
                >
                  📢 {t.notices}
                </button>
                <button
                  onClick={() => onTabChange('complaints')}
                  style={{
                    border: 'none',
                    background: activeTab === 'complaints' ? '#f1f5f9' : 'transparent',
                    color: activeTab === 'complaints' ? 'var(--primary)' : 'var(--text-muted)',
                    fontWeight: activeTab === 'complaints' ? 700 : 500,
                    padding: '0.35rem 0.65rem',
                    borderRadius: '6px',
                    fontSize: '0.82rem',
                    cursor: 'pointer',
                  }}
                >
                  🛠️ {t.complaints}
                </button>
              </>
            )}

            {isGuard && (
              <button
                onClick={() => onTabChange('guard')}
                style={{
                  border: 'none',
                  background: activeTab === 'guard' ? '#f1f5f9' : 'transparent',
                  color: activeTab === 'guard' ? 'var(--primary)' : 'var(--text-muted)',
                  fontWeight: activeTab === 'guard' ? 700 : 500,
                  padding: '0.35rem 0.65rem',
                  borderRadius: '6px',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                }}
              >
                🛡️ {t.guard_terminal}
              </button>
            )}

            {isHelpdesk && (
              <button
                onClick={() => onTabChange('helpdesk')}
                style={{
                  border: 'none',
                  background: activeTab === 'helpdesk' ? '#f1f5f9' : 'transparent',
                  color: activeTab === 'helpdesk' ? 'var(--primary)' : 'var(--text-muted)',
                  fontWeight: activeTab === 'helpdesk' ? 700 : 500,
                  padding: '0.35rem 0.65rem',
                  borderRadius: '6px',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                }}
              >
                📋 {t.helpdesk_queue}
              </button>
            )}

            {isAccounts && (
              <button
                onClick={() => onTabChange('accounts')}
                style={{
                  border: 'none',
                  background: activeTab === 'accounts' ? '#f1f5f9' : 'transparent',
                  color: activeTab === 'accounts' ? 'var(--primary)' : 'var(--text-muted)',
                  fontWeight: activeTab === 'accounts' ? 700 : 500,
                  padding: '0.35rem 0.65rem',
                  borderRadius: '6px',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                }}
              >
                💼 {t.accounts_workspace}
              </button>
            )}

            {isCommittee && (
              <button
                onClick={() => onTabChange('committee')}
                style={{
                  border: 'none',
                  background: activeTab === 'committee' ? '#f1f5f9' : 'transparent',
                  color: activeTab === 'committee' ? 'var(--primary)' : 'var(--text-muted)',
                  fontWeight: activeTab === 'committee' ? 700 : 500,
                  padding: '0.35rem 0.65rem',
                  borderRadius: '6px',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                }}
              >
                🏛️ {t.committee_dashboard}
              </button>
            )}

            {isCommittee && (
              <button
                onClick={() => onTabChange('notice-management')}
                style={{
                  border: 'none',
                  background: activeTab === 'notice-management' ? '#f1f5f9' : 'transparent',
                  color: activeTab === 'notice-management' ? 'var(--primary)' : 'var(--text-muted)',
                  fontWeight: activeTab === 'notice-management' ? 700 : 500,
                  padding: '0.35rem 0.65rem',
                  borderRadius: '6px',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                }}
              >
                📝 {t.manage_notices}
              </button>
            )}
          </nav>
        )}

        {/* Right Controls: Flat selector, Notifications, Language, Logout */}
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
                fontSize: '0.82rem'
              }}
            >
              {user.flats.map((f) => (
                <option key={f.flat_id} value={f.flat_id}>
                  {f.flat_number} ({f.member_type})
                </option>
              ))}
            </select>
          )}

          {/* Notification Bell */}
          {user && <NotificationBell lang={currentLang} />}

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
                  boxShadow: currentLang === lang ? '0 1px 2px rgba(0,0,0,0.08)' : 'none',
                  cursor: 'pointer',
                }}
              >
                {lang === 'en' ? 'EN' : lang === 'mr' ? 'मराठी' : 'हिंदी'}
              </button>
            ))}
          </div>

          {/* User Profile Pill & Prominent Sign Out */}
          {user && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'nowrap' }}>
              <div
                title={`Signed in as ${user.name} (${user.phone})`}
                style={{
                  background: '#f8fafc',
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  padding: '0.3rem 0.55rem',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  color: 'var(--text-main)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.3rem',
                  maxWidth: '180px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}
              >
                <span>👤</span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user.name.split(' ')[0]}
                </span>
                <span style={{
                  fontSize: '0.68rem',
                  background: '#e2e8f0',
                  color: '#475569',
                  padding: '1px 5px',
                  borderRadius: '4px',
                  textTransform: 'uppercase',
                  fontWeight: 700
                }}>
                  {userRoles[0] || (hasFlats ? 'Resident' : 'User')}
                </span>
              </div>

              <button
                onClick={onLogout}
                data-testid="navbar-logout-btn"
                title="Sign out of your session"
                style={{
                  border: '1.5px solid #f87171',
                  background: '#fef2f2',
                  color: '#b91c1c',
                  fontSize: '0.82rem',
                  padding: '0.32rem 0.75rem',
                  borderRadius: '6px',
                  fontWeight: 700,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  cursor: 'pointer',
                  boxShadow: '0 1px 2px rgba(185, 28, 28, 0.08)',
                  transition: 'background-color 0.15s ease'
                }}
              >
                <span>🚪</span>
                <span>{t.logout}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
