// Township One - Resident API client
// API client for resident authentication, billing summaries with multi-bill support,
// payment checkout with idempotency and simulated outcome dispatch.
// Enforces HttpOnly session cookie authentication with credentials: 'include'
// and double-submit CSRF protection on mutating requests.

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
  amount: string | number;
  amount_inr?: string;
}

export interface BillItem {
  id: string;
  period_month: number;
  period_year: number;
  principal_amount: string | number;
  principal_amount_inr?: string;
  late_fee_amount: string | number;
  total_amount: string | number;
  total_amount_inr?: string;
  paid_amount: string | number;
  paid_amount_inr?: string;
  balance_amount: string | number;
  balance_amount_inr?: string;
  status: string;
  due_date: string;
  lines: BillLine[];
}

export interface BillingSummary {
  flat_id: string;
  flat_number: string;
  area_sqft: string | number;
  current_due: string | number;
  current_due_inr?: string;
  total_outstanding_due: string | number;
  total_outstanding_due_inr?: string;
  overdue_days: number;
  interest_eligible_days?: number;
  estimated_late_fee: string | number;
  estimated_late_fee_inr?: string;
  late_fee_notice: string;
  unpaid_bills?: BillItem[];
  latest_bill?: BillItem;
  recent_ledger: Array<{
    id: string;
    entry_type: string;
    amount: string | number;
    amount_inr?: string;
    balance_after: string | number;
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
  amount: string | number;
  payment_mode: string;
  transaction_reference: string;
  issued_at: string;
}

/**
 * Reads double-submit CSRF token from document cookie.
 */
function getCsrfToken(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/(?:^|;\s*)township_csrf=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Shared fetch helper ensuring credentials: 'include' and automatic
 * X-CSRF-Token header attachment on mutating requests.
 */
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers || {});

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers.set('X-CSRF-Token', csrfToken);
    }
  }

  return fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });
}

export const api = {
  async requestOtp(phone: string) {
    const res = await fetchWithAuth(`${API_BASE}/auth/otp/request`, {
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
    const res = await fetchWithAuth(`${API_BASE}/auth/otp/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, otp }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error?.message || 'Invalid OTP');
    }
    const data = await res.json();
    return data;
  },

  async getMe(): Promise<UserProfile> {
    const res = await fetchWithAuth(`${API_BASE}/auth/me`);
    if (!res.ok) throw new Error('Unauthorized');
    return res.json();
  },

  async logout() {
    try {
      await fetchWithAuth(`${API_BASE}/auth/logout`, {
        method: 'POST',
      });
    } catch (e) {
      console.error(e);
    }
  },

  async getBillingSummary(flatId: string): Promise<BillingSummary> {
    const res = await fetchWithAuth(`${API_BASE}/billing/flats/${flatId}/summary`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error?.message || 'Failed to fetch billing');
    }
    return res.json();
  },

  async checkout(payload: {
    flat_id: string;
    bill_id: string;
    amount: string | number;
    payment_method?: string;
    test_outcome?: string;
    idempotency_key?: string;
  }) {
    const res = await fetchWithAuth(`${API_BASE}/payments/checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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
