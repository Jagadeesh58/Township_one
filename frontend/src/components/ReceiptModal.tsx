import React from 'react';
import { PaymentReceipt } from '../api/client';
import { Language, translations } from '../i18n/translations';
import { formatMoney } from '../utils/money';

interface ReceiptModalProps {
  receipt: PaymentReceipt;
  lang: Language;
  onClose: () => void;
}

export const ReceiptModal: React.FC<ReceiptModalProps> = ({ receipt, lang, onClose }) => {
  const t = translations[lang];

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(15, 23, 42, 0.6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 60,
      padding: '1rem'
    }}>
      <div style={{
        background: '#ffffff',
        borderRadius: 'var(--radius)',
        maxWidth: '480px',
        width: '100%',
        padding: '1.75rem',
        boxShadow: '0 25px 30px -5px rgba(0, 0, 0, 0.25)',
        position: 'relative'
      }}>
        {/* Receipt Header */}
        <div style={{ textAlign: 'center', borderBottom: '2px solid var(--border)', paddingBottom: '1rem', marginBottom: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Company A, Pune • Official Maintenance Receipt
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: '0.2rem', color: 'var(--text-main)' }}>
            {t.receipt}
          </h2>
          <div style={{
            display: 'inline-block',
            marginTop: '0.35rem',
            background: '#dcfce7',
            color: '#15803d',
            fontSize: '0.75rem',
            fontWeight: 700,
            padding: '2px 10px',
            borderRadius: '12px'
          }}>
            ✓ PAID & RECONCILED
          </div>
        </div>

        {/* Receipt Key-Value Rows */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.88rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.receipt_no}:</span>
            <span style={{ fontWeight: 700, fontFamily: 'monospace' }}>{receipt.receipt_number}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.flat_no}:</span>
            <span style={{ fontWeight: 600 }}>{receipt.flat_number}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.resident_name}:</span>
            <span style={{ fontWeight: 600 }}>{receipt.resident_name}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.date}:</span>
            <span>{new Date(receipt.issued_at).toLocaleString('en-IN')}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.reference}:</span>
            <span style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{receipt.transaction_reference}</span>
          </div>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '1.15rem',
            fontWeight: 800,
            color: 'var(--text-main)',
            borderTop: '2px solid var(--border)',
            paddingTop: '0.75rem',
            marginTop: '0.5rem'
          }}>
            <span>Amount Paid:</span>
            <span style={{ color: 'var(--success)' }}>{formatMoney(receipt.amount)}</span>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
          <button
            onClick={() => window.print()}
            style={{
              flex: 1,
              background: '#f8fafc',
              border: '1px solid var(--border)',
              padding: '0.75rem',
              borderRadius: '8px',
              fontWeight: 600,
              fontSize: '0.85rem'
            }}
          >
            🖨️ {t.download_receipt}
          </button>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              background: 'var(--primary)',
              color: '#ffffff',
              border: 'none',
              padding: '0.75rem',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '0.85rem'
            }}
          >
            {t.close}
          </button>
        </div>
      </div>
    </div>
  );
};
