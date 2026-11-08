// Township One - Resident Dues Card Component
// 2-tap direct payment CTA from resident home screen,
// displaying total outstanding dues, multi-bill notices, area-rate calculations, and late fees.

import React from 'react';
import { BillingSummary } from '../api/client';
import { Language, translations } from '../i18n/translations';
import { formatMoney, isPositiveMoney } from '../utils/money';

interface DuesCardProps {
  summary: BillingSummary | null;
  loading: boolean;
  lang: Language;
  onPayClick: () => void;
  onViewLedgerClick: () => void;
}

export const DuesCard: React.FC<DuesCardProps> = ({
  summary,
  loading,
  lang,
  onPayClick,
  onViewLedgerClick,
}) => {
  const t = translations[lang];

  if (loading) {
    return (
      <div style={{
        background: '#ffffff',
        borderRadius: 'var(--radius)',
        padding: '1.25rem',
        border: '1px solid var(--border)',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        animation: 'pulse 1.5s infinite'
      }}>
        <div style={{ height: '20px', background: '#e2e8f0', borderRadius: '4px', width: '40%', marginBottom: '1rem' }} />
        <div style={{ height: '36px', background: '#e2e8f0', borderRadius: '4px', width: '60%' }} />
      </div>
    );
  }

  if (!summary) return null;

  const totalOutstanding = summary.total_outstanding_due ?? summary.current_due;
  const hasDue = isPositiveMoney(totalOutstanding);
  const unpaidCount = summary.unpaid_bills?.length || (hasDue ? 1 : 0);

  return (
    <div style={{
      background: '#ffffff',
      borderRadius: 'var(--radius)',
      padding: '1.25rem',
      border: '1px solid var(--border)',
      boxShadow: '0 2px 4px rgba(0,0,0,0.04)',
      display: 'flex',
      flexDirection: 'column',
      gap: '1rem'
    }}>
      {/* Header: Title and Status Tag */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {t.dues_title}
        </span>
        {hasDue && summary.overdue_days > 0 ? (
          <span style={{
            background: '#fee2e2',
            color: 'var(--danger)',
            fontSize: '0.75rem',
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: '12px'
          }}>
            {summary.overdue_days} {t.days_overdue}
          </span>
        ) : hasDue ? (
          <span style={{
            background: '#fef3c7',
            color: '#b45309',
            fontSize: '0.75rem',
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: '12px'
          }}>
            Due 15th
          </span>
        ) : (
          <span style={{
            background: '#dcfce7',
            color: 'var(--success)',
            fontSize: '0.75rem',
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: '12px'
          }}>
            ✓ {t.up_to_date}
          </span>
        )}
      </div>

      {/* Big Due Amount Display */}
      <div>
        <div style={{ fontSize: '2.2rem', fontWeight: 800, color: hasDue ? 'var(--text-main)' : 'var(--success)', lineHeight: 1.1 }}>
          {formatMoney(totalOutstanding)}
        </div>
        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
          {summary.flat_number} • {summary.area_sqft} {t.sqft} @ {t.per_sqft_month}
        </div>
        {unpaidCount > 1 && (
          <div style={{ fontSize: '0.78rem', color: '#b45309', marginTop: '0.35rem', fontWeight: 600 }}>
            {unpaidCount} unpaid bills pending
          </div>
        )}
      </div>

      {/* Late fee breakdown notice if overdue */}
      {hasDue && isPositiveMoney(summary.estimated_late_fee) && (
        <div style={{
          background: '#fffbeb',
          border: '1px solid #fef3c7',
          borderRadius: '8px',
          padding: '0.6rem 0.75rem',
          fontSize: '0.78rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: 600, color: '#92400e' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>{t.late_fee_estimate}:</span>
              <span style={{
                background: '#fef3c7',
                color: '#92400e',
                border: '1px solid #fde68a',
                padding: '1px 6px',
                borderRadius: '4px',
                fontSize: '0.68rem',
                fontWeight: 700
              }}>
                Illustrative demo rule
              </span>
            </div>
            <span>+{formatMoney(summary.estimated_late_fee)}</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: '#b45309', marginTop: '4px', lineHeight: 1.3 }}>
            *{summary.late_fee_notice}
          </div>
        </div>
      )}

      {/* Action Buttons: 2-Tap Action direct from home */}
      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.25rem' }}>
        {hasDue ? (
          <button
            onClick={onPayClick}
            style={{
              flex: 2,
              background: 'var(--primary)',
              color: '#ffffff',
              border: 'none',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '0.95rem',
              boxShadow: '0 2px 4px rgba(37, 99, 235, 0.25)',
              cursor: 'pointer'
            }}
          >
            {t.pay_now} ({formatMoney(totalOutstanding)})
          </button>
        ) : (
          <div style={{
            flex: 2,
            background: '#f1f5f9',
            color: 'var(--text-muted)',
            textAlign: 'center',
            padding: '0.65rem 1rem',
            borderRadius: '8px',
            fontSize: '0.85rem',
            fontWeight: 500
          }}>
            {t.up_to_date}
          </div>
        )}

        <button
          onClick={onViewLedgerClick}
          style={{
            flex: 1,
            background: '#f8fafc',
            border: '1px solid var(--border)',
            color: 'var(--text-main)',
            padding: '0.75rem',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '0.85rem'
          }}
        >
          {t.ledger_statement}
        </button>
      </div>
    </div>
  );
};
