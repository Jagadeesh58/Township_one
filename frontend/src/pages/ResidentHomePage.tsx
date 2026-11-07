// Day 1 · D1-S6 — Resident interface and PWA
// Resident home dashboard: localized greeting, 2-tap dues payment CTA, quick actions,
// multi-flat switcher, and payment receipt presentation.

import React, { useState, useEffect } from 'react';
import { api, UserProfile, BillingSummary, PaymentReceipt } from '../api/client';
import { Language, translations } from '../i18n/translations';
import { DuesCard } from '../components/DuesCard';
import { QuickActions } from '../components/QuickActions';
import { PaymentModal } from '../components/PaymentModal';
import { ReceiptModal } from '../components/ReceiptModal';
import { LedgerView } from '../components/LedgerView';

interface ResidentHomePageProps {
  user: UserProfile;
  selectedFlatId: string;
  lang: Language;
}

export const ResidentHomePage: React.FC<ResidentHomePageProps> = ({
  user,
  selectedFlatId,
  lang,
}) => {
  const t = translations[lang];
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [activeReceipt, setActiveReceipt] = useState<PaymentReceipt | null>(null);
  const [activeTab, setActiveTab] = useState<'HOME' | 'LEDGER'>('HOME');

  const loadBilling = async () => {
    if (!selectedFlatId) return;
    setLoading(true);
    try {
      const data = await api.getBillingSummary(selectedFlatId);
      setSummary(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBilling();
  }, [selectedFlatId]);

  const handlePaymentSuccess = (receipt: PaymentReceipt) => {
    setShowPaymentModal(false);
    setActiveReceipt(receipt);
    loadBilling(); // Refresh billing data after payment
  };

  const handleQuickAction = (act: string) => {
    if (act === 'pay') {
      setShowPaymentModal(true);
    } else {
      alert(`${act.toUpperCase()} module is available in Day 2 & Day 3 modules!`);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '1rem auto', padding: '0 1rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Welcome Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        color: '#ffffff',
        borderRadius: 'var(--radius)',
        padding: '1.25rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Welcome Resident
          </div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 800 }}>
            {user.name}
          </h2>
          <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '0.2rem' }}>
            Flat {summary?.flat_number || 'Loading...'} • Company A Township, Pune
          </div>
        </div>

        {/* Tab switch between Home and Ledger */}
        <div style={{ display: 'flex', background: 'rgba(255,255,255,0.1)', borderRadius: '8px', padding: '3px' }}>
          <button
            onClick={() => setActiveTab('HOME')}
            style={{
              background: activeTab === 'HOME' ? '#ffffff' : 'transparent',
              color: activeTab === 'HOME' ? '#1e293b' : '#cbd5e1',
              border: 'none',
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              fontWeight: 700,
              fontSize: '0.8rem'
            }}
          >
            {t.home}
          </button>
          <button
            onClick={() => setActiveTab('LEDGER')}
            style={{
              background: activeTab === 'LEDGER' ? '#ffffff' : 'transparent',
              color: activeTab === 'LEDGER' ? '#1e293b' : '#cbd5e1',
              border: 'none',
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              fontWeight: 700,
              fontSize: '0.8rem'
            }}
          >
            {t.ledger_statement}
          </button>
        </div>
      </div>

      {activeTab === 'HOME' ? (
        <>
          {/* Maintenance Dues Card (2-tap action to pay!) */}
          <DuesCard
            summary={summary}
            loading={loading}
            lang={lang}
            onPayClick={() => setShowPaymentModal(true)}
            onViewLedgerClick={() => setActiveTab('LEDGER')}
          />

          {/* Quick Actions Bar (2-tap shortcuts) */}
          <QuickActions
            lang={lang}
            onActionClick={handleQuickAction}
          />

          {/* Open Complaints Preview */}
          <div style={{
            background: '#ffffff',
            borderRadius: 'var(--radius)',
            padding: '1.1rem',
            border: '1px solid var(--border)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                {t.open_complaints}
              </span>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--primary)' }}>
                View All →
              </span>
            </div>

            {summary?.flat_number === 'T12-0408' ? (
              <div style={{
                background: '#fff1f2',
                border: '1px solid #ffe4e6',
                borderRadius: '8px',
                padding: '0.75rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#9f1239' }}>
                    CMP-2026-1001: Severe bathroom ceiling water seepage
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#e11d48', marginTop: '2px' }}>
                    Category: WATER_SUPPLY • Urgency: HIGH • Assigned to Plumbing Team
                  </div>
                </div>
                <span style={{
                  background: '#fda4af',
                  color: '#881337',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '10px'
                }}>
                  IN_PROGRESS
                </span>
              </div>
            ) : (
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', padding: '0.5rem 0' }}>
                ✓ No active complaints filed for this flat. Everything running smoothly!
              </div>
            )}
          </div>

          {/* Today's Visitors Preview */}
          <div style={{
            background: '#ffffff',
            borderRadius: 'var(--radius)',
            padding: '1.1rem',
            border: '1px solid var(--border)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                {t.recent_visitors}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Gate 1 & Gate 2
              </span>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', padding: '0.5rem 0' }}>
              {t.no_recent_visitors}
            </div>
          </div>

          {/* Community Broadcast Notice Banner */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '1rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.9rem' }}>📢</span>
              <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-main)' }}>
                Mandatory Water Tank Cleaning - Tower 01 to 14
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
              Water supply will be temporarily shut off between 10:00 AM and 2:00 PM on Tuesday for scheduled overhead tank disinfection.
            </p>
          </div>
        </>
      ) : (
        /* Ledger Statement View */
        summary && <LedgerView summary={summary} lang={lang} />
      )}

      {/* Payment Modal */}
      {showPaymentModal && summary && (
        <PaymentModal
          summary={summary}
          lang={lang}
          onClose={() => setShowPaymentModal(false)}
          onPaymentSuccess={handlePaymentSuccess}
        />
      )}

      {/* Receipt Modal */}
      {activeReceipt && (
        <ReceiptModal
          receipt={activeReceipt}
          lang={lang}
          onClose={() => setActiveReceipt(null)}
        />
      )}
    </div>
  );
};
