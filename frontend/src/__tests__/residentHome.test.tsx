import React from 'react';
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ResidentHomePage } from '../pages/ResidentHomePage';
import { api, UserProfile, BillingSummary } from '../api/client';

describe('ResidentHomePage UI Integration & State Transitions', () => {
  const mockUser: UserProfile = {
    id: 'user-swati-uuid',
    phone: '9876543211',
    name: 'Swati Joshi',
    roles: [{ role_code: 'RESIDENT', scope_type: 'FLAT', scope_id: 'flat-swati-uuid' }],
    flats: [
      {
        flat_id: 'flat-swati-uuid',
        flat_number: 'T12-0408',
        floor_number: 4,
        area_sqft: '980.00',
        member_type: 'TENANT',
        can_pay_bills: true,
        can_approve_visitors: true,
        can_raise_complaints: true,
      },
    ],
  };

  const mockSummary: BillingSummary = {
    flat_id: 'flat-swati-uuid',
    flat_number: 'T12-0408',
    area_sqft: '980.00',
    current_due: '6370.00',
    current_due_inr: '6370.00',
    total_outstanding_due: '6370.00',
    total_outstanding_due_inr: '6370.00',
    overdue_days: 47,
    interest_eligible_days: 42,
    estimated_late_fee: '131.94',
    estimated_late_fee_inr: '131.94',
    late_fee_notice: 'Illustrative demo rule (18% p.a. simple interest per Model Bye-Law No. 67)',
    unpaid_bills: [
      {
        id: 'bill-sep-2026',
        period_month: 9,
        period_year: 2026,
        principal_amount: '6370.00',
        late_fee_amount: '0.00',
        total_amount: '6370.00',
        paid_amount: '0.00',
        balance_amount: '6370.00',
        status: 'OVERDUE',
        due_date: '2026-09-20T00:00:00Z',
        lines: [
          {
            id: 'line-1',
            line_type: 'PRINCIPAL',
            description: 'Monthly Maintenance (980.00 sq ft @ ₹6.50/sq ft)',
            amount: '6370.00',
          },
        ],
      },
    ],
    latest_bill: {
      id: 'bill-sep-2026',
      period_month: 9,
      period_year: 2026,
      principal_amount: '6370.00',
      late_fee_amount: '0.00',
      total_amount: '6370.00',
      paid_amount: '0.00',
      balance_amount: '6370.00',
      status: 'OVERDUE',
      due_date: '2026-09-20T00:00:00Z',
      lines: [],
    },
    recent_ledger: [],
  };

  const mockClearedSummary: BillingSummary = {
    ...mockSummary,
    current_due: '0.00',
    current_due_inr: '0.00',
    total_outstanding_due: '0.00',
    total_outstanding_due_inr: '0.00',
    overdue_days: 0,
    interest_eligible_days: 0,
    estimated_late_fee: '0.00',
    unpaid_bills: [],
    latest_bill: {
      id: 'bill-sep-2026',
      period_month: 9,
      period_year: 2026,
      principal_amount: '6370.00',
      late_fee_amount: '0.00',
      total_amount: '6370.00',
      paid_amount: '6370.00',
      balance_amount: '0.00',
      status: 'PAID',
      due_date: '2026-09-20T00:00:00Z',
      lines: [],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dues, open complaints, today visitors, and broadcast notice', async () => {
    vi.spyOn(api, 'getBillingSummary').mockResolvedValue(mockSummary);

    render(<ResidentHomePage user={mockUser} selectedFlatId="flat-swati-uuid" lang="en" />);

    // Initial loading indicator
    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    // After API resolves
    await waitFor(() => {
      expect(screen.getByText('Swati Joshi')).toBeInTheDocument();
    });

    // 1. Dues shown
    const dueElements = screen.getAllByText(/₹6,370\.00/);
    expect(dueElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Maintenance Dues/i)).toBeInTheDocument();

    // 2. Open complaints shown
    expect(screen.getByText(/CMP-2026-1001/i)).toBeInTheDocument();
    expect(screen.getByText(/Severe bathroom ceiling water seepage/i)).toBeInTheDocument();

    // 3. Today's visitors shown
    expect(screen.getByText(/Today's Visitors/i)).toBeInTheDocument();
    expect(screen.getByText(/No expected visitors at the gate right now/i)).toBeInTheDocument();

    // 4. Broadcast notice shown
    expect(screen.getByText(/Mandatory Water Tank Cleaning/i)).toBeInTheDocument();
  });

  it('opens simulated payment modal in <= 2 clicks from home (1 tap on Pay Now)', async () => {
    vi.spyOn(api, 'getBillingSummary').mockResolvedValue(mockSummary);

    render(<ResidentHomePage user={mockUser} selectedFlatId="flat-swati-uuid" lang="en" />);

    await waitFor(() => {
      expect(screen.getAllByText(/₹6,370\.00/).length).toBeGreaterThanOrEqual(1);
    });

    // Tap 1: Click "Pay Now" on DuesCard
    const payNowBtn = screen.getByRole('button', { name: /Pay Now/i });
    fireEvent.click(payNowBtn);

    // Assert PaymentModal is rendered and open
    await waitFor(() => {
      expect(screen.getByText(/Simulated Payment Gateway/i)).toBeInTheDocument();
      expect(screen.getByText('TEST MODE — No Real Money Charged')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Complete Test Payment/i })).toBeInTheDocument();
    });
  });

  it('renders clean empty state when all dues are fully cleared', async () => {
    vi.spyOn(api, 'getBillingSummary').mockResolvedValue(mockClearedSummary);

    render(<ResidentHomePage user={mockUser} selectedFlatId="flat-swati-uuid" lang="en" />);

    await waitFor(() => {
      const clearedElements = screen.getAllByText(/All dues cleared/i);
      expect(clearedElements.length).toBeGreaterThanOrEqual(1);
    });

    expect(screen.getByText('₹0.00')).toBeInTheDocument();
  });

  it('handles API loading and failure states gracefully', async () => {
    vi.spyOn(api, 'getBillingSummary').mockRejectedValue(new Error('Network error'));

    render(<ResidentHomePage user={mockUser} selectedFlatId="flat-swati-uuid" lang="en" />);

    await waitFor(() => {
      expect(screen.getByText('Swati Joshi')).toBeInTheDocument();
    });
  });
});
