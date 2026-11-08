import React, { useState, useEffect } from 'react';
import {
  api, ComplaintItem, SafetyEventItem, UserProfile
} from '../api/client';
import { Language, translations } from '../i18n/translations';

interface HelpDeskQueueProps {
  user: UserProfile;
  lang: Language;
}

export const HelpDeskQueue: React.FC<HelpDeskQueueProps> = ({ user, lang }) => {
  const t = translations[lang];

  // Queue state
  const [tickets, setTickets] = useState<ComplaintItem[]>([]);
  const [totalTickets, setTotalTickets] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [urgencyFilter, setUrgencyFilter] = useState<string>('');
  const [towerFilter, setTowerFilter] = useState<string>('');
  const [overdueOnly, setOverdueOnly] = useState<boolean>(false);

  // Safety Events
  const [safetyEvents, setSafetyEvents] = useState<SafetyEventItem[]>([]);

  // Selected Ticket Drawer
  const [selectedTicket, setSelectedTicket] = useState<ComplaintItem | null>(null);
  const [drawerLoading, setDrawerLoading] = useState<boolean>(false);

  // Correction Form
  const [editCategory, setEditCategory] = useState<string>('');
  const [editUrgency, setEditUrgency] = useState<string>('');
  const [editReason, setEditReason] = useState<string>('');
  const [correctionSubmitting, setCorrectionSubmitting] = useState<boolean>(false);
  const [correctionError, setCorrectionError] = useState<string | null>(null);

  // Transition Form
  const [transitionNotes, setTransitionNotes] = useState<string>('');
  const [transitionSubmitting, setTransitionSubmitting] = useState<boolean>(false);
  const [transitionError, setTransitionError] = useState<string | null>(null);

  // Duplicates
  const [duplicateCandidates, setDuplicateCandidates] = useState<any[]>([]);
  const [linkingCandidateId, setLinkingCandidateId] = useState<string | null>(null);

  useEffect(() => {
    loadSafetyEvents();
    loadQueue();
  }, [statusFilter, categoryFilter, urgencyFilter, towerFilter, overdueOnly, page]);

  const loadSafetyEvents = async () => {
    try {
      const events = await api.getActiveSafetyEvents();
      setSafetyEvents(events);
    } catch (e) {
      console.error(e);
    }
  };

  const loadQueue = async () => {
    setLoading(true);
    try {
      const res = await api.getHelpdeskQueue({
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        urgency: urgencyFilter || undefined,
        tower_id: towerFilter || undefined,
        overdue_only: overdueOnly || undefined,
        page,
      });
      setTickets(res.items);
      setTotalTickets(res.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const openTicketDrawer = async (ticket: ComplaintItem) => {
    setSelectedTicket(ticket);
    setEditCategory(ticket.category);
    setEditUrgency(ticket.urgency);
    setEditReason('');
    setCorrectionError(null);
    setTransitionError(null);
    setDrawerLoading(true);
    try {
      const detail = await api.getComplaintDetail(ticket.id);
      setSelectedTicket(detail);
      // Fetch duplicate candidates
      const dupRes = await api.getDuplicateCandidates(ticket.id);
      setDuplicateCandidates(dupRes.candidates || []);
    } catch (e) {
      console.error(e);
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleSafetyAction = async (eventId: string, action: 'ACKNOWLEDGE' | 'DISMISS') => {
    try {
      await api.acknowledgeSafetyEvent(eventId, action);
      loadSafetyEvents();
      loadQueue();
    } catch (e) {
      console.error(e);
    }
  };

  const handleCorrectClassification = async () => {
    if (!selectedTicket) return;
    setCorrectionSubmitting(true);
    setCorrectionError(null);
    try {
      const updated = await api.correctComplaintClassification(selectedTicket.id, {
        expected_version: selectedTicket.version,
        category: editCategory,
        urgency: editUrgency,
        reason: editReason || `Corrected by ${user.name}`,
      });
      setSelectedTicket(updated);
      loadQueue();
    } catch (err: any) {
      setCorrectionError(err.message || 'Correction failed');
    } finally {
      setCorrectionSubmitting(false);
    }
  };

  const handleTransition = async (targetStatus: string) => {
    if (!selectedTicket) return;
    setTransitionSubmitting(true);
    setTransitionError(null);
    try {
      const updated = await api.transitionComplaintStatus(selectedTicket.id, {
        status: targetStatus,
        notes: transitionNotes || `Status updated to ${targetStatus}`,
        expected_version: selectedTicket.version,
      });
      setSelectedTicket(updated);
      setTransitionNotes('');
      loadQueue();
    } catch (err: any) {
      setTransitionError(err.message || 'Transition failed');
    } finally {
      setTransitionSubmitting(false);
    }
  };

  const handleLinkDuplicate = async (targetComplaintId: string) => {
    if (!selectedTicket) return;
    setLinkingCandidateId(targetComplaintId);
    try {
      await api.linkDuplicateComplaint(selectedTicket.id, targetComplaintId);
      // Reload drawer
      openTicketDrawer(selectedTicket);
    } catch (err: any) {
      alert(`Linking failed: ${err.message}`);
    } finally {
      setLinkingCandidateId(null);
    }
  };

  const getUrgencyBadge = (urgency: string) => {
    let bg = '#f1f5f9';
    let color = '#475569';
    if (urgency === 'CRITICAL') { bg = '#fee2e2'; color = '#b91c1c'; }
    else if (urgency === 'HIGH') { bg = '#ffedd5'; color = '#c2410c'; }
    else if (urgency === 'MEDIUM') { bg = '#fef9c3'; color = '#a16207'; }
    else if (urgency === 'LOW') { bg = '#f0fdf4'; color = '#15803d'; }

    return (
      <span style={{ padding: '2px 7px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700, background: bg, color }}>
        {urgency}
      </span>
    );
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.8rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
            {t.helpdesk_queue}
          </h1>
          <p style={{ margin: '0.2rem 0 0 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Resident Complaints Triage • AI Classification • Incident Grouping • SLA Tracking
          </p>
        </div>

        <button
          onClick={() => { loadSafetyEvents(); loadQueue(); }}
          style={{
            background: '#f8fafc',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            padding: '0.4rem 0.8rem',
            fontSize: '0.85rem',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          🔄 Refresh
        </button>
      </div>

      {/* Safety Escalation Alert Banner */}
      {safetyEvents.length > 0 && (
        <div style={{
          background: '#fef2f2', border: '2px solid #ef4444', borderRadius: '8px', padding: '1rem',
          marginBottom: '1.5rem', boxShadow: '0 4px 12px rgba(239, 68, 68, 0.15)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '1.2rem' }}>🚨</span>
            <strong style={{ color: '#991b1b', fontSize: '0.95rem' }}>
              {t.safety_escalation_alert} ({safetyEvents.length} Active Incidents)
            </strong>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {safetyEvents.map((ev) => (
              <div key={ev.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#ffffff', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid #fecaca', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div>
                  <span style={{ fontWeight: 700, color: '#b91c1c', marginRight: '0.5rem' }}>[{ev.event_type}]</span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-main)' }}>Ticket #{ev.ticket_number || 'N/A'} (Flat {ev.flat_number || 'N/A'}): {ev.details}</span>
                </div>
                <div style={{ display: 'flex', gap: '0.4rem' }}>
                  <button
                    onClick={() => handleSafetyAction(ev.id, 'ACKNOWLEDGE')}
                    style={{ background: '#16a34a', color: '#fff', border: 'none', borderRadius: '4px', padding: '3px 8px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                  >
                    {t.acknowledge}
                  </button>
                  <button
                    onClick={() => handleSafetyAction(ev.id, 'DISMISS')}
                    style={{ background: '#64748b', color: '#fff', border: 'none', borderRadius: '4px', padding: '3px 8px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                  >
                    {t.dismiss}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <div style={{ background: '#ffffff', border: '1px solid var(--border)', borderRadius: '8px', padding: '0.8rem 1rem', marginBottom: '1.2rem', display: 'flex', gap: '0.8rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Status</label>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            style={{ padding: '0.35rem 0.6rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.82rem' }}
          >
            <option value="">All Statuses</option>
            <option value="SUBMITTED">SUBMITTED</option>
            <option value="ASSIGNED">ASSIGNED</option>
            <option value="IN_PROGRESS">IN_PROGRESS</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="CLOSED">CLOSED</option>
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Category</label>
          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
            style={{ padding: '0.35rem 0.6rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.82rem' }}
          >
            <option value="">All Categories</option>
            <option value="PLUMBING">PLUMBING</option>
            <option value="ELECTRICAL">ELECTRICAL</option>
            <option value="LIFT">LIFT</option>
            <option value="HOUSEKEEPING">HOUSEKEEPING</option>
            <option value="SECURITY">SECURITY</option>
            <option value="CARPENTRY">CARPENTRY</option>
            <option value="CIVIL">CIVIL</option>
            <option value="GENERAL">GENERAL</option>
          </select>
        </div>

        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Urgency</label>
          <select
            value={urgencyFilter}
            onChange={(e) => { setUrgencyFilter(e.target.value); setPage(1); }}
            style={{ padding: '0.35rem 0.6rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.82rem' }}
          >
            <option value="">All Urgencies</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '1rem' }}>
          <input
            type="checkbox"
            id="overdueOnly"
            checked={overdueOnly}
            onChange={(e) => { setOverdueOnly(e.target.checked); setPage(1); }}
          />
          <label htmlFor="overdueOnly" style={{ fontSize: '0.82rem', fontWeight: 600, color: '#dc2626', cursor: 'pointer' }}>
            Overdue SLA Only
          </label>
        </div>
      </div>

      {/* Ticket List Table */}
      <div style={{ background: '#ffffff', borderRadius: '10px', border: '1px solid var(--border)', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading complaints queue...
          </div>
        ) : tickets.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No tickets match the selected filters.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ background: '#f8fafc', borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Ticket</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Flat</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Title & Description</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Category</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Urgency</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Status</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>SLA Status</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Assigned Team</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((tkt) => (
                  <tr
                    key={tkt.id}
                    onClick={() => openTicketDrawer(tkt)}
                    style={{
                      borderBottom: '1px solid #f1f5f9',
                      cursor: 'pointer',
                      background: tkt.is_safety_escalation ? '#fef2f2' : undefined,
                    }}
                  >
                    <td style={{ padding: '0.55rem 0.8rem', fontFamily: 'monospace', fontWeight: 700, color: 'var(--primary)' }}>
                      {tkt.ticket_number}
                    </td>
                    <td style={{ padding: '0.55rem 0.8rem', fontWeight: 600 }}>{tkt.flat_number || '-'}</td>
                    <td style={{ padding: '0.55rem 0.8rem', maxWidth: '300px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {tkt.title}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {tkt.description}
                      </div>
                    </td>
                    <td style={{ padding: '0.55rem 0.8rem' }}>
                      <span style={{ padding: '2px 6px', borderRadius: '4px', background: '#f1f5f9', fontSize: '0.72rem', fontWeight: 600 }}>
                        {tkt.category}
                      </span>
                    </td>
                    <td style={{ padding: '0.55rem 0.8rem' }}>{getUrgencyBadge(tkt.urgency)}</td>
                    <td style={{ padding: '0.55rem 0.8rem' }}>
                      <span style={{
                        padding: '2px 6px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600,
                        background: tkt.status === 'RESOLVED' ? '#dcfce7' : tkt.status === 'IN_PROGRESS' ? '#dbeafe' : '#f1f5f9',
                        color: tkt.status === 'RESOLVED' ? '#166534' : tkt.status === 'IN_PROGRESS' ? '#1d4ed8' : '#475569',
                      }}>
                        {tkt.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.55rem 0.8rem' }}>
                      {tkt.sla_response_breached || tkt.sla_resolution_breached ? (
                        <span style={{ padding: '2px 6px', borderRadius: '4px', background: '#fee2e2', color: '#b91c1c', fontSize: '0.7rem', fontWeight: 700 }}>
                          ⚠️ BREACHED
                        </span>
                      ) : tkt.sla_resolution_time_remaining_hours !== undefined ? (
                        <span style={{ fontSize: '0.75rem', color: '#15803d' }}>
                          ⏱️ {tkt.sla_resolution_time_remaining_hours}h left
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>-</span>
                      )}
                    </td>
                    <td style={{ padding: '0.55rem 0.8rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {tkt.assigned_team || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Ticket Details & Triage Drawer Modal */}
      {selectedTicket && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'flex-end', zIndex: 110
        }}>
          <div style={{
            background: '#ffffff', width: '560px', maxWidth: '95vw', height: '100%',
            overflowY: 'auto', padding: '1.5rem', boxShadow: '-4px 0 24px rgba(0,0,0,0.15)', display: 'flex', flexDirection: 'column', gap: '1.2rem'
          }}>
            {/* Drawer Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border)', paddingBottom: '0.8rem' }}>
              <div>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.9rem', color: 'var(--primary)' }}>
                  #{selectedTicket.ticket_number} (v{selectedTicket.version})
                </span>
                <h2 style={{ fontSize: '1.2rem', margin: '0.2rem 0', fontWeight: 700 }}>
                  {selectedTicket.title}
                </h2>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Flat {selectedTicket.flat_number || 'N/A'} • Lodged {new Date(selectedTicket.created_at).toLocaleString()}
                </div>
              </div>
              <button
                onClick={() => setSelectedTicket(null)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.4rem', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                ✕
              </button>
            </div>

            {/* Description */}
            <div style={{ background: '#f8fafc', padding: '0.8rem', borderRadius: '6px', fontSize: '0.85rem', lineHeight: 1.4 }}>
              <strong>Description:</strong> {selectedTicket.description}
            </div>

            {/* AI Triage Evidence Card */}
            {selectedTicket.decisions && selectedTicket.decisions.length > 0 && (
              <div style={{ border: '1px solid #bfdbfe', background: '#eff6ff', borderRadius: '8px', padding: '0.8rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#1e40af' }}>
                    🤖 {t.ai_triage_evidence}
                  </span>
                  {selectedTicket.decisions[0].fallback_used ? (
                    <span style={{ background: '#fef3c7', color: '#92400e', padding: '2px 6px', borderRadius: '4px', fontSize: '0.68rem', fontWeight: 700 }}>
                      {t.fallback_active}
                    </span>
                  ) : (
                    <span style={{ background: '#dcfce7', color: '#166534', padding: '2px 6px', borderRadius: '4px', fontSize: '0.68rem', fontWeight: 700 }}>
                      Online AI Active
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '0.78rem', color: '#1e3a8a', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  <div>Provider: <strong>{selectedTicket.decisions[0].actor_type}</strong> (Model: {selectedTicket.decisions[0].model_version || 'v1.0'})</div>
                  <div>Predicted: <strong>{selectedTicket.decisions[0].predicted_category}</strong> • Urgency: <strong>{selectedTicket.decisions[0].predicted_urgency}</strong></div>
                  <div>Confidence: <strong>{((selectedTicket.decisions[0].confidence || 0.8) * 100).toFixed(1)}%</strong></div>
                </div>
              </div>
            )}

            {/* One-Tap Classification Correction */}
            <div style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '0.8rem' }}>
              <h3 style={{ fontSize: '0.9rem', margin: '0 0 0.5rem 0', fontWeight: 600 }}>
                Help Desk One-Tap Correction
              </h3>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <select
                  value={editCategory}
                  onChange={(e) => setEditCategory(e.target.value)}
                  style={{ flex: 1, padding: '0.35rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.8rem' }}
                >
                  <option value="PLUMBING">PLUMBING</option>
                  <option value="ELECTRICAL">ELECTRICAL</option>
                  <option value="LIFT">LIFT</option>
                  <option value="HOUSEKEEPING">HOUSEKEEPING</option>
                  <option value="SECURITY">SECURITY</option>
                  <option value="CARPENTRY">CARPENTRY</option>
                  <option value="CIVIL">CIVIL</option>
                  <option value="GENERAL">GENERAL</option>
                </select>

                <select
                  value={editUrgency}
                  onChange={(e) => setEditUrgency(e.target.value)}
                  disabled={selectedTicket.is_safety_escalation}
                  style={{ flex: 1, padding: '0.35rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.8rem' }}
                >
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>

              <input
                type="text"
                placeholder="Reason for correction..."
                value={editReason}
                onChange={(e) => setEditReason(e.target.value)}
                style={{ width: '100%', padding: '0.35rem 0.5rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.8rem', marginBottom: '0.5rem' }}
              />

              {correctionError && (
                <div style={{ color: '#b91c1c', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
                  {correctionError}
                </div>
              )}

              <button
                onClick={handleCorrectClassification}
                disabled={correctionSubmitting}
                style={{
                  background: 'var(--primary)', color: '#fff', border: 'none', borderRadius: '6px',
                  padding: '0.4rem 0.8rem', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer'
                }}
              >
                {correctionSubmitting ? 'Saving...' : 'Apply Correction (Optimistic Lock)'}
              </button>
            </div>

            {/* Lifecycle Status Transitions */}
            <div style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '0.8rem' }}>
              <h3 style={{ fontSize: '0.9rem', margin: '0 0 0.5rem 0', fontWeight: 600 }}>
                Status Transitions (Current: {selectedTicket.status})
              </h3>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                {selectedTicket.status === 'SUBMITTED' && (
                  <button
                    onClick={() => handleTransition('ASSIGNED')}
                    disabled={transitionSubmitting}
                    style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', padding: '4px 8px', fontSize: '0.78rem', cursor: 'pointer', fontWeight: 600 }}
                  >
                    Assign Staff
                  </button>
                )}
                {['SUBMITTED', 'ASSIGNED'].includes(selectedTicket.status) && (
                  <button
                    onClick={() => handleTransition('IN_PROGRESS')}
                    disabled={transitionSubmitting}
                    style={{ background: '#0284c7', color: '#fff', border: 'none', borderRadius: '4px', padding: '4px 8px', fontSize: '0.78rem', cursor: 'pointer', fontWeight: 600 }}
                  >
                    Start Work (IN_PROGRESS)
                  </button>
                )}
                {selectedTicket.status === 'IN_PROGRESS' && (
                  <button
                    onClick={() => handleTransition('RESOLVED')}
                    disabled={transitionSubmitting}
                    style={{ background: '#16a34a', color: '#fff', border: 'none', borderRadius: '4px', padding: '4px 8px', fontSize: '0.78rem', cursor: 'pointer', fontWeight: 600 }}
                  >
                    Mark RESOLVED
                  </button>
                )}
                {selectedTicket.status === 'RESOLVED' && (
                  <button
                    onClick={() => handleTransition('CLOSED')}
                    disabled={transitionSubmitting}
                    style={{ background: '#475569', color: '#fff', border: 'none', borderRadius: '4px', padding: '4px 8px', fontSize: '0.78rem', cursor: 'pointer', fontWeight: 600 }}
                  >
                    Close Ticket
                  </button>
                )}
              </div>

              <input
                type="text"
                placeholder="Transition notes (optional)..."
                value={transitionNotes}
                onChange={(e) => setTransitionNotes(e.target.value)}
                style={{ width: '100%', padding: '0.35rem 0.5rem', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.8rem' }}
              />

              {transitionError && (
                <div style={{ color: '#b91c1c', fontSize: '0.75rem', marginTop: '0.4rem' }}>
                  {transitionError}
                </div>
              )}
            </div>

            {/* Potential Duplicate Tickets */}
            {duplicateCandidates.length > 0 && (
              <div style={{ border: '1px solid #fed7aa', background: '#fff7ed', borderRadius: '8px', padding: '0.8rem' }}>
                <h3 style={{ fontSize: '0.85rem', margin: '0 0 0.4rem 0', color: '#9a3412', fontWeight: 700 }}>
                  👯 {t.duplicate_tickets} (Same Tower)
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {duplicateCandidates.map((cand) => (
                    <div key={cand.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#ffffff', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ffedd5' }}>
                      <div style={{ fontSize: '0.78rem' }}>
                        <span style={{ fontWeight: 700, marginRight: '0.3rem' }}>#{cand.ticket_number}</span>
                        <span>{cand.title}</span>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                          Similarity: {(cand.similarity_score * 100).toFixed(0)}%
                        </div>
                      </div>
                      <button
                        onClick={() => handleLinkDuplicate(cand.id)}
                        disabled={linkingCandidateId === cand.id}
                        style={{
                          background: '#ea580c', color: '#fff', border: 'none', borderRadius: '4px',
                          padding: '3px 7px', fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer'
                        }}
                      >
                        {linkingCandidateId === cand.id ? 'Linking...' : t.link_incident}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Timeline */}
            {selectedTicket.events && selectedTicket.events.length > 0 && (
              <div>
                <h3 style={{ fontSize: '0.85rem', margin: '0 0 0.4rem 0', fontWeight: 600 }}>
                  Audit Timeline
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {selectedTicket.events.map((ev) => (
                    <div key={ev.id} style={{ fontSize: '0.75rem', padding: '0.4rem 0.6rem', background: '#f8fafc', borderRadius: '4px', borderLeft: '3px solid var(--primary)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
                        <span>{ev.event_type} {ev.to_status ? `-> ${ev.to_status}` : ''}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>{new Date(ev.created_at).toLocaleString()}</span>
                      </div>
                      {ev.notes && <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>{ev.notes}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
