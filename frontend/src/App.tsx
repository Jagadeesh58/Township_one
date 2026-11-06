import React, { useState, useEffect } from 'react';
import { api, UserProfile } from './api/client';
import { Language } from './i18n/translations';
import { Navbar } from './components/Navbar';
import { LoginPage } from './pages/LoginPage';
import { ResidentHomePage } from './pages/ResidentHomePage';

export default function App() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [selectedFlatId, setSelectedFlatId] = useState<string>('');
  const [currentLang, setCurrentLang] = useState<Language>('en');
  const [loading, setLoading] = useState<boolean>(true);

  // Check existing session
  useEffect(() => {
    const initSession = async () => {
      const token = api.getAuthToken();
      if (token) {
        try {
          const profile = await api.getMe();
          setUser(profile);
          if (profile.flats && profile.flats.length > 0) {
            setSelectedFlatId(profile.flats[0].flat_id);
          }
        } catch (e) {
          api.clearAuthToken();
          setUser(null);
        }
      }
      setLoading(false);
    };
    initSession();

    // Register Service Worker for PWA
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch((err) => {
        console.log('SW registration skipped:', err);
      });
    }
  }, []);

  const handleLoginSuccess = (profile: UserProfile) => {
    setUser(profile);
    if (profile.flats && profile.flats.length > 0) {
      setSelectedFlatId(profile.flats[0].flat_id);
    }
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    setSelectedFlatId('');
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading Township One...
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        user={user}
        currentLang={currentLang}
        onLanguageChange={setCurrentLang}
        onLogout={handleLogout}
        selectedFlatId={selectedFlatId}
        onSelectFlat={setSelectedFlatId}
      />

      <main style={{ flex: 1, paddingBottom: '2rem' }}>
        {!user ? (
          <LoginPage
            lang={currentLang}
            onLoginSuccess={handleLoginSuccess}
          />
        ) : (
          <ResidentHomePage
            user={user}
            selectedFlatId={selectedFlatId}
            lang={currentLang}
          />
        )}
      </main>

      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '1rem',
        textAlign: 'center',
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        background: '#ffffff'
      }}>
        Township One • Client: Company A, Pune • 2,400 flats / 28 towers / 180 staff / 4 gates • Day 1 Build
      </footer>
    </div>
  );
}
