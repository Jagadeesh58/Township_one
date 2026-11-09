import React, { useState, useEffect } from 'react';
import { api, UserProfile, VisitorEntryItem, GuestCodeVerificationResult } from '../api/client';
import { Language, translations } from '../i18n/translations';

interface GuardGateTerminalProps {
  user: UserProfile;
  lang: Language;
}

const GATES = [
  { id: 'gate_1', number: 1, name: 'Main North Gate', desc: 'Main boulevard vehicle & visitor entry' },
  { id: 'gate_2', number: 2, name: 'South Gate', desc: 'Near Tower 18-28 service exit' },
  { id: 'gate_3', number: 3, name: 'East Gate', desc: 'Pedestrian & school bus pickup gate' },
  { id: 'gate_4', number: 4, name: 'West Gate', desc: 'Clubhouse and sports arena delivery gate' },
];

export const GuardGateTerminal: React.FC<GuardGateTerminalProps> = ({ user, lang }) => {
  const t = translations[lang];
  const [selectedGateNum, setSelectedGateNum] = useState<number>(1);
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [darkTheme, setDarkTheme] = useState<boolean>(false);
  const [entries, setEntries] = useState<VisitorEntryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Verification
  const [verifyCode, setVerifyCode] = useState<string>('');
  const [verifyResult, setVerifyResult] = useState<GuestCodeVerificationResult | null>(null);

  // New Visitor Form
  const [visitorName, setVisitorName] = useState<string>('');
  const [visitorPhone, setVisitorPhone] = useState<string>('');
  const [visitorPurpose, setVisitorPurpose] = useState<string>('Delivery');
  const [targetFlatId, setTargetFlatId] = useState<string>('');
  const [uploadedPhotoId, setUploadedPhotoId] = useState<string | null>(null);
  const [uploadingPhoto, setUploadingPhoto] = useState<boolean>(false);

  // Override Modal
  const [overrideEntryId, setOverrideEntryId] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState<string>('');

  // Gate matching
  const currentGate = GATES.find((g) => g.number === selectedGateNum) || GATES[0];

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const fetchEntries = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listVisitorEntries(currentGate.id);
      setEntries(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load gate entries');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, [selectedGateNum]);

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setUploadingPhoto(true);
    setError(null);
    try {
      const res = await api.uploadVisitorPhoto(file);
      setUploadedPhotoId(res.photo_id);
      setSuccessMsg('Photograph captured and verified (90-day retention).');
    } catch (err: any) {
      setError(err.message || 'Failed to process visitor photo');
    } finally {
      setUploadingPhoto(false);
    }
  };

  const handleRecordArrival = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!visitorName.trim() || !targetFlatId.trim()) {
      setError('Visitor Name and Flat ID are required.');
      return;
    }
    setError(null);
    setSuccessMsg(null);
    try {
      await api.createVisitorEntry({
        gate_id: currentGate.id,
        flat_id: targetFlatId.trim(),
        visitor_name: visitorName.trim(),
        phone: visitorPhone.trim() || undefined,
        purpose: visitorPurpose.trim(),
        photo_id: uploadedPhotoId || undefined,
      });
      setSuccessMsg(`Arrival recorded for ${visitorName}. Resident approval requested.`);
      setVisitorName('');
      setVisitorPhone('');
      setUploadedPhotoId(null);
      fetchEntries();
    } catch (err: any) {
      setError(err.message || 'Failed to record visitor arrival');
    }
  };

  const handleAdmit = async (id: string) => {
    setError(null);
    try {
      await api.admitVisitor(id);
      setSuccessMsg('Visitor admitted through gate barrier.');
      fetchEntries();
    } catch (err: any) {
      setError(err.message || 'Failed to admit visitor');
    }
  };

  const handleExit = async (id: string) => {
    setError(null);
    try {
      await api.exitVisitor(id);
      setSuccessMsg('Visitor exit recorded.');
      fetchEntries();
    } catch (err: any) {
      setError(err.message || 'Failed to record exit');
    }
  };

  const handleVerifyCode = async () => {
    if (!verifyCode.trim()) return;
    setError(null);
    setVerifyResult(null);
    try {
      const isJwt = verifyCode.includes('.');
      const res = await api.verifyGuestCode(
        currentGate.id,
        isJwt ? undefined : verifyCode.trim(),
        isJwt ? verifyCode.trim() : undefined
      );
      setVerifyResult(res);
      if (res.valid) {
        setSuccessMsg(`Guest Verified: ${res.guest_name || 'Authorized'} (Remaining Uses: ${res.remaining_uses})`);
      } else {
        setError(res.message);
      }
    } catch (err: any) {
      setError(err.message || 'Verification failed');
    }
  };

  const handleApplyOverride = async () => {
    if (!overrideEntryId || !overrideReason.trim()) return;
    setError(null);
    try {
      await api.overrideVisitor(overrideEntryId, overrideReason.trim());
      setSuccessMsg('Supervisor override granted. Visitor can now be admitted.');
      setOverrideEntryId(null);
      setOverrideReason('');
      fetchEntries();
    } catch (err: any) {
      setError(err.message || 'Failed to apply supervisor override');
    }
  };

  // Color scheme based on darkTheme toggle for guard sunlight/night readability
  const themeBg = darkTheme ? '#0F172A' : '#F8FAFC';
  const cardBg = darkTheme ? '#1E293B' : '#FFFFFF';
  const textColor = darkTheme ? '#F8FAFC' : '#0F172A';
  const textMuted = darkTheme ? '#94A3B8' : '#64748B';
  const borderColor = darkTheme ? '#334155' : '#E2E8F0';

  return (
    <div style={{ background: themeBg, color: textColor, minHeight: '100vh', padding: '1rem', transition: 'background 0.2s' }}>
      <div style={{ maxWidth: '1050px', margin: '0 auto' }}>
        {/* Header Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.2rem' }}>
          <div>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0 }}>🛡️ {t.guard_terminal}</h1>
            <div style={{ fontSize: '0.85rem', color: textMuted }}>
              Township One Access Control • Operator: {user.name} ({user.phone})
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            {/* Online / Offline status badge */}
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.4rem 0.8rem',
              borderRadius: '20px',
              fontWeight: 600,
              fontSize: '0.82rem',
              background: isOnline ? '#DCFCE7' : '#FEE2E2',
              color: isOnline ? '#15803D' : '#B91C1C',
              border: `1px solid ${isOnline ? '#86EFAC' : '#FCA5A5'}`,
            }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: isOnline ? '#16A34A' : '#DC2626' }} />
              {isOnline ? t.online : t.offline}
            </div>

            {/* Dark Mode toggle for outdoor guards */}
            <button
              onClick={() => setDarkTheme(!darkTheme)}
              style={{
                minHeight: '48px',
                minWidth: '48px',
                padding: '0.5rem 0.9rem',
                borderRadius: '8px',
                border: `1px solid ${borderColor}`,
                background: cardBg,
                color: textColor,
                fontWeight: 600,
                cursor: 'pointer',
              }}
              title="Toggle High-Contrast Outdoor Theme"
            >
              {darkTheme ? '☀️ Light' : '🌙 Night'}
            </button>
          </div>
        </div>

        {/* Gate Selection Pills */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.2rem' }}>
          {GATES.map((g) => (
            <button
              key={g.number}
              onClick={() => setSelectedGateNum(g.number)}
              style={{
                minHeight: '48px',
                padding: '0.6rem 1.1rem',
                borderRadius: '8px',
                border: selectedGateNum === g.number ? '2px solid #2563EB' : `1px solid ${borderColor}`,
                background: selectedGateNum === g.number ? (darkTheme ? '#1E3A8A' : '#EFF6FF') : cardBg,
                color: selectedGateNum === g.number ? (darkTheme ? '#93C5FD' : '#1D4ED8') : textColor,
                fontWeight: selectedGateNum === g.number ? 700 : 500,
                cursor: 'pointer',
              }}
            >
              Gate {g.number}: {g.name}
            </button>
          ))}
        </div>

        {/* Messages */}
        {error && (
          <div style={{ padding: '0.75rem 1rem', background: '#FEE2E2', color: '#B91C1C', borderRadius: '8px', marginBottom: '1rem', fontWeight: 500 }}>
            ⚠️ {error}
          </div>
        )}
        {successMsg && (
          <div style={{ padding: '0.75rem 1rem', background: '#DCFCE7', color: '#15803D', borderRadius: '8px', marginBottom: '1rem', fontWeight: 500 }}>
            ✅ {successMsg}
          </div>
        )}

        {/* Two-Column Grid: Quick Verification & Arrival Recording */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.2rem', marginBottom: '1.5rem' }}>
          {/* Box 1: Pre-Approved Guest Pass Verifier */}
          <div style={{ background: cardBg, padding: '1.2rem', borderRadius: '10px', border: `1px solid ${borderColor}` }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: 0, marginBottom: '0.8rem' }}>
              🔑 {t.verify_code}
            </h2>
            <p style={{ fontSize: '0.85rem', color: textMuted, marginTop: 0 }}>
              Enter 6-digit resident pass code or scan offline ECDSA compact credential token.
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.6rem' }}>
              <input
                type="text"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value)}
                placeholder="e.g. 458921"
                style={{
                  flex: 1,
                  minHeight: '48px',
                  padding: '0.6rem 0.8rem',
                  borderRadius: '8px',
                  border: `1px solid ${borderColor}`,
                  background: darkTheme ? '#0F172A' : '#FFFFFF',
                  color: textColor,
                  fontSize: '1rem',
                  fontWeight: 600,
                  letterSpacing: '1px',
                }}
              />
              <button
                type="button"
                onClick={handleVerifyCode}
                style={{
                  minHeight: '48px',
                  minWidth: '100px',
                  background: '#2563EB',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Verify
              </button>
            </div>

            {verifyResult && (
              <div style={{
                marginTop: '0.8rem',
                padding: '0.75rem',
                borderRadius: '8px',
                background: verifyResult.valid ? '#F0FDF4' : '#FEF2F2',
                border: `1px solid ${verifyResult.valid ? '#86EFAC' : '#FCA5A5'}`,
                color: verifyResult.valid ? '#166534' : '#991B1B',
                fontSize: '0.88rem',
              }}>
                <div style={{ fontWeight: 700 }}>{verifyResult.message}</div>
                {verifyResult.guest_name && <div>Guest: <b>{verifyResult.guest_name}</b></div>}
                {verifyResult.remaining_uses !== undefined && <div>Remaining Uses: <b>{verifyResult.remaining_uses}</b></div>}
              </div>
            )}
          </div>

          {/* Box 2: Record Visitor Arrival */}
          <div style={{ background: cardBg, padding: '1.2rem', borderRadius: '10px', border: `1px solid ${borderColor}` }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: 0, marginBottom: '0.8rem' }}>
              📝 {t.record_entry}
            </h2>
            <form onSubmit={handleRecordArrival} style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <input
                  type="text"
                  placeholder="Visitor Name *"
                  value={visitorName}
                  onChange={(e) => setVisitorName(e.target.value)}
                  required
                  style={{
                    minHeight: '48px',
                    padding: '0.5rem 0.8rem',
                    borderRadius: '8px',
                    border: `1px solid ${borderColor}`,
                    background: darkTheme ? '#0F172A' : '#FFFFFF',
                    color: textColor,
                  }}
                />
                <input
                  type="text"
                  placeholder="Visitor Phone"
                  value={visitorPhone}
                  onChange={(e) => setVisitorPhone(e.target.value)}
                  style={{
                    minHeight: '48px',
                    padding: '0.5rem 0.8rem',
                    borderRadius: '8px',
                    border: `1px solid ${borderColor}`,
                    background: darkTheme ? '#0F172A' : '#FFFFFF',
                    color: textColor,
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <input
                  type="text"
                  placeholder="Flat Number or ID *"
                  value={targetFlatId}
                  onChange={(e) => setTargetFlatId(e.target.value)}
                  required
                  style={{
                    minHeight: '48px',
                    padding: '0.5rem 0.8rem',
                    borderRadius: '8px',
                    border: `1px solid ${borderColor}`,
                    background: darkTheme ? '#0F172A' : '#FFFFFF',
                    color: textColor,
                  }}
                />
                <select
                  value={visitorPurpose}
                  onChange={(e) => setVisitorPurpose(e.target.value)}
                  style={{
                    minHeight: '48px',
                    padding: '0.5rem 0.8rem',
                    borderRadius: '8px',
                    border: `1px solid ${borderColor}`,
                    background: darkTheme ? '#0F172A' : '#FFFFFF',
                    color: textColor,
                  }}
                >
                  <option value="Delivery - Food/Groceries">Delivery - Food/Groceries</option>
                  <option value="Delivery - Courier/E-commerce">Delivery - E-commerce</option>
                  <option value="Personal Guest">Personal Guest</option>
                  <option value="Home Maintenance / Repair">Maintenance / Repair</option>
                  <option value="Official / Government Inspection">Official Inspection</option>
                  <option value="Cab / Transport Pickup">Cab / Transport Pickup</option>
                </select>
              </div>

              {/* Photo capture */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <label style={{
                  minHeight: '48px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '0 1rem',
                  borderRadius: '8px',
                  border: `1px dashed ${borderColor}`,
                  background: darkTheme ? '#0F172A' : '#F1F5F9',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                }}>
                  📷 {uploadingPhoto ? 'Processing photo...' : uploadedPhotoId ? 'Photo Attached ✓' : 'Capture / Upload Photo'}
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={handlePhotoUpload}
                    style={{ display: 'none' }}
                  />
                </label>
                {uploadedPhotoId && (
                  <span style={{ fontSize: '0.75rem', color: '#16A34A', fontWeight: 600 }}>EXIF stripped & signed</span>
                )}
              </div>

              <button
                type="submit"
                style={{
                  minHeight: '48px',
                  background: '#16A34A',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 700,
                  fontSize: '0.95rem',
                  cursor: 'pointer',
                  marginTop: '0.4rem',
                }}
              >
                {t.record_entry}
              </button>
            </form>
          </div>
        </div>

        {/* Live Visitor Entries Table */}
        <div style={{ background: cardBg, padding: '1.2rem', borderRadius: '10px', border: `1px solid ${borderColor}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0 }}>
              📋 Today's Visitors at Gate {currentGate.number} ({entries.length})
            </h2>
            <button
              onClick={fetchEntries}
              disabled={loading}
              style={{
                minHeight: '48px',
                padding: '0.4rem 0.9rem',
                borderRadius: '8px',
                border: `1px solid ${borderColor}`,
                background: darkTheme ? '#0F172A' : '#FFFFFF',
                color: textColor,
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              🔄 Refresh
            </button>
          </div>

          {entries.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: textMuted }}>
              No visitors registered at this gate today.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
                <thead>
                  <tr style={{ borderBottom: `2px solid ${borderColor}`, textAlign: 'left', color: textMuted }}>
                    <th style={{ padding: '0.6rem' }}>Visitor</th>
                    <th style={{ padding: '0.6rem' }}>Flat</th>
                    <th style={{ padding: '0.6rem' }}>Purpose</th>
                    <th style={{ padding: '0.6rem' }}>Status</th>
                    <th style={{ padding: '0.6rem' }}>Time</th>
                    <th style={{ padding: '0.6rem', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((item) => {
                    const statusColor =
                      item.status === 'APPROVED' ? '#16A34A' :
                      item.status === 'ADMITTED' ? '#2563EB' :
                      item.status === 'OVERRIDDEN_ADMIT' ? '#9333EA' :
                      item.status === 'REJECTED' ? '#DC2626' :
                      item.status === 'EXITED' ? '#6B7280' : '#D97706';

                    return (
                      <tr key={item.id} style={{ borderBottom: `1px solid ${borderColor}` }}>
                        <td style={{ padding: '0.6rem', fontWeight: 600 }}>
                          {item.visitor_name}
                          {item.phone && <div style={{ fontSize: '0.75rem', color: textMuted }}>{item.phone}</div>}
                        </td>
                        <td style={{ padding: '0.6rem' }}>
                          <b>{item.flat_number || item.flat_id}</b>
                          {item.tower_number && <span style={{ fontSize: '0.75rem', color: textMuted }}> ({item.tower_number})</span>}
                        </td>
                        <td style={{ padding: '0.6rem' }}>{item.purpose}</td>
                        <td style={{ padding: '0.6rem' }}>
                          <span style={{
                            padding: '0.2rem 0.5rem',
                            borderRadius: '4px',
                            fontWeight: 700,
                            fontSize: '0.75rem',
                            background: `${statusColor}22`,
                            color: statusColor,
                            border: `1px solid ${statusColor}55`,
                          }}>
                            {item.status}
                          </span>
                        </td>
                        <td style={{ padding: '0.6rem', fontSize: '0.78rem', color: textMuted }}>
                          {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td style={{ padding: '0.6rem', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
                            {/* Admit button */}
                            {(item.status === 'APPROVED' || item.status === 'OVERRIDDEN_ADMIT') && (
                              <button
                                onClick={() => handleAdmit(item.id)}
                                style={{
                                  minHeight: '48px',
                                  padding: '0.4rem 0.8rem',
                                  background: '#16A34A',
                                  color: '#FFFFFF',
                                  border: 'none',
                                  borderRadius: '6px',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                }}
                              >
                                {t.admit}
                              </button>
                            )}

                            {/* Exit button */}
                            {item.status === 'ADMITTED' && (
                              <button
                                onClick={() => handleExit(item.id)}
                                style={{
                                  minHeight: '48px',
                                  padding: '0.4rem 0.8rem',
                                  background: '#4B5563',
                                  color: '#FFFFFF',
                                  border: 'none',
                                  borderRadius: '6px',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                }}
                              >
                                {t.exit}
                              </button>
                            )}

                            {/* Supervisor override button */}
                            {item.status === 'AWAITING_APPROVAL' && (
                              <button
                                onClick={() => setOverrideEntryId(item.id)}
                                style={{
                                  minHeight: '48px',
                                  padding: '0.4rem 0.8rem',
                                  background: darkTheme ? '#334155' : '#F1F5F9',
                                  color: textColor,
                                  border: `1px solid ${borderColor}`,
                                  borderRadius: '6px',
                                  fontWeight: 600,
                                  fontSize: '0.75rem',
                                  cursor: 'pointer',
                                }}
                              >
                                {t.override}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Supervisor Override Reason Modal */}
        {overrideEntryId && (
          <div style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '1rem',
          }}>
            <div style={{
              background: cardBg,
              color: textColor,
              padding: '1.5rem',
              borderRadius: '12px',
              maxWidth: '450px',
              width: '100%',
              border: `1px solid ${borderColor}`,
            }}>
              <h3 style={{ marginTop: 0, fontSize: '1.15rem' }}>⚠️ Supervisor Override Admission</h3>
              <p style={{ fontSize: '0.85rem', color: textMuted }}>
                Only authorized Help Desk staff and Administrators may grant exceptional admission when resident is unreachable.
                An explicit audit log reason is strictly required.
              </p>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Reason (e.g. Resident verified via intercom telephone)..."
                rows={3}
                style={{
                  width: '100%',
                  padding: '0.6rem',
                  borderRadius: '8px',
                  border: `1px solid ${borderColor}`,
                  background: darkTheme ? '#0F172A' : '#FFFFFF',
                  color: textColor,
                  fontSize: '0.9rem',
                  boxSizing: 'border-box',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.6rem', marginTop: '1rem' }}>
                <button
                  type="button"
                  onClick={() => setOverrideEntryId(null)}
                  style={{
                    minHeight: '48px',
                    padding: '0.5rem 1rem',
                    borderRadius: '8px',
                    border: `1px solid ${borderColor}`,
                    background: 'transparent',
                    color: textColor,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleApplyOverride}
                  disabled={!overrideReason.trim()}
                  style={{
                    minHeight: '48px',
                    padding: '0.5rem 1.2rem',
                    borderRadius: '8px',
                    border: 'none',
                    background: '#9333EA',
                    color: '#FFFFFF',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Confirm Override
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
