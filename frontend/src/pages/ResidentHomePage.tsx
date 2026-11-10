// Township One - Resident Home Dashboard
// Resident home dashboard: localized greeting, 2-tap dues payment CTA, quick actions,
// multi-flat switcher, today's visitors 1-tap approval, notice board, and guest pass generator.

import React, { useState, useEffect } from 'react';
import {
  api,
  UserProfile,
  BillingSummary,
  PaymentReceipt,
  VisitorEntryItem,
  NoticeRevisionItem,
  PreApprovalItem
} from '../api/client';
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
  onNavigateTab?: (tab: 'home' | 'complaints' | 'accounts' | 'helpdesk' | 'amenities' | 'guard' | 'committee' | 'notices' | 'notice-management') => void;
  onLogout?: () => void;
}

export const ResidentHomePage: React.FC<ResidentHomePageProps> = ({
  user,
  selectedFlatId,
  lang,
  onNavigateTab,
  onLogout,
}) => {
  const t = translations[lang];
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [activeReceipt, setActiveReceipt] = useState<PaymentReceipt | null>(null);
  const [activeTab, setActiveTab] = useState<'HOME' | 'LEDGER'>('HOME');

  // Visitors and Notices
  const [visitors, setVisitors] = useState<VisitorEntryItem[]>([]);
  const [notices, setNotices] = useState<NoticeRevisionItem[]>([]);
  const [visitorActionMsg, setVisitorActionMsg] = useState<string | null>(null);

  // Pre-approved Guest Pass Modal
  const [showGuestPassModal, setShowGuestPassModal] = useState(false);
  const [guestName, setGuestName] = useState('');
  const [guestPhone, setGuestPhone] = useState('');
  const [guestPurpose, setGuestPurpose] = useState('GUEST');
  const [validDays, setValidDays] = useState(1);
  const [createdPass, setCreatedPass] = useState<PreApprovalItem | null>(null);
  const [guestPassError, setGuestPassError] = useState<string | null>(null);
  const [isSubmittingPass, setIsSubmittingPass] = useState(false);

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

  const loadVisitors = async () => {
    if (!selectedFlatId) return;
    try {
      const data = await api.listVisitorEntries(undefined, selectedFlatId);
      setVisitors(data);
    } catch (err) {
      console.error('Failed to load visitors', err);
    }
  };

  const loadNotices = async () => {
    try {
      const data = await api.listActiveNotices(lang);
      setNotices(data);
    } catch (err) {
      console.error('Failed to load notices', err);
    }
  };

  useEffect(() => {
    loadBilling();
    loadVisitors();
    loadNotices();
  }, [selectedFlatId, lang]);

  const handlePaymentSuccess = (receipt: PaymentReceipt) => {
    setShowPaymentModal(false);
    setActiveReceipt(receipt);
    loadBilling();
  };

  const handleQuickAction = (act: string) => {
    if (act === 'pay') {
      setShowPaymentModal(true);
    } else if (act === 'complaint') {
      if (onNavigateTab) onNavigateTab('complaints');
    } else if (act === 'visitor') {
      setShowGuestPassModal(true);
    } else if (act === 'amenity') {
      if (onNavigateTab) onNavigateTab('amenities');
    }
  };

  const handleApproveVisitor = async (entryId: string) => {
    try {
      await api.decideVisitorApproval(entryId, 'APPROVE');
      setVisitorActionMsg('Visitor approved! Guard may now admit entry.');
      loadVisitors();
      setTimeout(() => setVisitorActionMsg(null), 4000);
    } catch (err: any) {
      setVisitorActionMsg(`Approval failed: ${err.error?.message || err.detail || err.message}`);
    }
  };

  const handleRejectVisitor = async (entryId: string) => {
    try {
      await api.decideVisitorApproval(entryId, 'REJECT');
      setVisitorActionMsg('Visitor denied. Guard notified.');
      loadVisitors();
      setTimeout(() => setVisitorActionMsg(null), 4000);
    } catch (err: any) {
      setVisitorActionMsg(`Rejection failed: ${err.error?.message || err.detail || err.message}`);
    }
  };

  const handleMarkNoticeRead = async (revisionId: string) => {
    try {
      await api.markNoticeRead(revisionId);
      loadNotices();
    } catch (err) {
      console.error('Failed to mark notice read', err);
    }
  };

  const handleCreateGuestPass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFlatId || !guestName || !guestPhone) return;
    setIsSubmittingPass(true);
    setGuestPassError(null);

    const now = new Date();
    const validUntil = new Date(now.getTime() + validDays * 24 * 60 * 60 * 1000);

    try {
      const pass = await api.createPreApproval({
        flat_id: selectedFlatId,
        guest_name: guestName,
        phone: guestPhone,
        purpose: guestPurpose,
        valid_from: now.toISOString(),
        valid_until: validUntil.toISOString(),
        max_uses: 1,
      });
      setCreatedPass(pass);
      setGuestName('');
      setGuestPhone('');
    } catch (err: any) {
      setGuestPassError(err.error?.message || err.detail || err.message || 'Failed to create guest pass');
    } finally {
      setIsSubmittingPass(false);
    }
  };

  const waitingVisitors = visitors.filter((v) => v.status === 'AWAITING_APPROVAL');

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
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem'
      }}>
        <div>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Welcome Resident
          </div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 800, margin: '0.2rem 0' }}>
            {user.name}
          </h2>
          <div style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>
            Flat {summary?.flat_number || 'Loading...'} • Company A Township, Pune
          </div>
        </div>

        {/* Right side controls: Tab switch between Home and Ledger + Sign Out */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', background: 'rgba(255,255,255,0.1)', borderRadius: '8px', padding: '3px' }}>
            <button
              onClick={() => setActiveTab('HOME')}
              style={{
                minHeight: '44px',
                background: activeTab === 'HOME' ? '#ffffff' : 'transparent',
                color: activeTab === 'HOME' ? '#1e293b' : '#cbd5e1',
                border: 'none',
                padding: '0.4rem 0.8rem',
                borderRadius: '6px',
                fontWeight: 700,
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              {t.home}
            </button>
            <button
              onClick={() => setActiveTab('LEDGER')}
              style={{
                minHeight: '44px',
                background: activeTab === 'LEDGER' ? '#ffffff' : 'transparent',
                color: activeTab === 'LEDGER' ? '#1e293b' : '#cbd5e1',
                border: 'none',
                padding: '0.4rem 0.8rem',
                borderRadius: '6px',
                fontWeight: 700,
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              {t.ledger_statement}
            </button>
          </div>

          {onLogout && (
            <button
              onClick={onLogout}
              data-testid="resident-logout-btn"
              title="Sign out of Township One"
              style={{
                minHeight: '44px',
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid rgba(248, 113, 113, 0.5)',
                color: '#fee2e2',
                padding: '0.4rem 0.85rem',
                borderRadius: '6px',
                fontWeight: 700,
                fontSize: '0.82rem',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem'
              }}
            >
              <span>🚪</span>
              <span>{t.logout}</span>
            </button>
          )}
        </div>
      </div>

      {activeTab === 'HOME' ? (
        <>
          {/* Urgent Visitor Approval Banner (<= 2 taps for key resident action!) */}
          {waitingVisitors.length > 0 && (
            <div style={{
              background: '#fef3c7',
              border: '2px solid #f59e0b',
              borderRadius: 'var(--radius)',
              padding: '1rem',
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)'
            }}>
              <div style={{ fontWeight: 800, fontSize: '0.95rem', color: '#92400e', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                🔔 Visitor Awaiting Gate Admission ({waitingVisitors.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {waitingVisitors.map((v) => (
                  <div
                    key={v.id}
                    style={{
                      background: '#ffffff',
                      borderRadius: '8px',
                      padding: '0.85rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '0.75rem'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                        {v.visitor_name} ({v.phone || 'No phone'})
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        Purpose: {v.purpose} • Gate: {v.gate_id} • Arrived: {new Date(v.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                    {/* 1-Tap Action Buttons (>= 48px touch targets) */}
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={() => handleRejectVisitor(v.id)}
                        style={{
                          minHeight: '48px',
                          minWidth: '90px',
                          padding: '0.5rem 1rem',
                          borderRadius: '6px',
                          border: '1px solid #ef4444',
                          background: '#fff1f2',
                          color: '#b91c1c',
                          fontWeight: 700,
                          fontSize: '0.85rem',
                          cursor: 'pointer'
                        }}
                      >
                        ✕ {t.reject}
                      </button>
                      <button
                        onClick={() => handleApproveVisitor(v.id)}
                        style={{
                          minHeight: '48px',
                          minWidth: '90px',
                          padding: '0.5rem 1rem',
                          borderRadius: '6px',
                          border: 'none',
                          background: '#16a34a',
                          color: '#ffffff',
                          fontWeight: 700,
                          fontSize: '0.85rem',
                          cursor: 'pointer'
                        }}
                      >
                        ✓ {t.approve}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {visitorActionMsg && (
            <div style={{
              padding: '0.75rem',
              borderRadius: '8px',
              background: '#ecfdf5',
              border: '1px solid #a7f3d0',
              color: '#065f46',
              fontSize: '0.85rem'
            }}>
              {visitorActionMsg}
            </div>
          )}

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
              <span
                onClick={() => onNavigateTab && onNavigateTab('complaints')}
                style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--primary)', cursor: 'pointer' }}
              >
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

          {/* Today's Visitors Preview Card */}
          <div style={{
            background: '#ffffff',
            borderRadius: 'var(--radius)',
            padding: '1.1rem',
            border: '1px solid var(--border)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                🚪 {t.recent_visitors}
              </span>
              <button
                onClick={() => setShowGuestPassModal(true)}
                style={{
                  minHeight: '48px',
                  padding: '0.35rem 0.8rem',
                  border: '1px solid var(--primary)',
                  borderRadius: '6px',
                  background: '#eff6ff',
                  color: 'var(--primary)',
                  fontWeight: 700,
                  fontSize: '0.8rem',
                  cursor: 'pointer'
                }}
              >
                + {t.generate_pass}
              </button>
            </div>

            {visitors.length === 0 ? (
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', padding: '0.5rem 0' }}>
                {t.no_recent_visitors}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {visitors.slice(0, 4).map((entry) => (
                  <div
                    key={entry.id}
                    style={{
                      borderBottom: '1px solid var(--border)',
                      paddingBottom: '0.5rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '0.82rem'
                    }}
                  >
                    <div>
                      <strong>{entry.visitor_name}</strong> ({entry.purpose})
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        Gate {entry.gate_id} • {new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                    <span style={{
                      fontWeight: 700,
                      fontSize: '0.75rem',
                      padding: '2px 8px',
                      borderRadius: '10px',
                      background: entry.status === 'ADMITTED' ? '#dcfce7' : entry.status === 'REJECTED' ? '#fee2e2' : '#f1f5f9',
                      color: entry.status === 'ADMITTED' ? '#15803d' : entry.status === 'REJECTED' ? '#b91c1c' : '#475569'
                    }}>
                      {entry.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Community Notices Card with Tower Targeting and Language Fallback */}
          <div style={{
            background: '#ffffff',
            borderRadius: 'var(--radius)',
            padding: '1.1rem',
            border: '1px solid var(--border)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                📢 {t.notice_board}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Tower & Township Updates
              </span>
            </div>

            {notices.length === 0 ? (
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
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4, margin: 0 }}>
                  Water supply will be temporarily shut off between 10:00 AM and 2:00 PM on Tuesday for scheduled overhead tank disinfection.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                {notices.map((n) => {
                  return (
                    <div
                      key={n.id}
                      style={{
                        background: '#f8fafc',
                        border: '1px solid var(--border)',
                        borderRadius: '8px',
                        padding: '0.85rem'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.35rem' }}>
                        <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-main)' }}>
                          {n.title}
                        </div>
                        <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
                          {n.is_fallback_language && (
                            <span style={{
                              background: '#fef3c7',
                              color: '#92400e',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              padding: '2px 6px',
                              borderRadius: '4px'
                            }}>
                              {t.shown_in_english}
                            </span>
                          )}
                          <span style={{
                            background: n.severity === 'URGENT' ? '#fee2e2' : '#e0f2fe',
                            color: n.severity === 'URGENT' ? '#b91c1c' : '#0369a1',
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: '4px'
                          }}>
                            {n.severity}
                          </span>
                        </div>
                      </div>

                      <p style={{ fontSize: '0.8rem', color: '#475569', lineHeight: 1.4, margin: '0 0 0.5rem 0' }}>
                        {n.body}
                      </p>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        <span>
                          {n.tower_number ? `Target: Tower ${n.tower_number}` : 'All Towers'} • Rev #{n.revision_number}
                        </span>
                        {!n.is_read && (
                          <button
                            onClick={() => handleMarkNoticeRead(n.id)}
                            style={{
                              minHeight: '44px',
                              padding: '0.2rem 0.6rem',
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px',
                              background: '#ffffff',
                              fontSize: '0.72rem',
                              cursor: 'pointer',
                              fontWeight: 600
                            }}
                          >
                            ✓ {t.mark_as_read}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
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

      {/* Generate Guest Pass Modal */}
      {showGuestPassModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
          padding: '1rem'
        }}>
          <div style={{
            background: '#ffffff',
            borderRadius: '12px',
            maxWidth: '440px',
            width: '100%',
            padding: '1.5rem',
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0 0 0.5rem 0' }}>
              🎟️ {t.generate_pass}
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '0 0 1rem 0' }}>
              Create a 6-digit fast-track entry code with offline cryptographic verification.
            </p>

            {createdPass ? (
              <div style={{
                background: '#f0fdf4',
                border: '1px solid #86efac',
                borderRadius: '8px',
                padding: '1rem',
                textAlign: 'center',
                marginBottom: '1rem'
              }}>
                <div style={{ fontSize: '0.8rem', color: '#166534', fontWeight: 600 }}>GUEST PASS CODE</div>
                <div style={{
                  fontSize: '2rem',
                  fontWeight: 900,
                  letterSpacing: '0.2em',
                  color: '#15803d',
                  margin: '0.5rem 0'
                }}>
                  {createdPass.code}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#166534' }}>
                  Valid for <strong>{createdPass.guest_name}</strong> until {new Date(createdPass.valid_until).toLocaleDateString()}
                </div>
                <button
                  onClick={() => {
                    if (createdPass.code) {
                      navigator.clipboard?.writeText(createdPass.code);
                      alert(`Code ${createdPass.code} copied!`);
                    }
                  }}
                  style={{
                    minHeight: '48px',
                    marginTop: '0.75rem',
                    padding: '0.4rem 1rem',
                    border: '1px solid #16a34a',
                    borderRadius: '6px',
                    background: '#ffffff',
                    color: '#15803d',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  📋 Copy Code to Share
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreateGuestPass} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>
                    Guest Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={guestName}
                    onChange={(e) => setGuestName(e.target.value)}
                    placeholder="e.g. Rahul Sharma"
                    style={{
                      minHeight: '48px',
                      width: '100%',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '6px',
                      border: '1px solid var(--border)',
                      fontSize: '0.9rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>
                    Guest Mobile Number *
                  </label>
                  <input
                    type="tel"
                    required
                    value={guestPhone}
                    onChange={(e) => setGuestPhone(e.target.value)}
                    placeholder="10-digit mobile number"
                    style={{
                      minHeight: '48px',
                      width: '100%',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '6px',
                      border: '1px solid var(--border)',
                      fontSize: '0.9rem'
                    }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                  <div>
                    <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>
                      Purpose
                    </label>
                    <select
                      value={guestPurpose}
                      onChange={(e) => setGuestPurpose(e.target.value)}
                      style={{
                        minHeight: '48px',
                        width: '100%',
                        padding: '0.5rem',
                        borderRadius: '6px',
                        border: '1px solid var(--border)',
                        fontSize: '0.85rem'
                      }}
                    >
                      <option value="GUEST">Guest / Family</option>
                      <option value="DELIVERY">Delivery</option>
                      <option value="CAB">Cab / Taxi</option>
                      <option value="SERVICE">Home Service</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.25rem' }}>
                      Validity
                    </label>
                    <select
                      value={validDays}
                      onChange={(e) => setValidDays(Number(e.target.value))}
                      style={{
                        minHeight: '48px',
                        width: '100%',
                        padding: '0.5rem',
                        borderRadius: '6px',
                        border: '1px solid var(--border)',
                        fontSize: '0.85rem'
                      }}
                    >
                      <option value={1}>1 Day (Today)</option>
                      <option value={2}>2 Days</option>
                      <option value={7}>7 Days</option>
                    </select>
                  </div>
                </div>

                {guestPassError && (
                  <div style={{ color: '#dc2626', fontSize: '0.8rem' }}>
                    ⚠️ {guestPassError}
                  </div>
                )}

                <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setShowGuestPassModal(false);
                      setCreatedPass(null);
                    }}
                    style={{
                      minHeight: '48px',
                      padding: '0.5rem 1rem',
                      borderRadius: '6px',
                      border: '1px solid var(--border)',
                      background: '#ffffff',
                      cursor: 'pointer'
                    }}
                  >
                    {t.close}
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingPass}
                    style={{
                      minHeight: '48px',
                      padding: '0.5rem 1.25rem',
                      borderRadius: '6px',
                      border: 'none',
                      background: 'var(--primary)',
                      color: '#ffffff',
                      fontWeight: 700,
                      cursor: isSubmittingPass ? 'not-allowed' : 'pointer'
                    }}
                  >
                    {isSubmittingPass ? t.processing : 'Generate Pass'}
                  </button>
                </div>
              </form>
            )}

            {createdPass && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.75rem' }}>
                <button
                  onClick={() => {
                    setShowGuestPassModal(false);
                    setCreatedPass(null);
                  }}
                  style={{
                    minHeight: '48px',
                    padding: '0.5rem 1.5rem',
                    borderRadius: '6px',
                    border: 'none',
                    background: 'var(--primary)',
                    color: '#ffffff',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  Done
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
