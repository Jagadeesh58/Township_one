import React, { FormEvent, useCallback, useEffect, useState } from 'react';
import { api, ManagedNoticeItem, NoticeRevisionItem, UserProfile } from '../api/client';
import { Language, translations } from '../i18n/translations';

interface CommitteeNoticeEditorProps {
  user: UserProfile;
  lang: Language;
}

type Audience = 'ALL' | 'TOWER';
type Severity = 'NORMAL' | 'CRITICAL';

function toLocalInput(value?: string): string {
  if (!value) return '';
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

export const CommitteeNoticeEditor: React.FC<CommitteeNoticeEditorProps> = ({ user, lang }) => {
  const t = translations[lang];
  const [items, setItems] = useState<ManagedNoticeItem[]>([]);
  const [selected, setSelected] = useState<ManagedNoticeItem | null>(null);
  const [revisions, setRevisions] = useState<NoticeRevisionItem[]>([]);
  const [title, setTitle] = useState('');
  const [bodyEn, setBodyEn] = useState('');
  const [bodyHi, setBodyHi] = useState('');
  const [bodyMr, setBodyMr] = useState('');
  const [audience, setAudience] = useState<Audience>('ALL');
  const [towerId, setTowerId] = useState('');
  const [severity, setSeverity] = useState<Severity>('NORMAL');
  const [publishAt, setPublishAt] = useState(toLocalInput(new Date().toISOString()));
  const [expiresAt, setExpiresAt] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.listManagedNotices(lang);
      setItems(result);
      if (selected) {
        const refreshed = result.find((item) => item.id === selected.id) ?? null;
        setSelected(refreshed);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t.notice_error);
    } finally {
      setLoading(false);
    }
  }, [lang, selected?.id, user.id, t.notice_error]);

  useEffect(() => { void load(); }, [load]);

  const startNew = () => {
    setSelected(null);
    setRevisions([]);
    setTitle('');
    setBodyEn('');
    setBodyHi('');
    setBodyMr('');
    setAudience('ALL');
    setTowerId('');
    setSeverity('NORMAL');
    setPublishAt(toLocalInput(new Date().toISOString()));
    setExpiresAt('');
    setMessage(null);
  };

  const selectItem = async (item: ManagedNoticeItem) => {
    setSelected(item);
    const current = item.current_revision;
    setTitle(current.title);
    setBodyEn(current.body_en);
    setBodyHi(current.body_hi || '');
    setBodyMr(current.body_mr || '');
    setAudience(current.audience as Audience);
    setTowerId(current.tower_id || '');
    setSeverity(current.severity as Severity);
    setPublishAt(toLocalInput(current.publish_at));
    setExpiresAt(toLocalInput(current.expires_at));
    setMessage(null);
    try {
      setRevisions(await api.getNoticeRevisions(item.id, lang));
    } catch (err) {
      setError(err instanceof Error ? err.message : t.notice_error);
    }
  };

  const saveDraft = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const payload = {
        title: title.trim(),
        body_en: bodyEn.trim(),
        body_hi: bodyHi.trim() || undefined,
        body_mr: bodyMr.trim() || undefined,
        audience,
        tower_id: audience === 'TOWER' ? towerId.trim() : undefined,
        severity,
        publish_at: publishAt ? new Date(publishAt).toISOString() : undefined,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
      };
      if (selected) {
        await api.updateNotice(selected.id, payload);
      } else {
        await api.createNotice({ ...payload, status: 'DRAFT' });
      }
      setMessage(t.notice_saved);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.notice_error);
    } finally {
      setSaving(false);
    }
  };

  const publish = async () => {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      await api.publishNotice(selected.id);
      setMessage(t.notice_published);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.notice_error);
    } finally {
      setSaving(false);
    }
  };

  const withdraw = async () => {
    if (!selected || !window.confirm(t.withdraw_notice + '?')) return;
    setSaving(true);
    setError(null);
    try {
      await api.withdrawNotice(selected.id);
      setMessage(t.notice_withdrawn);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.notice_error);
    } finally {
      setSaving(false);
    }
  };

  const fieldStyle: React.CSSProperties = { width: '100%', boxSizing: 'border-box', minHeight: 42, border: '1px solid var(--border)', borderRadius: 7, padding: '0.55rem 0.65rem', font: 'inherit' };
  const labelStyle: React.CSSProperties = { display: 'grid', gap: 5, fontSize: '0.85rem', fontWeight: 650 };

  return (
    <main style={{ maxWidth: 1100, margin: '1.25rem auto', padding: '0 1rem', width: '100%', boxSizing: 'border-box' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }}>{t.manage_notices}</h1>
          <p style={{ margin: '0.35rem 0', color: 'var(--text-muted)' }}>Committee notices, audience targeting and revision history</p>
        </div>
        <button type="button" onClick={startNew} style={{ minHeight: 44, padding: '0.5rem 0.9rem' }}>+ {t.create_draft}</button>
      </header>

      {error && <div role="alert" style={{ marginBottom: 12, padding: 12, borderRadius: 8, background: '#FEE2E2', color: '#991B1B' }}>{error}</div>}
      {message && <div role="status" style={{ marginBottom: 12, padding: 12, borderRadius: 8, background: '#DCFCE7', color: '#166534' }}>{message}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 16, alignItems: 'start' }}>
        <section style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 12, minWidth: 0 }}>
          <h2 style={{ margin: '0 0 10px', fontSize: '1rem' }}>Notices</h2>
          {loading ? <p role="status">{t.notice_loading}</p> : items.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>{t.notice_empty}</p> : (
            <div style={{ display: 'grid', gap: 8 }}>
              {items.map((item) => (
                <button key={item.id} type="button" onClick={() => void selectItem(item)} style={{ textAlign: 'left', border: selected?.id === item.id ? '2px solid var(--primary)' : '1px solid var(--border)', borderRadius: 8, padding: 10, background: '#fff', minWidth: 0 }}>
                  <strong style={{ display: 'block', overflowWrap: 'anywhere' }}>{item.current_revision.title}</strong>
                  <span style={{ display: 'block', fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: 4 }}>{item.status} · {item.revision_count} revisions</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 14, minWidth: 0 }}>
          <h2 style={{ margin: '0 0 12px', fontSize: '1rem' }}>{selected ? 'Edit notice' : t.create_draft}</h2>
          <form onSubmit={saveDraft} style={{ display: 'grid', gap: 10 }}>
            <label style={labelStyle}>{t.notice_title}<input style={fieldStyle} value={title} onChange={(e) => setTitle(e.target.value)} minLength={3} required /></label>
            <label style={labelStyle}>{t.notice_body_en}<textarea style={{ ...fieldStyle, minHeight: 90 }} value={bodyEn} onChange={(e) => setBodyEn(e.target.value)} minLength={5} required /></label>
            <label style={labelStyle}>{t.notice_body_hi}<textarea style={{ ...fieldStyle, minHeight: 70 }} value={bodyHi} onChange={(e) => setBodyHi(e.target.value)} /></label>
            <label style={labelStyle}>{t.notice_body_mr}<textarea style={{ ...fieldStyle, minHeight: 70 }} value={bodyMr} onChange={(e) => setBodyMr(e.target.value)} /></label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))', gap: 10 }}>
              <label style={labelStyle}>{t.notice_audience}<select style={fieldStyle} value={audience} onChange={(e) => setAudience(e.target.value as Audience)}><option value="ALL">{t.notice_all}</option><option value="TOWER">{t.notice_tower}</option></select></label>
              <label style={labelStyle}>{t.notice_severity}<select style={fieldStyle} value={severity} onChange={(e) => setSeverity(e.target.value as Severity)}><option value="NORMAL">{t.notice_normal}</option><option value="CRITICAL">{t.notice_critical}</option></select></label>
            </div>
            {audience === 'TOWER' && <label style={labelStyle}>{t.notice_tower_id}<input style={fieldStyle} value={towerId} onChange={(e) => setTowerId(e.target.value)} required /></label>}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
              <label style={labelStyle}>{t.notice_publish_at}<input style={fieldStyle} type="datetime-local" value={publishAt} onChange={(e) => setPublishAt(e.target.value)} required /></label>
              <label style={labelStyle}>{t.notice_expires_at}<input style={fieldStyle} type="datetime-local" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} /></label>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 8 }}>
              {selected && selected.status === 'DRAFT' && <button type="button" onClick={() => void publish()} disabled={saving} style={{ minHeight: 44, padding: '0.5rem 0.9rem' }}>{t.publish_notice}</button>}
              {selected && selected.status === 'PUBLISHED' && <button type="button" onClick={() => void withdraw()} disabled={saving} style={{ minHeight: 44, padding: '0.5rem 0.9rem' }}>{t.withdraw_notice}</button>}
              <button type="submit" disabled={saving} style={{ minHeight: 44, padding: '0.5rem 1rem', background: 'var(--primary)', color: '#fff', border: 0, borderRadius: 7 }}>{saving ? 'Saving…' : t.create_draft}</button>
            </div>
          </form>

          {selected && (
            <div style={{ marginTop: 20, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
              <h3 style={{ margin: '0 0 8px', fontSize: '0.95rem' }}>{t.notice_revision_history}</h3>
              {revisions.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>No revision history.</p> : revisions.map((revision) => (
                <article key={revision.id} style={{ padding: 9, border: '1px solid var(--border)', borderRadius: 7, marginBottom: 7 }}>
                  <strong>Revision {revision.revision_number}: {revision.title}</strong>
                  <p style={{ margin: '4px 0', fontSize: '0.82rem', whiteSpace: 'pre-wrap' }}>{revision.body_en}</p>
                  <small style={{ color: 'var(--text-muted)' }}>{new Date(revision.created_at).toLocaleString()}</small>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
};
