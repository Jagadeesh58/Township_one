import React from 'react';
import { Language, translations } from '../i18n/translations';

interface QuickActionsProps {
  lang: Language;
  onActionClick: (action: string) => void;
}

export const QuickActions: React.FC<QuickActionsProps> = ({ lang, onActionClick }) => {
  const t = translations[lang];

  const actions = [
    { id: 'pay', label: t.pay_dues, icon: '💳', bg: '#eff6ff', color: '#1d4ed8' },
    { id: 'complaint', label: t.raise_complaint, icon: '🔧', bg: '#fef2f2', color: '#b91c1c' },
    { id: 'visitor', label: t.guest_approval, icon: '🚪', bg: '#f0fdf4', color: '#15803d' },
    { id: 'amenity', label: t.book_amenity, icon: '🎾', bg: '#fefce8', color: '#a16207' },
  ];

  return (
    <div>
      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.6rem', textTransform: 'uppercase' }}>
        {t.quick_actions}
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '0.6rem',
      }}>
        {actions.map((act) => (
          <button
            key={act.id}
            onClick={() => onActionClick(act.id)}
            style={{
              background: '#ffffff',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              padding: '0.75rem 0.4rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '0.35rem',
              textAlign: 'center',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
              minHeight: '44px',
              minWidth: '44px',
              cursor: 'pointer'
            }}
          >
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: act.bg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.2rem'
            }}>
              {act.icon}
            </div>
            <span style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--text-main)', lineHeight: 1.2 }}>
              {act.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
