import React from 'react';
import { BillingSummary } from '../api/client';
import { Language, translations } from '../i18n/translations';
import { formatMoney, isPositiveMoney } from '../utils/money';

interface LedgerViewProps {
  summary: BillingSummary;
  lang: Language;
}

export const LedgerView: React.FC<LedgerViewProps> = ({ summary, lang }) => {
  const t = translations[lang];

  return (
    <div style={{
      background: '#ffffff',
      borderRadius: 'var(--radius)',
      padding: '1.25rem',
      border: '1px solid var(--border)',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)' }}>
            {t.ledger_statement}
          </h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {summary.flat_number} • Reconciled per-flat running ledger
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Current Balance
          </span>
          <div style={{ fontSize: '1.1rem', fontWeight: 800, color: isPositiveMoney(summary.current_due) ? 'var(--danger)' : 'var(--success)' }}>
            {formatMoney(summary.current_due)}
          </div>
        </div>
      </div>

      {summary.recent_ledger.length === 0 ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No ledger transactions found.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{ background: '#f8fafc', borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                <th style={{ padding: '0.6rem' }}>Date</th>
                <th style={{ padding: '0.6rem' }}>Description</th>
                <th style={{ padding: '0.6rem', textAlign: 'right' }}>{t.debit} (₹)</th>
                <th style={{ padding: '0.6rem', textAlign: 'right' }}>{t.credit} (₹)</th>
                <th style={{ padding: '0.6rem', textAlign: 'right' }}>{t.balance} (₹)</th>
              </tr>
            </thead>
            <tbody>
              {summary.recent_ledger.map((entry) => (
                <tr key={entry.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '0.6rem', whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>
                    {new Date(entry.created_at).toLocaleDateString('en-IN')}
                  </td>
                  <td style={{ padding: '0.6rem', fontWeight: 500 }}>
                    {entry.description}
                  </td>
                  <td style={{ padding: '0.6rem', textAlign: 'right', color: entry.entry_type === 'DEBIT' ? 'var(--danger)' : 'inherit', fontWeight: entry.entry_type === 'DEBIT' ? 600 : 400 }}>
                    {entry.entry_type === 'DEBIT' ? formatMoney(entry.amount, { showCurrency: false }) : '-'}
                  </td>
                  <td style={{ padding: '0.6rem', textAlign: 'right', color: entry.entry_type === 'CREDIT' ? 'var(--success)' : 'inherit', fontWeight: entry.entry_type === 'CREDIT' ? 700 : 400 }}>
                    {entry.entry_type === 'CREDIT' ? formatMoney(entry.amount, { showCurrency: false }) : '-'}
                  </td>
                  <td style={{ padding: '0.6rem', textAlign: 'right', fontWeight: 700 }}>
                    {formatMoney(entry.balance_after)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
