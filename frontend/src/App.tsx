import React, { useState, useEffect } from 'react';
import { api, UserProfile } from './api/client';
import { Language } from './i18n/translations';
import { Navbar, NavTab } from './components/Navbar';
import { LoginPage } from './pages/LoginPage';
import { ResidentHomePage } from './pages/ResidentHomePage';
import { ResidentComplaints } from './pages/ResidentComplaints';
import { AccountsWorkspace } from './pages/AccountsWorkspace';
import { HelpDeskQueue } from './pages/HelpDeskQueue';
import { AmenityBookingPage } from './pages/AmenityBookingPage';
import { GuardGateTerminal } from './pages/GuardGateTerminal';
import { CommitteeDashboard } from './pages/CommitteeDashboard';

export default function App() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [selectedFlatId, setSelectedFlatId] = useState<string>('');
  const [currentLang, setCurrentLang] = useState<Language>('en');
  const [activeTab, setActiveTab] = useState<NavTab>('home');
  const [loading, setLoading] = useState<boolean>(true);

  const determineDefaultTab = (profile: UserProfile): NavTab => {
    const roles = profile.roles.map((r) => r.role_code);
    if (roles.includes('GUARD')) {
      return 'guard';
    }
    if (roles.includes('COMMITTEE') && (!profile.flats || profile.flats.length === 0)) {
      return 'committee';
    }
    if (profile.flats && profile.flats.length > 0) {
      return 'home';
    }
    if (roles.includes('ACCOUNTS')) {
      return 'accounts';
    }
    if (roles.includes('HELPDESK') || roles.includes('MANAGEMENT')) {
      return 'helpdesk';
    }
    return 'home';
  };

  // Check existing session
  useEffect(() => {
    const initSession = async () => {
      try {
        const profile = await api.getMe();
        setUser(profile);
        if (profile.flats && profile.flats.length > 0) {
          setSelectedFlatId(profile.flats[0].flat_id);
        }
        setActiveTab(determineDefaultTab(profile));
      } catch (e) {
        setUser(null);
      } finally {
        setLoading(false);
      }
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
    setActiveTab(determineDefaultTab(profile));
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    setSelectedFlatId('');
    setActiveTab('home');
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
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <main style={{ flex: 1, paddingBottom: '2rem' }}>
        {!user ? (
          <LoginPage
            lang={currentLang}
            onLoginSuccess={handleLoginSuccess}
          />
        ) : activeTab === 'amenities' ? (
          <AmenityBookingPage
            user={user}
            selectedFlatId={selectedFlatId}
            lang={currentLang}
          />
        ) : activeTab === 'guard' ? (
          <GuardGateTerminal
            user={user}
            lang={currentLang}
          />
        ) : activeTab === 'committee' ? (
          <CommitteeDashboard
            user={user}
            lang={currentLang}
          />
        ) : activeTab === 'complaints' ? (
          <ResidentComplaints
            user={user}
            selectedFlatId={selectedFlatId}
            lang={currentLang}
          />
        ) : activeTab === 'accounts' ? (
          <AccountsWorkspace
            user={user}
            lang={currentLang}
          />
        ) : activeTab === 'helpdesk' ? (
          <HelpDeskQueue
            user={user}
            lang={currentLang}
          />
        ) : (
          <ResidentHomePage
            user={user}
            selectedFlatId={selectedFlatId}
            lang={currentLang}
            onNavigateTab={setActiveTab}
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
        Township One • Client: Company A, Pune • 2,400 flats / 28 towers / 180 staff / 4 gates
      </footer>
    </div>
  );
}
