// Day 1 · D1-S6 — Resident interface and PWA
// API client for resident authentication, billing summaries with multi-bill support,
// payment checkout with idempotency and simulated outcome dispatch.

const API_BASE = '/api/v1';

export interface UserRole {
  role_code: string;
  scope_type: string;
  scope_id?: string;
}

export interface UserFlat {
  flat_id: string;
  flat_number: string;
  floor_number: number;
  area_sqft: number;
  member_type: string;
  can_pay_bills: boolean;
  can_approve_visitors: boolean;
  can_raise_complaints: boolean;
}

export interface UserProfile {
  id: string;
  phone: string;
  name: string;
  email?: string;
  roles: UserRole[];
  flats: UserFlat[];
}

export interface BillLine {
  id: string;
  line_type: string;
  description: string;
  amount: number;
  amount_inr?: string;
}

export interface BillItem {
  id: string;
  period_month: number;
  period_year: number;
  principal_amount: number;
  principal_amount_inr?: string;
  late_fee_amount: number;
  total_amount: number;
  total_amount_inr?: string;
  paid_amount: number;
  paid_amount_inr?: string;
  balance_amount: number;
  balance_amount_inr?: string;
  status: string;
  due_date: string;
  lines: BillLine[];
}

export interface BillingSummary {
  flat_id: string;
  flat_number: string;
  area_sqft: number;
  current_due: number;
  current_due_inr?: string;
  total_outstanding_due: number;
  total_outstanding_due_inr?: string;
  overdue_days: number;
  estimated_late_fee: number;
  estimated_late_fee_inr?: string;
  late_fee_notice: string;
  unpaid_bills?: BillItem[];
  latest_bill?: BillItem;
  recent_ledger: Array<{
    id: string;
    entry_type: string;
    amount: number;
    amount_inr?: string;
    balance_after: number;
    balance_after_inr?: string;
    description: string;
    reference_id?: string;
    created_at: string;
  }>;
}

export interface PaymentReceipt {
  id: string;
  receipt_number: string;
  flat_number: string;
  resident_name: string;
  amount: number;
  payment_mode: string;
  transaction_reference: string;
  issued_at: string;
}

export const api = {
  getAuthToken: () => localStorage.getItem('township_token'),
  setAuthToken: (t: string) => localStorage.setItem('township_token', t),
  clearAuthToken: () => localStorage.removeItem('township_token'),

  async requestOtp(phone: string) {
    const res = await fetch(`${API_BASE}/auth/otp/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error?.message || 'Failed to request OTP');
    }
    return res.json();
  },

  async verifyOtp(phone: string, otp: string) {
    const res = await fetch(`${API_BASE}/auth/otp/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, otp }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error?.message || 'Invalid OTP');
    }
    const data = await res.json();
    api.setAuthToken(data.access_token);
    return data;
  },

  async getMe(): Promise<UserProfile> {
    const token = api.getAuthToken();
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Unauthorized');
    return res.json();
  },

  async logout() {
    const token = api.getAuthToken();
    if (token) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch (e) {
        console.error(e);
      }
    }
    api.clearAuthToken();
  },

  async getBillingSummary(flatId: string): Promise<BillingSummary> {
    const token = api.getAuthToken();
    const res = await fetch(`${API_BASE}/billing/flats/${flatId}/summary`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error?.message || 'Failed to fetch billing');
    }
    return res.json();
  },

  async checkout(payload: {
    flat_id: string;
    bill_id: string;
    amount: number;
    payment_method?: string;
    test_outcome?: string;
    idempotency_key?: string;
  }) {
    const token = api.getAuthToken();
    const res = await fetch(`${API_BASE}/payments/checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        ...payload,
        payment_method: payload.payment_method || 'UPI_SIMULATED',
        test_outcome: payload.test_outcome || 'SUCCESS',
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error?.message || 'Payment failed');
    }
    return res.json();
  },
};
