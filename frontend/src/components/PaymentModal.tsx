// Township One - Payment checkout modal
// Payment checkout modal with multi-bill selection, state machine retry lifecycle,
// strict idempotency key management, explicit test outcome selector, and localized feedback.

import React, { useState } from 'react';
import { api, BillingSummary, PaymentReceipt, BillItem } from '../api/client';
import { Language, translations } from '../i18n/translations';
import { formatMoney, generateIdempotencyKey } from '../utils/money';

export type PaymentState = 'READY' | 'PROCESSING' | 'SUCCESS' | 'FAILED' | 'NETWORK_INTERRUPTION';

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
  const [paymentState, setPaymentState] = useState<PaymentState>('READY');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const unpaidBills: BillItem[] = summary.unpaid_bills && summary.unpaid_bills.length > 0
    ? summary.unpaid_bills
    : (summary.latest_bill ? [summary.latest_bill] : []);

  const [selectedBillId, setSelectedBillId] = useState<string>(
    () => unpaidBills[0]?.id || summary.latest_bill?.id || ''
  );

  const [idempotencyKey, setIdempotencyKey] = useState<string>(generateIdempotencyKey);

  const selectedBill = unpaidBills.find(b => b.id === selectedBillId) || summary.latest_bill;
  const billId = selectedBill?.id;
  const dueAmount = selectedBill ? (selectedBill.balance_amount ?? selectedBill.total_amount) : summary.current_due;

  const handleBillSelect = (newBillId: string) => {
    setSelectedBillId(newBillId);
    setIdempotencyKey(generateIdempotencyKey());
    setPaymentState('READY');
    setErrorMsg(null);
  };

  const handleOutcomeSelect = (outcome: 'SUCCESS' | 'PENDING' | 'FAILED' | 'EXPIRED') => {
    setTestOutcome(outcome);
    setIdempotencyKey(generateIdempotencyKey());
    setPaymentState('READY');
    setErrorMsg(null);
  };

  const startNewAttempt = () => {
    setIdempotencyKey(generateIdempotencyKey());
    setPaymentState('READY');
    setErrorMsg(null);
  };

  const handlePay = async (isRetry: boolean = false) => {
    if (!billId) return;
    setPaymentState('PROCESSING');
    setErrorMsg(null);

    // If it's not an exact retry of a network interruption, ensure key is current
    const keyToUse = idempotencyKey;

    try {
      const res = await api.checkout({
        flat_id: summary.flat_id,
        bill_id: billId,
        amount: dueAmount,
        test_outcome: testOutcome,
        idempotency_key: keyToUse,
      });

      if (res.status === 'SUCCESS' && res.receipt) {
        setPaymentState('SUCCESS');
        onPaymentSuccess(res.receipt);
      } else if (res.status === 'FAILED') {
        setPaymentState('FAILED');
        setErrorMsg('Payment failed. Please try again.');
      } else if (res.status === 'PENDING') {
        setPaymentState('FAILED');
        setErrorMsg('Payment is being processed. Check your ledger shortly.');
      } else if (res.status === 'EXPIRED') {
        setPaymentState('FAILED');
        setErrorMsg('Your payment session has expired. Please try again.');
      }
    } catch (err: any) {
      const msg = err.message || '';
      const isNetwork =
        err.name === 'TypeError' ||
        msg.toLowerCase().includes('network') ||
        msg.toLowerCase().includes('fetch') ||
        msg.toLowerCase().includes('failed to fetch') ||
        (typeof navigator !== 'undefined' && !navigator.onLine);

      if (isNetwork) {
        setPaymentState('NETWORK_INTERRUPTION');
        setErrorMsg('Network error. You can safely retry — your payment will not be duplicated.');
      } else {
        setPaymentState('FAILED');
        setErrorMsg(msg || 'Payment processing error');
      }
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
            aria-label="Close"
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '1.2rem',
              color: 'var(--text-muted)',
              cursor: 'pointer'
            }}
          >
            ✕
          </button>
        </div>

        {/* Multi-Bill Selector if more than 1 unpaid bill */}
        {unpaidBills.length > 1 && (
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '0.35rem' }}>
              Select a Bill ({unpaidBills.length} unpaid):
            </label>
            <select
              value={selectedBillId}
              onChange={(e) => handleBillSelect(e.target.value)}
              disabled={paymentState === 'PROCESSING'}
              style={{
                width: '100%',
                padding: '0.55rem',
                borderRadius: '6px',
                border: '1px solid var(--border)',
                background: '#ffffff',
                fontSize: '0.85rem',
                fontWeight: 600
              }}
            >
              {unpaidBills.map((b) => (
                <option key={b.id} value={b.id}>
                  Bill {b.period_month}/{b.period_year} — {formatMoney(b.balance_amount ?? b.total_amount)} ({b.status})
                </option>
              ))}
            </select>
          </div>
        )}

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
          {selectedBill && (
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Period:</span>
              <span>{selectedBill.period_month}/{selectedBill.period_year}</span>
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.95rem', fontWeight: 700, borderTop: '1px dashed var(--border)', paddingTop: '0.5rem', marginTop: '0.5rem' }}>
            <span>{t.amount_due}:</span>
            <span style={{ color: 'var(--primary)' }}>{formatMoney(dueAmount)}</span>
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
                disabled={paymentState === 'PROCESSING'}
                onClick={() => handleOutcomeSelect(outcome)}
                style={{
                  border: `2px solid ${testOutcome === outcome ? 'var(--primary)' : 'var(--border)'}`,
                  background: testOutcome === outcome ? '#eff6ff' : '#ffffff',
                  color: testOutcome === outcome ? 'var(--primary)' : 'var(--text-main)',
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  cursor: paymentState === 'PROCESSING' ? 'not-allowed' : 'pointer'
                }}
              >
                {outcome}
              </button>
            ))}
          </div>
        </div>

        {/* Status / Error Notifications */}
        {errorMsg && (
          <div style={{
            background: paymentState === 'NETWORK_INTERRUPTION' ? '#fffbeb' : '#fee2e2',
            border: paymentState === 'NETWORK_INTERRUPTION' ? '1px solid #fde68a' : '1px solid #fecaca',
            color: paymentState === 'NETWORK_INTERRUPTION' ? '#92400e' : 'var(--danger)',
            fontSize: '0.82rem',
            padding: '0.65rem',
            borderRadius: '6px',
            marginBottom: '1rem',
            fontWeight: 500
          }}>
            {errorMsg}
          </div>
        )}

        {/* Contextual Action Buttons based on Payment State Machine */}
        {paymentState === 'NETWORK_INTERRUPTION' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button
              onClick={() => handlePay(true)}
              style={{
                width: '100%',
                background: '#d97706',
                color: '#ffffff',
                border: 'none',
                padding: '0.75rem',
                borderRadius: '8px',
                fontWeight: 700,
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              🔄 Retry Payment
            </button>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={startNewAttempt}
                style={{
                  flex: 1,
                  background: '#f1f5f9',
                  border: 'none',
                  padding: '0.6rem',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.82rem',
                  cursor: 'pointer'
                }}
              >
                Start New Attempt
              </button>
              <button
                onClick={onClose}
                style={{
                  flex: 1,
                  background: '#f1f5f9',
                  border: 'none',
                  padding: '0.6rem',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.82rem',
                  cursor: 'pointer'
                }}
              >
                {t.close}
              </button>
            </div>
          </div>
        ) : paymentState === 'FAILED' ? (
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
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              {t.close}
            </button>
            <button
              onClick={startNewAttempt}
              style={{
                flex: 2,
                background: 'var(--primary)',
                color: '#ffffff',
                border: 'none',
                padding: '0.75rem',
                borderRadius: '8px',
                fontWeight: 700,
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              Start New Attempt
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={onClose}
              disabled={paymentState === 'PROCESSING'}
              style={{
                flex: 1,
                background: '#f1f5f9',
                border: 'none',
                padding: '0.75rem',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: paymentState === 'PROCESSING' ? 'not-allowed' : 'pointer'
              }}
            >
              {t.close}
            </button>
            <button
              onClick={() => handlePay(false)}
              disabled={paymentState === 'PROCESSING'}
              style={{
                flex: 2,
                background: 'var(--primary)',
                color: '#ffffff',
                border: 'none',
                padding: '0.75rem',
                borderRadius: '8px',
                fontWeight: 700,
                fontSize: '0.9rem',
                cursor: paymentState === 'PROCESSING' ? 'not-allowed' : 'pointer',
                opacity: paymentState === 'PROCESSING' ? 0.7 : 1
              }}
            >
              {paymentState === 'PROCESSING' ? t.processing : `${t.confirm_payment} (${formatMoney(dueAmount)})`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
