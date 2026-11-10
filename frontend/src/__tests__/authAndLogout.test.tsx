/** @vitest-environment jsdom */
import React from 'react';
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LoginPage } from '../pages/LoginPage';
import { Navbar } from '../components/Navbar';
import { ResidentHomePage } from '../pages/ResidentHomePage';
import { api, UserProfile } from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual('../api/client');
  return {
    ...actual,
    api: {
      loginWithPassword: vi.fn(),
      requestOtp: vi.fn(),
      verifyOtp: vi.fn(),
      getMe: vi.fn(),
      logout: vi.fn(),
      getBillingSummary: vi.fn().mockResolvedValue({
        flat_id: 'flat-1',
        flat_number: 'T07-1203',
        area_sqft: '1150',
        current_due: '0.00',
        total_outstanding_due: '0.00',
        overdue_days: 0,
        estimated_late_fee: '0.00',
        late_fee_notice: '',
        recent_ledger: [],
      }),
      listVisitors: vi.fn().mockResolvedValue([]),
      listVisitorEntries: vi.fn().mockResolvedValue([]),
      listNotices: vi.fn().mockResolvedValue([]),
      listActiveNotices: vi.fn().mockResolvedValue([]),
    },
  };
});

const mockUser: UserProfile = {
  id: 'u-1',
  phone: '9876543210',
  name: 'Neeraj Kulkarni',
  email: 'neeraj@township.local',
  roles: [{ role_code: 'RESIDENT', scope_type: 'TOWNSHIP' }],
  flats: [
    {
      flat_id: 'flat-1',
      flat_number: 'T07-1203',
      floor_number: 12,
      area_sqft: '1150',
      member_type: 'OWNER',
      can_pay_bills: true,
      can_approve_visitors: true,
      can_raise_complaints: true,
    },
  ],
};

describe('LoginPage and Authentication Modes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all three login modes: 1-Click Demo, Password, and Mobile OTP', () => {
    const handleLoginSuccess = vi.fn();
    render(<LoginPage lang="en" onLoginSuccess={handleLoginSuccess} />);

    expect(screen.getByText(/Quick Demo Roles/i)).toBeInTheDocument();
    expect(screen.getByText(/Password Login/i)).toBeInTheDocument();
    expect(screen.getByText(/Mobile OTP/i)).toBeInTheDocument();
    expect(screen.getByText(/Neeraj Kulkarni/i)).toBeInTheDocument();
    expect(screen.getByText(/Swati Joshi/i)).toBeInTheDocument();
  });

  it('executes 1-click login for Resident Owner preset', async () => {
    const handleLoginSuccess = vi.fn();
    (api.loginWithPassword as any).mockResolvedValueOnce({ user: mockUser });

    render(<LoginPage lang="en" onLoginSuccess={handleLoginSuccess} />);

    const ownerCard = screen.getByText(/Neeraj Kulkarni/i).closest('button');
    expect(ownerCard).toBeInTheDocument();
    fireEvent.click(ownerCard!);

    await waitFor(() => {
      expect(api.loginWithPassword).toHaveBeenCalledWith('9876543210', '123456');
      expect(handleLoginSuccess).toHaveBeenCalledWith(mockUser);
    });
  });

  it('allows switching to Password Login mode and autofilling demo credentials', async () => {
    const handleLoginSuccess = vi.fn();
    (api.loginWithPassword as any).mockResolvedValueOnce({ user: mockUser });

    render(<LoginPage lang="en" onLoginSuccess={handleLoginSuccess} />);

    // Switch to Password tab
    const passwordTab = screen.getByText(/Password Login/i);
    fireEvent.click(passwordTab);

    // Check autofill button and inputs
    const autofillBtn = screen.getByText(/Fill Demo Password/i);
    fireEvent.click(autofillBtn);

    const submitBtn = screen.getByText(/Sign In with Password/i);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.loginWithPassword).toHaveBeenCalledWith('9876543210', '123456');
      expect(handleLoginSuccess).toHaveBeenCalledWith(mockUser);
    });
  });

  it('allows switching to Mobile OTP mode and displays clear 123456 code highlight', async () => {
    const handleLoginSuccess = vi.fn();
    (api.requestOtp as any).mockResolvedValueOnce({
      message: 'OTP sent',
      phone: '9876543210',
      demo_hint: 'Demo OTP is 123456',
    });
    (api.verifyOtp as any).mockResolvedValueOnce({ user: mockUser });

    render(<LoginPage lang="en" onLoginSuccess={handleLoginSuccess} />);

    // Switch to OTP tab
    const otpTab = screen.getByText(/Mobile OTP/i);
    fireEvent.click(otpTab);

    expect(screen.getByText(/Demo Mode: No SMS needed/i)).toBeInTheDocument();

    // Click Send OTP
    const sendOtpBtn = screen.getByText(/Send OTP/i);
    fireEvent.click(sendOtpBtn);

    await waitFor(() => {
      expect(api.requestOtp).toHaveBeenCalledWith('9876543210');
      expect(screen.getByText(/DEMO OTP CODE:/i)).toBeInTheDocument();
      expect(screen.getAllByText('123456').length).toBeGreaterThanOrEqual(1);
    });

    // Auto-fill OTP
    const autofillOtpBtn = screen.getByText(/One-Click Fill/i);
    fireEvent.click(autofillOtpBtn);

    // Verify OTP
    const verifyBtn = screen.getByText(/Verify & Continue/i);
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(api.verifyOtp).toHaveBeenCalledWith('9876543210', '123456');
      expect(handleLoginSuccess).toHaveBeenCalledWith(mockUser);
    });
  });
});

describe('Logout Availability Across Views', () => {
  it('renders a prominent Sign Out button and user badge in Navbar', () => {
    const handleLogout = vi.fn();
    render(
      <Navbar
        user={mockUser}
        currentLang="en"
        onLanguageChange={vi.fn()}
        onLogout={handleLogout}
        selectedFlatId="flat-1"
      />
    );

    const logoutBtn = screen.getByTestId('navbar-logout-btn');
    expect(logoutBtn).toBeInTheDocument();
    expect(logoutBtn).toHaveTextContent(/Sign Out/i);
    expect(screen.getByText(/Neeraj/i)).toBeInTheDocument();

    fireEvent.click(logoutBtn);
    expect(handleLogout).toHaveBeenCalledTimes(1);
  });

  it('renders a prominent Sign Out button on the Resident Home banner', async () => {
    const handleLogout = vi.fn();
    render(
      <ResidentHomePage
        user={mockUser}
        selectedFlatId="flat-1"
        lang="en"
        onLogout={handleLogout}
      />
    );

    const residentLogoutBtn = await screen.findByTestId('resident-logout-btn');
    expect(residentLogoutBtn).toBeInTheDocument();
    expect(residentLogoutBtn).toHaveTextContent(/Sign Out/i);

    fireEvent.click(residentLogoutBtn);
    expect(handleLogout).toHaveBeenCalledTimes(1);
  });
});
