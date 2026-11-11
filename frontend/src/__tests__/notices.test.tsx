import React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { api, ManagedNoticeItem, NoticeRevisionItem, UserProfile } from '../api/client';
import { ResidentNoticesPage } from '../pages/ResidentNoticesPage';
import { CommitteeNoticeEditor } from '../pages/CommitteeNoticeEditor';
import { Navbar } from '../components/Navbar';

vi.mock('../components/NotificationBell', () => ({ NotificationBell: () => null }));

vi.mock('../api/client', () => ({
  api: {
    listActiveNotices: vi.fn(),
    markNoticeRead: vi.fn(),
    listManagedNotices: vi.fn(),
    getNoticeRevisions: vi.fn(),
    createNotice: vi.fn(),
    updateNotice: vi.fn(),
    publishNotice: vi.fn(),
    withdrawNotice: vi.fn(),
    logout: vi.fn(),
  },
}));

const resident: UserProfile = {
  id: 'resident-1',
  phone: '9876543211',
  name: 'Swati Joshi',
  roles: [{ role_code: 'RESIDENT', scope_type: 'FLAT', scope_id: 'flat-1' }],
  flats: [{
    flat_id: 'flat-1', flat_number: 'T12-0408', floor_number: 4,
    area_sqft: '980.00', member_type: 'TENANT', can_pay_bills: true,
    can_approve_visitors: true, can_raise_complaints: true,
  }],
};

const committee: UserProfile = {
  id: 'committee-1',
  phone: '9876543299',
  name: 'Committee Member',
  roles: [{ role_code: 'COMMITTEE', scope_type: 'TOWNSHIP' }],
  flats: [],
};

const notice: NoticeRevisionItem = {
  id: 'revision-7', notice_id: 'notice-1', revision_number: 2,
  title: 'Water supply maintenance', body: 'Water service will pause at 10:00.',
  body_en: 'Water service will pause at 10:00.', body_hi: undefined, body_mr: undefined,
  is_fallback_language: true, fallback_language_label: 'Shown in English',
  publish_at: '2026-11-09T08:00:00Z', audience: 'TOWER', tower_id: 'tower-12',
  tower_number: 'T12', severity: 'CRITICAL', created_at: '2026-11-09T07:00:00Z', is_read: false,
};

const managedNotice: ManagedNoticeItem = {
  id: 'notice-1', status: 'DRAFT', revision_count: 1,
  current_revision: { ...notice, is_fallback_language: false, fallback_language_label: undefined, is_read: false },
};

beforeEach(() => {
  vi.clearAllMocks();
  (api.listActiveNotices as ReturnType<typeof vi.fn>).mockResolvedValue([notice]);
  (api.markNoticeRead as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true });
  (api.listManagedNotices as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  (api.getNoticeRevisions as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  (api.createNotice as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'notice-new' });
});

describe('resident notices', () => {
  it('shows tower audience, critical severity and explicit English fallback', async () => {
    render(<ResidentNoticesPage user={resident} lang="mr" />);

    expect(await screen.findByText('Water supply maintenance')).toBeInTheDocument();
    expect(screen.getByText('Shown in English')).toBeInTheDocument();
    expect(screen.getByText('Tower T12')).toBeInTheDocument();
    expect(screen.getByText(/(CRITICAL|अत्यावश्यक)/i)).toBeInTheDocument();
  });

  it('marks the exact revision as read', async () => {
    render(<ResidentNoticesPage user={resident} lang="en" />);
    fireEvent.click(await screen.findByRole('button', { name: /mark as read/i }));

    await waitFor(() => expect(api.markNoticeRead).toHaveBeenCalledWith('revision-7'));
    expect(await screen.findByText(/Read/i)).toBeInTheDocument();
  });
});

describe('committee notice editor', () => {
  it('creates a multilingual tower-scoped draft with a publish window', async () => {
    render(<CommitteeNoticeEditor user={committee} lang="en" />);
    await screen.findByText('Notices');

    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Tower 12 water work' } });
    fireEvent.change(screen.getByLabelText(/English text/i), { target: { value: 'Water supply will pause for maintenance.' } });
    fireEvent.change(screen.getByLabelText(/Hindi text/i), { target: { value: 'जल आपूर्ति रखरखाव के लिए रुकेगी।' } });
    fireEvent.change(screen.getByLabelText(/Marathi text/i), { target: { value: 'देखभालीसाठी पाणीपुरवठा थांबेल.' } });
    fireEvent.change(screen.getByLabelText('Audience'), { target: { value: 'TOWER' } });
    fireEvent.change(screen.getByLabelText('Tower ID'), { target: { value: 'tower-12' } });

    const saveDraftButtons = screen.getAllByRole('button', { name: /save draft/i });
    fireEvent.click(saveDraftButtons[saveDraftButtons.length - 1]);

    await waitFor(() => expect(api.createNotice).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Tower 12 water work',
      body_en: 'Water supply will pause for maintenance.',
      body_hi: 'जल आपूर्ति रखरखाव के लिए रुकेगी।',
      body_mr: 'देखभालीसाठी पाणीपुरवठा थांबेल.',
      audience: 'TOWER',
      tower_id: 'tower-12',
      status: 'DRAFT',
      publish_at: expect.any(String),
    })));
  });
});

describe('notice navigation permissions', () => {
  it('does not show the notice editor tab to residents', () => {
    render(<Navbar user={resident} currentLang="en" onLanguageChange={vi.fn()} onLogout={vi.fn()} onTabChange={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /notice editor/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /notices/i })).toBeInTheDocument();
  });

  it('shows notice management to committee users', () => {
    render(<Navbar user={committee} currentLang="en" onLanguageChange={vi.fn()} onLogout={vi.fn()} onTabChange={vi.fn()} />);
    expect(screen.getByRole('button', { name: /notice editor/i })).toBeInTheDocument();
  });
});
