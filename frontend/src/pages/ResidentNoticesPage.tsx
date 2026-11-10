import React, { useCallback, useEffect, useState } from 'react';
import { api, NoticeRevisionItem, UserProfile } from '../api/client';
import { Language, translations } from '../i18n/translations';

interface ResidentNoticesPageProps {
  user: UserProfile;
  lang: Language;
}

export const ResidentNoticesPage: React.FC<ResidentNoticesPageProps> = ({ user, lang }) => {
  const t = translations[lang];
  const [notices, setNotices] = useState<NoticeRevisionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setNotices(await api.listActiveNotices(lang));
    } catch (err) {
      setError(err instanceof Error ? err.message : t.notice_error);
    } finally {
      setLoading(false);
    }
  }, [lang, user.id, t.notice_error]);

  useEffect(() => { void load(); }, [load]);

  const markRead = async (notice: NoticeRevisionItem) => {
    setBusyId(notice.id);
    setError(null);
    try {
      await api.markNoticeRead(notice.id);
      setNotices((current) => current.map((item) => item.id === notice.id ? { ...item, is_read: true } : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : t.notice_error);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <main style={{ maxWidth: 820, width: '100%', boxSizing: 'border-box', margin: '1.25rem auto', padding: '0 1rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }}>{t.resident_notices}</h1>
          <p style={{ color: 'var(--text-muted)', margin: '0.4rem 0 1rem' }}>{t.notice_board}</p>
        </div>
        <button type="button" onClick={() => void load()} disabled={loading} style={{ minHeight: 44, padding: '0.5rem 0.9rem' }}>
          {loading ? t.notice_loading : 'Refresh'}
        </button>
      </header>

      {error && <div role="alert" style={{ padding: 12, borderRadius: 8, background: '#FEE2E2', color: '#991B1B', marginBottom: 12 }}>{error}</div>}
      {loading ? (
        <p role="status">{t.notice_loading}</p>
      ) : notices.length === 0 ? (
        <div style={{ padding: '2rem 1rem', textAlign: 'center', border: '1px solid var(--border)', borderRadius: 12, color: 'var(--text-muted)' }}>{t.notice_empty}</div>
      ) : (
        <section aria-label={t.resident_notices} style={{ display: 'grid', gap: 12 }}>
          {notices.map((notice) => {
            const critical = notice.severity === 'CRITICAL';
            return (
              <article key={notice.id} style={{ border: `1px solid ${critical ? '#DC2626' : 'var(--border)'}`, borderLeft: `5px solid ${critical ? '#DC2626' : '#64748B'}`, borderRadius: 10, padding: '1rem', background: critical ? '#FFF7F7' : '#FFFFFF', color: '#172033', overflowWrap: 'anywhere' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  <h2 style={{ fontSize: '1.08rem', margin: 0 }}>{notice.title}</h2>
                  <span style={{ fontSize: '0.75rem', fontWeight: 800, color: critical ? '#B91C1C' : '#475569' }}>{critical ? t.notice_critical : t.notice_normal}</span>
                </div>
                {notice.is_fallback_language && <p style={{ margin: '0.65rem 0 0', fontSize: '0.78rem', fontWeight: 700, color: '#92400E' }}>{notice.fallback_language_label || t.notice_shown_english}</p>}
                <p style={{ margin: '0.7rem 0', whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>{notice.body}</p>
                <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, color: '#64748B', fontSize: '0.76rem' }}>
                  <span>{new Date(notice.publish_at).toLocaleString()}</span>
                  <span>{notice.tower_number ? `Tower ${notice.tower_number}` : t.notice_all}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
                  {notice.is_read ? (
                    <span aria-label={t.notice_read} style={{ color: '#166534', fontWeight: 700, fontSize: '0.85rem' }}>✓ {t.notice_read}</span>
                  ) : (
                    <button type="button" onClick={() => void markRead(notice)} disabled={busyId === notice.id} style={{ minHeight: 44, padding: '0.5rem 0.9rem' }}>
                      {busyId === notice.id ? '…' : t.notice_mark_read}
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
};
