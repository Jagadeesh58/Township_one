import React, { useState } from 'react';
import { api, BillingSummary, PaymentReceipt } from '../api/client';
import { Language, translations } from '../i18n/translations';

interface PaymentModalProps {
  summary: BillingSummary;
  lang: Language;
  onClose: () => void;
  onPaymentSuccess: (receipt: PaymentReceipt) => void;
}

export const PaymentModal: React.FC<PaymentModalProps> = ({
  summary,
  lang,
  onClose,
  onPaymentSuccess,
}) => {
  const t = translations[lang];
  const [testOutcome, setTestOutcome] = useState<'SUCCESS' | 'PENDING' | 'FAILED' | 'EXPIRED'>('SUCCESS');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const billId = summary.latest_bill?.id;
  const dueAmount = summary.current_due;

  const handlePay = async () => {
    if (!billId) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.checkout({
        flat_id: summary.flat_id,
        bill_id: billId,
        amount: dueAmount,
        test_outcome: testOutcome,
      });

      if (res.status === 'SUCCESS' && res.receipt) {
        onPaymentSuccess(res.receipt);
      } else if (res.status === 'FAILED') {
        setErrorMsg('Simulated Payment Failed / Bank Declined (Test Mode Outcome)');
      } else if (res.status === 'PENDING') {
        setErrorMsg('Simulated Payment Pending (Awaiting Settlement)');
      } else if (res.status === 'EXPIRED') {
        setErrorMsg('Simulated Payment Session Expired');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Payment processing error');
    } finally {
      setLoading(false);
    }
  };

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
      zIndex: 50,
      padding: '1rem'
    }}>
      <div style={{
        background: '#ffffff',
        borderRadius: 'var(--radius)',
        maxWidth: '460px',
        width: '100%',
        padding: '1.5rem',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)'
      }}>
        {/* Header & TEST MODE Badge */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div>
            <span style={{
              background: '#fef3c7',
              color: '#b45309',
              fontSize: '0.72rem',
              fontWeight: 800,
              padding: '2px 8px',
              borderRadius: '4px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              {t.test_mode_badge}
            </span>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginTop: '0.35rem', color: 'var(--text-main)' }}>
              {t.test_checkout_title}
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '1.2rem',
              color: 'var(--text-muted)'
            }}
          >
            ✕
          </button>
        </div>

        {/* Bill Details Summary */}
        <div style={{
          background: '#f8fafc',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '0.85rem',
          marginBottom: '1rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.flat_no}:</span>
            <span style={{ fontWeight: 600 }}>{summary.flat_number}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.area}:</span>
            <span>{summary.area_sqft} {t.sqft}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.95rem', fontWeight: 700, borderTop: '1px dashed var(--border)', paddingTop: '0.5rem', marginTop: '0.5rem' }}>
            <span>{t.amount_due}:</span>
            <span style={{ color: 'var(--primary)' }}>₹{dueAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
          </div>
        </div>

        {/* Deliberate Test Outcome Selector */}
        <div style={{ marginBottom: '1.25rem' }}>
          <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>
            {t.select_test_outcome}
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
            {(['SUCCESS', 'PENDING', 'FAILED', 'EXPIRED'] as const).map((outcome) => (
              <button
                key={outcome}
                type="button"
                onClick={() => setTestOutcome(outcome)}
                style={{
                  border: `2px solid ${testOutcome === outcome ? 'var(--primary)' : 'var(--border)'}`,
                  background: testOutcome === outcome ? '#eff6ff' : '#ffffff',
                  color: testOutcome === outcome ? 'var(--primary)' : 'var(--text-main)',
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  padding: '0.5rem',
                  borderRadius: '6px'
                }}
              >
                {outcome}
              </button>
            ))}
          </div>
        </div>

        {errorMsg && (
          <div style={{
            background: '#fee2e2',
            color: 'var(--danger)',
            fontSize: '0.82rem',
            padding: '0.65rem',
            borderRadius: '6px',
            marginBottom: '1rem',
            fontWeight: 500
          }}>
            {errorMsg}
          </div>
        )}

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              background: '#f1f5f9',
              border: 'none',
              padding: '0.75rem',
              borderRadius: '8px',
              fontWeight: 600,
              fontSize: '0.9rem'
            }}
          >
            {t.close}
          </button>
          <button
            onClick={handlePay}
            disabled={loading}
            style={{
              flex: 2,
              background: 'var(--primary)',
              color: '#ffffff',
              border: 'none',
              padding: '0.75rem',
              borderRadius: '8px',
              fontWeight: 700,
              fontSize: '0.9rem',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? t.processing : `${t.confirm_payment} (₹${dueAmount.toLocaleString('en-IN')})`}
          </button>
        </div>
      </div>
    </div>
  );
};
