import React, { useState, useEffect } from 'react';
import {
  api, ComplaintItem, UserProfile
} from '../api/client';
import { Language, translations } from '../i18n/translations';

interface ResidentComplaintsProps {
  user: UserProfile;
  selectedFlatId: string;
  lang: Language;
}

export const ResidentComplaints: React.FC<ResidentComplaintsProps> = ({
  user,
  selectedFlatId,
  lang,
}) => {
  const t = translations[lang];

  const [complaints, setComplaints] = useState<ComplaintItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // New complaint form state
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [category, setCategory] = useState<string>('GENERAL');
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  // Rating modal state
  const [ratingComplaint, setRatingComplaint] = useState<ComplaintItem | null>(null);
  const [selectedStars, setSelectedStars] = useState<number>(5);
  const [ratingFeedback, setRatingFeedback] = useState<string>('');
  const [ratingSubmitting, setRatingSubmitting] = useState<boolean>(false);

  // Reopen modal state
  const [reopenComplaint, setReopenComplaint] = useState<ComplaintItem | null>(null);
  const [reopenReason, setReopenReason] = useState<string>('');
  const [reopenSubmitting, setReopenSubmitting] = useState<boolean>(false);

  // Photo viewer modal state
  const [signedPhotoUrl, setSignedPhotoUrl] = useState<string | null>(null);

  useEffect(() => {
    loadComplaints();
  }, []);

  const loadComplaints = async () => {
    setLoading(true);
    try {
      const items = await api.getMyComplaints();
      setComplaints(items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      if (f.size > 5 * 1024 * 1024) {
        setFormError('Photo size exceeds 5MB limit');
        return;
      }
      setPhotoFile(f);
      setFormError(null);
    }
  };

  const handleSubmitComplaint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setFormError('Title and description are required');
      return;
    }
    if (!selectedFlatId) {
      setFormError('Please select a flat');
      return;
    }

    setSubmitting(true);
    setFormError(null);
    setFormSuccess(null);

    const formData = new FormData();
    formData.append('flat_id', selectedFlatId);
    formData.append('title', title.trim());
    formData.append('description', description.trim());
    if (category) formData.append('category', category);
    formData.append('language', lang);
    if (photoFile) formData.append('photo', photoFile);

    try {
      const res = await api.raiseComplaint(formData);
      setFormSuccess(`Ticket #${res.ticket_number} created successfully! Assigned to: ${res.assigned_team || 'Maintenance'}`);
      setTitle('');
      setDescription('');
      setPhotoFile(null);
      loadComplaints();
    } catch (err: any) {
      setFormError(err.message || 'Failed to submit complaint');
    } finally {
      setSubmitting(false);
    }
  };

  const submitRating = async () => {
    if (!ratingComplaint) return;
    setRatingSubmitting(true);
    try {
      await api.rateComplaint(ratingComplaint.id, {
        rating: selectedStars,
        feedback: ratingFeedback || undefined,
      });
      setRatingComplaint(null);
      loadComplaints();
    } catch (err: any) {
      alert(`Rating failed: ${err.message}`);
    } finally {
      setRatingSubmitting(false);
    }
  };

  const submitReopen = async () => {
    if (!reopenComplaint || !reopenReason.trim()) return;
    setReopenSubmitting(true);
    try {
      await api.reopenComplaint(reopenComplaint.id, {
        reopen_reason: reopenReason.trim(),
      });
      setReopenComplaint(null);
      loadComplaints();
    } catch (err: any) {
      alert(`Reopen failed: ${err.message}`);
    } finally {
      setReopenSubmitting(false);
    }
  };

  const viewPhoto = async (complaintId: string, attachmentId: string) => {
    try {
      const res = await api.getSignedPhotoUrl(complaintId, attachmentId);
      setSignedPhotoUrl(res.signed_url);
    } catch (e: any) {
      alert(`Could not load photo: ${e.message}`);
    }
  };

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, margin: '0 0 1.2rem 0', color: 'var(--text-main)' }}>
        {t.complaints} • {t.my_complaints}
      </h1>

      {/* Form: Raise New Complaint */}
      <div style={{ background: '#ffffff', borderRadius: '10px', border: '1px solid var(--border)', padding: '1.2rem', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: '0 0 0.8rem 0' }}>
          ➕ {t.raise_complaint}
        </h2>

        {/* Safety Invariant Notice */}
        <div style={{
          padding: '0.6rem 0.8rem', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '6px',
          marginBottom: '1rem', fontSize: '0.8rem', color: '#92400e', lineHeight: 1.4
        }}>
          ⚠️ <strong>Safety Notice:</strong> Hazardous conditions (gas leak, fire/smoke, sparking, lift entrapment) in English, Marathi, or Hindi are automatically detected, assigned <strong>CRITICAL</strong> urgency, and escalated immediately to the 24/7 duty manager.
        </div>

        <form onSubmit={handleSubmitComplaint} style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.2rem' }}>
              {t.complaint_title} *
            </label>
            <input
              type="text"
              placeholder="e.g. Kitchen tap leaking water / गॅसचा वास येत आहे"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              style={{ width: '100%', padding: '0.45rem 0.6rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '180px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                {t.complaint_category}
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                style={{ width: '100%', padding: '0.45rem 0.6rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
              >
                <option value="GENERAL">Auto-Classify (AI Assisted)</option>
                <option value="PLUMBING">PLUMBING (Plumbing & Water)</option>
                <option value="ELECTRICAL">ELECTRICAL (Electrical & Power)</option>
                <option value="LIFT">LIFT (Elevator Maintenance)</option>
                <option value="HOUSEKEEPING">HOUSEKEEPING (Cleaning & Waste)</option>
                <option value="SECURITY">SECURITY (Guards & Access)</option>
                <option value="CARPENTRY">CARPENTRY (Doors & Woodwork)</option>
                <option value="CIVIL">CIVIL (Masonry & Structure)</option>
              </select>
            </div>

            <div style={{ flex: 1, minWidth: '180px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                {t.attach_photo}
              </label>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handlePhotoChange}
                style={{ width: '100%', fontSize: '0.8rem' }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.2rem' }}>
              {t.complaint_description} *
            </label>
            <textarea
              placeholder="Describe the issue in detail (Supports English, मराठी, हिंदी)..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              required
              style={{ width: '100%', padding: '0.45rem 0.6rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
            />
          </div>

          {formError && (
            <div style={{ padding: '0.5rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', color: '#b91c1c', fontSize: '0.8rem' }}>
              {formError}
            </div>
          )}

          {formSuccess && (
            <div style={{ padding: '0.5rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px', color: '#166534', fontSize: '0.8rem' }}>
              {formSuccess}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            style={{
              alignSelf: 'flex-start',
              background: 'var(--primary)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '0.55rem 1.2rem',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: submitting ? 'not-allowed' : 'pointer',
              opacity: submitting ? 0.7 : 1,
            }}
          >
            {submitting ? 'Submitting Ticket...' : `Submit Ticket`}
          </button>
        </form>
      </div>

      {/* Complaints List */}
      <div>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: '0 0 0.8rem 0' }}>
          {t.open_complaints}
        </h2>

        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading complaints...
          </div>
        ) : complaints.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', background: '#ffffff', borderRadius: '8px', border: '1px solid var(--border)' }}>
            No complaints raised for your flat.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            {complaints.map((c) => (
              <div
                key={c.id}
                style={{
                  background: '#ffffff',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  padding: '1rem',
                  borderLeft: c.is_safety_escalation ? '4px solid #dc2626' : undefined,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.4rem' }}>
                  <div>
                    <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.85rem', color: 'var(--primary)', marginRight: '0.5rem' }}>
                      #{c.ticket_number}
                    </span>
                    <strong style={{ fontSize: '0.95rem', color: 'var(--text-main)' }}>{c.title}</strong>
                  </div>

                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                    <span style={{
                      padding: '2px 7px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700,
                      background: c.status === 'RESOLVED' ? '#dcfce7' : c.status === 'IN_PROGRESS' ? '#dbeafe' : '#f1f5f9',
                      color: c.status === 'RESOLVED' ? '#166534' : c.status === 'IN_PROGRESS' ? '#1d4ed8' : '#475569',
                    }}>
                      {c.status}
                    </span>
                    <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600, background: '#f8fafc', color: 'var(--text-muted)' }}>
                      {c.category}
                    </span>
                  </div>
                </div>

                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.6rem', lineHeight: 1.4 }}>
                  {c.description}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <span>Team: <strong>{c.assigned_team || 'General Maintenance'}</strong></span>
                    {c.assigned_staff_name && <span> • Staff: <strong>{c.assigned_staff_name}</strong></span>}
                  </div>

                  <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                    {c.attachments && c.attachments.length > 0 && (
                      <button
                        onClick={() => viewPhoto(c.id, c.attachments![0].id)}
                        style={{ background: 'transparent', border: '1px solid var(--border)', borderRadius: '4px', padding: '2px 6px', fontSize: '0.72rem', cursor: 'pointer' }}
                      >
                        📷 View Photo
                      </button>
                    )}

                    {/* Rating button if resolved */}
                    {c.status === 'RESOLVED' && !c.rating && (
                      <button
                        onClick={() => { setRatingComplaint(c); setSelectedStars(5); setRatingFeedback(''); }}
                        style={{ background: '#16a34a', color: '#fff', border: 'none', borderRadius: '4px', padding: '2px 8px', fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer' }}
                      >
                        ⭐ {t.rate_service}
                      </button>
                    )}

                    {c.rating && (
                      <span style={{ color: '#ca8a04', fontWeight: 700 }}>
                        {'★'.repeat(c.rating)}{'☆'.repeat(5 - c.rating)} ({c.rating}/5)
                      </span>
                    )}

                    {/* Reopen button */}
                    {c.status === 'RESOLVED' && !c.reopen_requested && (
                      <button
                        onClick={() => { setReopenComplaint(c); setReopenReason(''); }}
                        style={{ background: '#f8fafc', border: '1px solid var(--border)', color: '#dc2626', borderRadius: '4px', padding: '2px 8px', fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer' }}
                      >
                        🔄 {t.reopen_ticket}
                      </button>
                    )}

                    {c.reopen_requested && (
                      <span style={{ color: '#ea580c', fontWeight: 600, fontSize: '0.72rem' }}>
                        (Reopen Requested)
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Rating Modal */}
      {ratingComplaint && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 120
        }}>
          <div style={{ background: '#ffffff', borderRadius: '10px', padding: '1.5rem', width: '400px', maxWidth: '90vw' }}>
            <h3 style={{ marginTop: 0, marginBottom: '0.5rem' }}>{t.rate_service}</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0 0 1rem 0' }}>
              Ticket #{ratingComplaint.ticket_number}: {ratingComplaint.title}
            </p>

            <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center', margin: '1rem 0' }}>
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => setSelectedStars(star)}
                  style={{
                    background: 'transparent', border: 'none', fontSize: '2rem', cursor: 'pointer',
                    color: star <= selectedStars ? '#eab308' : '#cbd5e1'
                  }}
                >
                  ★
                </button>
              ))}
            </div>

            <textarea
              placeholder="Comments on resolution quality (optional)..."
              value={ratingFeedback}
              onChange={(e) => setRatingFeedback(e.target.value)}
              rows={2}
              style={{ width: '100%', padding: '0.4rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.8rem', marginBottom: '1rem' }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setRatingComplaint(null)}
                style={{ border: '1px solid var(--border)', background: '#fff', borderRadius: '6px', padding: '0.4rem 0.8rem', fontSize: '0.8rem', cursor: 'pointer' }}
              >
                {t.close}
              </button>
              <button
                onClick={submitRating}
                disabled={ratingSubmitting}
                style={{ background: '#16a34a', color: '#fff', border: 'none', borderRadius: '6px', padding: '0.4rem 1rem', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
              >
                {ratingSubmitting ? 'Submitting...' : 'Submit Rating'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reopen Modal */}
      {reopenComplaint && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 120
        }}>
          <div style={{ background: '#ffffff', borderRadius: '10px', padding: '1.5rem', width: '420px', maxWidth: '90vw' }}>
            <h3 style={{ marginTop: 0, marginBottom: '0.5rem' }}>{t.reopen_ticket}</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0 0 1rem 0' }}>
              Ticket #{reopenComplaint.ticket_number}: {reopenComplaint.title}
            </p>

            <textarea
              placeholder="Why does this issue need to be reopened? (Required)..."
              value={reopenReason}
              onChange={(e) => setReopenReason(e.target.value)}
              rows={3}
              required
              style={{ width: '100%', padding: '0.4rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.8rem', marginBottom: '1rem' }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setReopenComplaint(null)}
                style={{ border: '1px solid var(--border)', background: '#fff', borderRadius: '6px', padding: '0.4rem 0.8rem', fontSize: '0.8rem', cursor: 'pointer' }}
              >
                {t.close}
              </button>
              <button
                onClick={submitReopen}
                disabled={reopenSubmitting || !reopenReason.trim()}
                style={{ background: '#dc2626', color: '#fff', border: 'none', borderRadius: '6px', padding: '0.4rem 1rem', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
              >
                {reopenSubmitting ? 'Requesting...' : 'Request Reopen'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Signed Photo Viewer Modal */}
      {signedPhotoUrl && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 130
        }}>
          <div style={{ background: '#ffffff', borderRadius: '10px', padding: '1rem', maxWidth: '90vw', maxHeight: '90vh', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <img
              src={signedPhotoUrl}
              alt="Complaint Attachment"
              style={{ maxWidth: '100%', maxHeight: '75vh', objectFit: 'contain', borderRadius: '6px' }}
            />
            <button
              onClick={() => setSignedPhotoUrl(null)}
              style={{ marginTop: '0.8rem', background: '#334155', color: '#fff', border: 'none', borderRadius: '6px', padding: '0.4rem 1.2rem', fontSize: '0.85rem', cursor: 'pointer' }}
            >
              {t.close}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
