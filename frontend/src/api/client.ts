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
  area_sqft: string | number;
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

export interface BankAccountItem {
  id: string;
  account_no: string;
  bank_name: string;
  ifsc_code: string;
  is_active: boolean;
}

export interface BankRowItem {
  id: string;
  import_file_id: string;
  original_row_number: number;
  txn_date?: string;
  value_date?: string;
  narration?: string;
  direction?: 'CREDIT' | 'DEBIT';
  amount?: string | number;
  currency?: string;
  utr?: string;
  payer_upi?: string;
  flat_ref?: string;
  parse_status: string;
  decision?: string;
  decision_reason?: string;
  review_status: string;
  matched_flat_id?: string;
  matched_flat_number?: string;
  matched_bill_id?: string;
  matched_payment_id?: string;
  is_valid?: boolean;
  candidate_decision?: string;
  candidate_action?: string;
  errors?: string[];
}

export interface BankImportPreview {
  file_sha256: string;
  filename: string;
  total_rows: number;
  accepted_rows: number;
  invalid_rows: number;
  total_credit: string | number;
  total_debit: string | number;
  duplicate_file: boolean;
  rows: BankRowItem[];
}

export interface BankImportCommit {
  status: string;
  import_file_id: string;
  account_no: string;
  total_rows: number;
  accepted_rows: number;
  invalid_rows: number;
  auto_matched_rows: number;
  held_for_review_rows: number;
  duplicate_rows: number;
  total_credit_settled: string | number;
}

export interface ComplaintAttachmentItem {
  id: string;
  file_name: string;
  content_type: string;
  file_size: number;
  file_sha256: string;
  signed_url?: string;
}

export interface ComplaintEventItem {
  id: string;
  actor_role?: string;
  event_type: string;
  from_status?: string;
  to_status?: string;
  notes?: string;
  created_at: string;
}

export interface ClassificationDecisionItem {
  id: string;
  actor_type: string;
  model_version?: string;
  predicted_category?: string;
  predicted_urgency?: string;
  confidence?: number;
  fallback_used: boolean;
  needs_human_review: boolean;
  created_at: string;
}

export interface ComplaintItem {
  id: string;
  ticket_number: string;
  flat_id: string;
  flat_number?: string;
  tower_id?: string;
  title: string;
  description: string;
  category: string;
  urgency: string;
  status: string;
  version: number;
  is_safety_escalation: boolean;
  language: string;
  assigned_team?: string;
  assigned_staff_id?: string;
  assigned_staff_name?: string;
  rating?: number;
  feedback?: string;
  reopen_requested?: boolean;
  reopen_reason?: string;
  created_at: string;
  closed_at?: string;
  first_response_at?: string;
  resolved_at?: string;
  sla_target_response_hours?: number;
  sla_target_resolution_hours?: number;
  sla_response_breached?: boolean;
  sla_resolution_breached?: boolean;
  sla_resolution_time_remaining_hours?: number;
  events?: ComplaintEventItem[];
  attachments?: ComplaintAttachmentItem[];
  decisions?: ClassificationDecisionItem[];
  incident_group_id?: string;
}

export interface SafetyEventItem {
  id: string;
  complaint_id: string;
  event_type: string;
  details?: string;
  status: string;
  created_at: string;
  ticket_number?: string;
  flat_number?: string;
}

export interface NotificationItem {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  payload?: any;
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
      if (typeof window !== 'undefined' && 'caches' in window) {
        const cacheKeys = await caches.keys();
        await Promise.all(cacheKeys.map(k => caches.delete(k)));
      }
      if (typeof navigator !== 'undefined' && navigator.serviceWorker && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_CACHES' });
      }
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

  // Bank Statement Matching
  async getBankAccounts(): Promise<BankAccountItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/bank/accounts`);
    if (!res.ok) throw new Error('Failed to fetch bank accounts');
    return res.json();
  },

  async previewBankStatement(file: File, accountNo?: string): Promise<BankImportPreview> {
    const formData = new FormData();
    formData.append('file', file);
    if (accountNo) formData.append('account_no', accountNo);

    const res = await fetchWithAuth(`${API_BASE}/bank/imports/preview`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to preview statement');
    }
    return res.json();
  },

  async commitBankStatement(bankAccountNo: string, importFileId: string): Promise<BankImportCommit> {
    const res = await fetchWithAuth(`${API_BASE}/bank/imports/commit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bank_account_no: bankAccountNo,
        import_file_id: importFileId,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to commit statement');
    }
    return res.json();
  },

  async getBankReviewQueue(params?: { bank_account_id?: string; review_status?: string; page?: number }): Promise<{
    items: BankRowItem[];
    total: number;
    page: number;
    pages: number;
  }> {
    const searchParams = new URLSearchParams();
    if (params?.bank_account_id) searchParams.set('bank_account_id', params.bank_account_id);
    if (params?.review_status) searchParams.set('review_status', params.review_status);
    if (params?.page) searchParams.set('page', String(params.page));

    const res = await fetchWithAuth(`${API_BASE}/bank/review-queue?${searchParams.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch review queue');
    return res.json();
  },

  async submitBankReviewAction(bankRowId: string, actionPayload: {
    action: string;
    target_flat_id?: string;
    target_bill_id?: string;
    reason?: string;
  }) {
    const res = await fetchWithAuth(`${API_BASE}/bank/rows/${bankRowId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(actionPayload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to submit review action');
    }
    return res.json();
  },

  async getBankImportHistory() {
    const res = await fetchWithAuth(`${API_BASE}/bank/imports`);
    if (!res.ok) throw new Error('Failed to fetch import history');
    return res.json();
  },

  // Complaints & Help Desk
  async raiseComplaint(formData: FormData): Promise<ComplaintItem> {
    const res = await fetchWithAuth(`${API_BASE}/complaints`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to submit complaint');
    }
    return res.json();
  },

  async getMyComplaints(): Promise<ComplaintItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/complaints/my`);
    if (!res.ok) throw new Error('Failed to fetch my complaints');
    return res.json();
  },

  async getHelpdeskQueue(params?: {
    status?: string;
    category?: string;
    urgency?: string;
    tower_id?: string;
    overdue_only?: boolean;
    page?: number;
  }): Promise<{ items: ComplaintItem[]; total: number; page: number; pages: number }> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.category) searchParams.set('category', params.category);
    if (params?.urgency) searchParams.set('urgency', params.urgency);
    if (params?.tower_id) searchParams.set('tower_id', params.tower_id);
    if (params?.overdue_only) searchParams.set('overdue_only', 'true');
    if (params?.page) searchParams.set('page', String(params.page));

    const res = await fetchWithAuth(`${API_BASE}/complaints/helpdesk/queue?${searchParams.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch help desk queue');
    return res.json();
  },

  async getComplaintDetail(complaintId: string): Promise<ComplaintItem> {
    const res = await fetchWithAuth(`${API_BASE}/complaints/${complaintId}`);
    if (!res.ok) throw new Error('Failed to fetch complaint detail');
    return res.json();
  },

  async transitionComplaintStatus(complaintId: string, payload: {
    status: string;
    notes?: string;
    expected_version?: number;
  }): Promise<ComplaintItem> {
    const res = await fetchWithAuth(`${API_BASE}/complaints/${complaintId}/transition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to transition status');
    }
    return res.json();
  },

  async correctComplaintClassification(complaintId: string, payload: {
    expected_version: number;
    category: string;
    urgency: string;
    reason: string;
  }): Promise<ComplaintItem> {
    const res = await fetchWithAuth(`${API_BASE}/complaints/${complaintId}/correct-classification`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to correct classification');
    }
    return res.json();
  },

  async rateComplaint(complaintId: string, payload: { rating: number; feedback?: string }): Promise<ComplaintItem> {
    const res = await fetchWithAuth(`${API_BASE}/complaints/${complaintId}/rating`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to submit rating');
    }
    return res.json();
  },

  async reopenComplaint(complaintId: string, payload: { reopen_reason: string }): Promise<ComplaintItem> {
    const res = await fetchWithAuth(`${API_BASE}/complaints/${complaintId}/reopen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to request reopen');
    }
    return res.json();
  },

  async getDuplicateCandidates(complaintId: string): Promise<{ candidates: any[] }> {
    const res = await fetchWithAuth(`${API_BASE}/complaints/${complaintId}/duplicate-candidates`);
    if (!res.ok) throw new Error('Failed to fetch duplicate candidates');
    return res.json();
  },

  async linkDuplicateComplaint(complaintId: string, targetComplaintId: string) {
    const res = await fetchWithAuth(`${API_BASE}/complaints/${complaintId}/link-duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_complaint_id: targetComplaintId }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to link duplicate');
    }
    return res.json();
  },

  async getActiveSafetyEvents(): Promise<SafetyEventItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/complaints/safety-events/active`);
    if (!res.ok) throw new Error('Failed to fetch safety events');
    return res.json();
  },

  async acknowledgeSafetyEvent(eventId: string, action: 'ACKNOWLEDGE' | 'DISMISS', notes?: string) {
    const res = await fetchWithAuth(`${API_BASE}/complaints/safety-events/${eventId}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, notes: notes || 'Acknowledged by operator' }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to update safety event');
    }
    return res.json();
  },

  async getSignedPhotoUrl(complaintId: string, attachmentId: string): Promise<{ signed_url: string }> {
    const res = await fetchWithAuth(`${API_BASE}/complaints/${complaintId}/photos/${attachmentId}/signed-url`);
    if (!res.ok) throw new Error('Failed to get signed photo URL');
    return res.json();
  },

  // Notifications
  async getNotifications(limit: number = 20): Promise<NotificationItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/notifications?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch notifications');
    return res.json();
  },

  async getUnreadNotificationCount(): Promise<{ unread_count: number }> {
    const res = await fetchWithAuth(`${API_BASE}/notifications/unread-count`);
    if (!res.ok) throw new Error('Failed to fetch unread count');
    return res.json();
  },

  async markNotificationsRead(notificationIds: string[]) {
    const res = await fetchWithAuth(`${API_BASE}/notifications/read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notification_ids: notificationIds }),
    });
    if (!res.ok) throw new Error('Failed to mark notifications read');
    return res.json();
  },

  async markAllNotificationsRead() {
    const res = await fetchWithAuth(`${API_BASE}/notifications/read-all`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to mark all notifications read');
    return res.json();
  },
};
