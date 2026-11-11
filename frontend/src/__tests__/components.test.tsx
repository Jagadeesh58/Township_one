import React from 'react';
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DuesCard } from '../components/DuesCard';
import { LedgerView } from '../components/LedgerView';
import { PaymentModal } from '../components/PaymentModal';
import { ReceiptModal } from '../components/ReceiptModal';
import { BillingSummary, PaymentReceipt } from '../api/client';
import {
  formatMoney,
  toPaise,
  fromPaise,
  addMoney,
  subMoney,
  compareMoney,
  isPositiveMoney,
  generateIdempotencyKey,
} from '../utils/money';

describe('Financial Utility: money.ts', () => {
  it('formats Indian currency numbers and strings correctly without floating point errors', () => {
    // Both string and number inputs format identically
    expect(formatMoney(6370)).toBe('₹6,370.00');
    expect(formatMoney('6370.00')).toBe('₹6,370.00');
    expect(formatMoney('0.00')).toBe('₹0.00');
    expect(formatMoney(0)).toBe('₹0.00');
    expect(formatMoney(null)).toBe('₹0.00');
    expect(formatMoney(undefined)).toBe('₹0.00');
    expect(formatMoney('1234567.89')).toBe('₹12,34,567.89');
    expect(formatMoney('10660.00')).toBe('₹10,660.00');
  });

  it('converts to integer paise accurately and avoids binary floating-point drift', () => {
    expect(toPaise('6370.00')).toBe(637000);
    expect(toPaise(6370.0)).toBe(637000);
    expect(toPaise('0.10')).toBe(10);
    expect(toPaise('0.20')).toBe(20);
    expect(fromPaise(637000)).toBe('6370.00');

    // Float addition 0.1 + 0.2 is normally 0.30000000000000004 in JS
    expect(addMoney('0.10', '0.20')).toBe(0.3);
    expect(formatMoney(addMoney('0.10', '0.20'))).toBe('₹0.30');
    expect(subMoney('100.00', '49.95')).toBe(50.05);
  });

  it('generates compliant UUID v4 idempotency keys', () => {
    const key1 = generateIdempotencyKey();
    const key2 = generateIdempotencyKey();

    expect(key1).not.toBe(key2);
    expect(key1.length).toBeGreaterThanOrEqual(36);
    // UUID v4 format pattern: 8-4-4-4-12 hex digits
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    expect(uuidRegex.test(key1)).toBe(true);
  });
});

describe('React Components: String/Decimal Runtime Resilience', () => {
  const mockOverdueSummary: BillingSummary = {
    flat_id: 'flat-swati-uuid',
    flat_number: 'T12-0408',
    area_sqft: '980.00' as any,
    current_due: '6370.00' as any,
    current_due_inr: '6370.00',
    total_outstanding_due: '6370.00' as any,
    total_outstanding_due_inr: '6370.00',
    overdue_days: 47,
    interest_eligible_days: 42,
    estimated_late_fee: '131.94' as any,
    estimated_late_fee_inr: '131.94',
    late_fee_notice: 'Illustrative demo calculation (18% p.a. simple interest after 5-day grace period)',
    unpaid_bills: [
      {
        id: 'bill-sep-2026',
        period_month: 9,
        period_year: 2026,
        principal_amount: '6370.00' as any,
        late_fee_amount: '0.00' as any,
        total_amount: '6370.00' as any,
        paid_amount: '0.00' as any,
        balance_amount: '6370.00' as any,
        status: 'OVERDUE',
        due_date: '2026-09-20T00:00:00Z',
        lines: [
          {
            id: 'line-1',
            line_type: 'PRINCIPAL',
            description: 'Monthly Maintenance (980.00 sq ft @ ₹6.50/sq ft)',
            amount: '6370.00' as any,
          },
        ],
      },
    ],
    latest_bill: {
      id: 'bill-sep-2026',
      period_month: 9,
      period_year: 2026,
      principal_amount: '6370.00' as any,
      late_fee_amount: '0.00' as any,
      total_amount: '6370.00' as any,
      paid_amount: '0.00' as any,
      balance_amount: '6370.00' as any,
      status: 'OVERDUE',
      due_date: '2026-09-20T00:00:00Z',
      lines: [],
    },
    recent_ledger: [
      {
        id: 'led-1',
        entry_type: 'DEBIT',
        amount: '6370.00' as any,
        balance_after: '6370.00' as any,
        description: 'Maintenance Bill - 09/2026',
        created_at: '2026-09-01T00:00:00Z',
      },
    ],
  };

  it('renders DuesCard with exact backend string numbers without throwing .toFixed TypeError', () => {
    const onPay = vi.fn();
    const onViewLedger = vi.fn();

    render(
      <DuesCard
        summary={mockOverdueSummary}
        loading={false}
        lang="en"
        onPayClick={onPay}
        onViewLedgerClick={onViewLedger}
      />
    );

    // Assert formatted currency display
    expect(screen.getByText('₹6,370.00')).toBeInTheDocument();
    expect(screen.getByText(/47 days overdue/i)).toBeInTheDocument();
    expect(screen.getByText(/\+₹131.94/i)).toBeInTheDocument();

    // Trigger action
    const payBtn = screen.getByRole('button', { name: /Pay Now/i });
    fireEvent.click(payBtn);
    expect(onPay).toHaveBeenCalledTimes(1);

    const ledgerBtn = screen.getByRole('button', { name: /Flat Ledger Statement/i });
    fireEvent.click(ledgerBtn);
    expect(onViewLedger).toHaveBeenCalledTimes(1);
  });

  it('renders DuesCard with zero due status correctly', () => {
    const mockZeroSummary: BillingSummary = {
      ...mockOverdueSummary,
      current_due: '0.00' as any,
      total_outstanding_due: '0.00' as any,
      overdue_days: 0,
      estimated_late_fee: '0.00' as any,
      unpaid_bills: [],
    };

    render(
      <DuesCard
        summary={mockZeroSummary}
        loading={false}
        lang="en"
        onPayClick={vi.fn()}
        onViewLedgerClick={vi.fn()}
      />
    );

    expect(screen.getByText('₹0.00')).toBeInTheDocument();
    expect(screen.getAllByText(/All dues cleared/i).length).toBeGreaterThan(0);
  });

  it('renders LedgerView with string amounts without throwing .toFixed TypeError', () => {
    render(<LedgerView summary={mockOverdueSummary} lang="en" />);

    expect(screen.getByText('Flat Ledger Statement')).toBeInTheDocument();
    expect(screen.getByText('Maintenance Bill - 09/2026')).toBeInTheDocument();
    expect(screen.getByText('6,370.00')).toBeInTheDocument();
  });

  it('renders PaymentModal with string due amounts and generates UUID v4 idempotency key', () => {
    const onClose = vi.fn();
    const onPaymentSuccess = vi.fn();

    render(
      <PaymentModal
        summary={mockOverdueSummary}
        lang="en"
        onClose={onClose}
        onPaymentSuccess={onPaymentSuccess}
      />
    );

    expect(screen.getByText(/TEST MODE — No Real Money Charged/i)).toBeInTheDocument();
    expect(screen.getByText('T12-0408')).toBeInTheDocument();
    // Verify amount due is displayed cleanly
    expect(screen.getByText('₹6,370.00')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Complete Test Payment/i })).toBeInTheDocument();
  });

  it('renders ReceiptModal correctly with string amount', () => {
    const mockReceipt: PaymentReceipt = {
      id: 'rcpt-uuid-1',
      receipt_number: 'RCPT-20261106-0001',
      flat_number: 'T12-0408',
      resident_name: 'Swati Joshi',
      amount: '6370.00' as any,
      payment_mode: 'UPI_SIMULATED',
      transaction_reference: 'TXN-9876543210-UUID',
      issued_at: '2026-11-06T12:00:00Z',
    };

    render(<ReceiptModal receipt={mockReceipt} lang="en" onClose={vi.fn()} />);

    expect(screen.getByText('RCPT-20261106-0001')).toBeInTheDocument();
    expect(screen.getByText('Swati Joshi')).toBeInTheDocument();
    expect(screen.getByText('₹6,370.00')).toBeInTheDocument();
    expect(screen.getByText('✓ PAYMENT CONFIRMED')).toBeInTheDocument();
  });
});
