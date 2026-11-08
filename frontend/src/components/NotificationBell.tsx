import React, { useState, useEffect, useRef } from 'react';
import { api, NotificationItem } from '../api/client';
import { Language, translations } from '../i18n/translations';

interface NotificationBellProps {
  lang: Language;
}

export const NotificationBell: React.FC<NotificationBellProps> = ({ lang }) => {
  const t = translations[lang];
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  const fetchUnread = async () => {
    try {
      const res = await api.getUnreadNotificationCount();
      setUnreadCount(res.unread_count);
    } catch {
      // ignore
    }
  };

  const fetchList = async () => {
    setLoading(true);
    try {
      const items = await api.getNotifications(15);
      setNotifications(items);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnread();
    const timer = setInterval(fetchUnread, 30000); // 30s refresh
    return () => clearInterval(timer);
  }, []);

  const toggleOpen = () => {
    if (!isOpen) {
      fetchList();
    }
    setIsOpen(!isOpen);
  };

  const handleMarkAll = async () => {
    try {
      await api.markAllNotificationsRead();
      setUnreadCount(0);
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    } catch {
      // ignore
    }
  };

  const handleItemClick = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await api.markNotificationsRead([notif.id]);
        setUnreadCount(prev => Math.max(0, prev - 1));
        setNotifications(prev => prev.map(n => n.id === notif.id ? { ...n, is_read: true } : n));
      } catch {
        // ignore
      }
    }
  };

  // Close on outside click
  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutside);
    }
    return () => document.removeEventListener('mousedown', handleOutside);
  }, [isOpen]);

  return (
    <div style={{ position: 'relative' }} ref={popoverRef}>
      <button
        onClick={toggleOpen}
        aria-label="Notifications"
        style={{
          position: 'relative',
          background: 'transparent',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          padding: '0.35rem 0.55rem',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1rem',
          color: 'var(--text-main)',
        }}
      >
        🔔
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              background: '#dc2626',
              color: '#ffffff',
              fontSize: '0.65rem',
              fontWeight: 700,
              padding: '1px 5px',
              borderRadius: '10px',
              minWidth: '16px',
              textAlign: 'center',
            }}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            right: 0,
            top: '110%',
            width: '320px',
            maxWidth: '90vw',
            background: '#ffffff',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            zIndex: 100,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.6rem 0.8rem',
              borderBottom: '1px solid var(--border)',
              background: '#f8fafc',
            }}
          >
            <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{t.notifications}</span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAll}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--primary)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {t.mark_all_read}
              </button>
            )}
          </div>

          <div style={{ maxHeight: '340px', overflowY: 'auto' }}>
            {loading ? (
              <div style={{ padding: '1rem', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Loading...
              </div>
            ) : notifications.length === 0 ? (
              <div style={{ padding: '1.5rem', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {t.no_notifications}
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => handleItemClick(n)}
                  style={{
                    padding: '0.6rem 0.8rem',
                    borderBottom: '1px solid #f1f5f9',
                    background: n.is_read ? '#ffffff' : '#f0fdf4',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    borderLeft: n.notification_type === 'SAFETY_ESCALATION' ? '4px solid #dc2626' : undefined,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                    <span style={{ fontWeight: 600, color: n.notification_type === 'SAFETY_ESCALATION' ? '#dc2626' : 'var(--text-main)' }}>
                      {n.title}
                    </span>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                      {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', lineHeight: 1.3 }}>
                    {n.message}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
