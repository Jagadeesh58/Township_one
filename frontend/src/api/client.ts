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

export type VisitorStatusType =
  | 'AWAITING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'ADMITTED'
  | 'EXITED'
  | 'EXPIRED'
  | 'OVERRIDDEN_ADMIT';

export interface VisitorEntryItem {
  id: string;
  gate_id: string;
  flat_id: string;
  flat_number?: string;
  tower_number?: string;
  visitor_name: string;
  phone?: string;
  purpose: string;
  status: VisitorStatusType;
  created_by_guard?: string;
  approval_decided_by?: string;
  approval_decided_at?: string;
  admitted_at?: string;
  exited_at?: string;
  photo_id?: string;
  photo_url?: string;
  pre_approval_id?: string;
  source: string;
  client_event_id?: string;
  version: number;
  created_at: string;
}

export interface PreApprovalItem {
  id: string;
  flat_id: string;
  guest_name: string;
  phone?: string;
  purpose: string;
  gate_id?: string;
  valid_from: string;
  valid_until: string;
  max_uses: number;
  used_count: number;
  code?: string;
  credential_jwt?: string;
  is_revoked: boolean;
  created_at: string;
}

export interface GuestCodeVerificationResult {
  valid: boolean;
  message: string;
  pre_approval_id?: string;
  flat_id?: string;
  guest_name?: string;
  remaining_uses?: number;
  conflict_flagged?: boolean;
}

export interface AmenityItem {
  id: string;
  name: string;
  description?: string;
  hourly_fee: string | number;
  capacity: number;
  rules?: string;
}

export interface AmenitySlotItem {
  id: string;
  amenity_id: string;
  slot_date: string;
  start_time: string;
  end_time: string;
  capacity: number;
  booked_count: number;
  available_spots: number;
  is_closed: boolean;
  closure_reason?: string;
}

export interface AmenityRuleItem {
  id: string;
  amenity_id: string;
  booking_window_days: number;
  max_daily_slots_per_flat: number;
  cancellation_cutoff_hours: number;
}

export interface AmenityBookingItem {
  id: string;
  flat_id: string;
  slot_id: string;
  user_id: string;
  amenity_name?: string;
  slot_date?: string;
  start_time?: string;
  end_time?: string;
  status: string;
  fee: string | number;
  fee_status: string;
  idempotency_key: string;
  version: number;
  created_at: string;
  cancelled_at?: string;
}

export interface AmenityClosureItem {
  id: string;
  amenity_id: string;
  start_date: string;
  end_date: string;
  reason: string;
  created_by_user_id: string;
  created_at: string;
}

export interface NoticeRevisionItem {
  id: string;
  notice_id: string;
  revision_number: number;
  title: string;
  body: string;
  body_en: string;
  body_hi?: string;
  body_mr?: string;
  is_fallback_language: boolean;
  fallback_language_label?: string;
  publish_at: string;
  expires_at?: string;
  audience: string;
  tower_id?: string;
  tower_number?: string;
  severity: string;
  created_at: string;
  is_read: boolean;
}

export interface DuesAgeingBandsData {
  band_0_30_days: string | number;
  band_31_60_days: string | number;
  band_61_90_days: string | number;
  band_90_plus_days: string | number;
  total_outstanding: string | number;
}

export interface FinancialMetricsData {
  total_billed: string | number;
  total_collected: string | number;
  total_outstanding: string | number;
  collection_rate_percent: string | number;
  ageing: DuesAgeingBandsData;
}

export interface ComplaintsMetricsData {
  total_complaints: number;
  open_unresolved_count: number;
  closed_resolved_count: number;
  overdue_count: number;
  reopened_count: number;
  reopened_rate_percent: string | number;
  mean_resolution_hours?: string | number;
  median_resolution_hours?: string | number;
  mean_first_response_hours?: string | number;
}

export interface PaymentMatchingMetricsData {
  total_rows_imported: number;
  auto_matched_count: number;
  review_queue_count: number;
  manually_approved_count: number;
  held_or_rejected_count: number;
  auto_match_coverage_percent: string | number;
}

export interface ClientTargetData {
  kpi_name: string;
  client_target_description: string;
  demo_sample_value: string;
  target_status_label: string;
}

export interface CommitteeReportData {
  reporting_period: string;
  data_cutoff_time: string;
  timezone: string;
  financials: FinancialMetricsData;
  complaints: ComplaintsMetricsData;
  payment_matching: PaymentMatchingMetricsData;
  client_targets: ClientTargetData[];
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

  const resolvedUrl = (typeof url === 'string' && url.startsWith('/') && (typeof window === 'undefined' || !window.location.origin || window.location.origin === 'null'))
    ? `http://localhost:8000${url}`
    : url;

  return fetch(resolvedUrl, {
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

  // Visitors & Gates
  async listVisitorEntries(gateId?: string, flatId?: string, statusFilter?: string): Promise<VisitorEntryItem[]> {
    const params = new URLSearchParams();
    if (gateId) params.append('gate_id', gateId);
    if (flatId) params.append('flat_id', flatId);
    if (statusFilter) params.append('status_filter', statusFilter);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetchWithAuth(`${API_BASE}/visitors/entries${qs}`);
    if (!res.ok) throw new Error('Failed to list visitor entries');
    return res.json();
  },

  async createVisitorEntry(payload: {
    gate_id: string;
    flat_id: string;
    visitor_name: string;
    phone?: string;
    purpose: string;
    photo_id?: string;
    client_event_id?: string;
  }): Promise<VisitorEntryItem> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/entries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to record visitor entry');
    }
    return res.json();
  },

  async decideVisitorApproval(entryId: string, decision: 'APPROVE' | 'REJECT'): Promise<VisitorEntryItem> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/${entryId}/approval`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to decide visitor approval');
    }
    return res.json();
  },

  async admitVisitor(entryId: string): Promise<VisitorEntryItem> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/${entryId}/admit`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to admit visitor');
    }
    return res.json();
  },

  async exitVisitor(entryId: string): Promise<VisitorEntryItem> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/${entryId}/exit`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to record visitor exit');
    }
    return res.json();
  },

  async overrideVisitor(entryId: string, reason: string): Promise<VisitorEntryItem> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/${entryId}/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to apply supervisor override');
    }
    return res.json();
  },

  async uploadVisitorPhoto(file: File): Promise<{ photo_id: string; sha256: string; retention_expires_at: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetchWithAuth(`${API_BASE}/visitors/photo/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to upload visitor photo');
    }
    return res.json();
  },

  async createPreApproval(payload: {
    flat_id: string;
    guest_name: string;
    phone?: string;
    purpose: string;
    gate_id?: string;
    valid_from: string;
    valid_until: string;
    max_uses?: number;
  }): Promise<PreApprovalItem> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/pre-approvals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to create guest pass');
    }
    return res.json();
  },

  async listPreApprovals(flatId?: string): Promise<PreApprovalItem[]> {
    const qs = flatId ? `?flat_id=${flatId}` : '';
    const res = await fetchWithAuth(`${API_BASE}/visitors/pre-approvals${qs}`);
    if (!res.ok) throw new Error('Failed to list guest passes');
    return res.json();
  },

  async verifyGuestCode(gateId: string, code?: string, credentialJwt?: string): Promise<GuestCodeVerificationResult> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/guest-code/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gate_id: gateId, code, credential_jwt: credentialJwt }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Guest code verification failed');
    }
    return res.json();
  },

  async getGatePublicKey(): Promise<{ algorithm: string; public_key_pem: string; offline_notice: string }> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/gate/public-key`);
    if (!res.ok) throw new Error('Failed to fetch gate public key');
    return res.json();
  },

  async getGateTimeAnchor(): Promise<{ server_time_utc: string; timestamp_unix: number; validity_window_seconds: number }> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/gate/time-anchor`);
    if (!res.ok) throw new Error('Failed to fetch gate time anchor');
    return res.json();
  },

  async syncOfflineGate(gateId: string, events: any[]): Promise<{ processed_count: number; acknowledged_ids: string[]; conflicts: any[] }> {
    const res = await fetchWithAuth(`${API_BASE}/visitors/gate/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gate_id: gateId, events }),
    });
    if (!res.ok) throw new Error('Failed to sync offline gate queue');
    return res.json();
  },

  // Amenities
  async listAmenities(): Promise<AmenityItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/amenities`);
    if (!res.ok) throw new Error('Failed to fetch amenities');
    return res.json();
  },

  async listAmenitySlots(amenityId: string, targetDate?: string): Promise<AmenitySlotItem[]> {
    const qs = targetDate ? `?target_date=${targetDate}` : '';
    const res = await fetchWithAuth(`${API_BASE}/amenities/${amenityId}/slots${qs}`);
    if (!res.ok) throw new Error('Failed to fetch amenity slots');
    return res.json();
  },

  async getAmenityRules(amenityId: string): Promise<AmenityRuleItem> {
    const res = await fetchWithAuth(`${API_BASE}/amenities/${amenityId}/rules`);
    if (!res.ok) throw new Error('Failed to fetch amenity rules');
    return res.json();
  },

  async listAmenityBookings(flatId?: string): Promise<AmenityBookingItem[]> {
    const qs = flatId ? `?flat_id=${flatId}` : '';
    const res = await fetchWithAuth(`${API_BASE}/amenities/bookings${qs}`);
    if (!res.ok) throw new Error('Failed to list amenity bookings');
    return res.json();
  },

  async bookAmenitySlot(flatId: string, slotId: string, idempotencyKey: string): Promise<AmenityBookingItem> {
    const res = await fetchWithAuth(`${API_BASE}/amenities/bookings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ flat_id: flatId, slot_id: slotId, idempotency_key: idempotencyKey }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to book amenity slot');
    }
    return res.json();
  },

  async cancelAmenityBooking(bookingId: string): Promise<AmenityBookingItem> {
    const res = await fetchWithAuth(`${API_BASE}/amenities/bookings/${bookingId}/cancel`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to cancel amenity booking');
    }
    return res.json();
  },

  async createAmenityClosure(payload: {
    amenity_id: string;
    start_date: string;
    end_date: string;
    reason: string;
  }): Promise<AmenityClosureItem> {
    const res = await fetchWithAuth(`${API_BASE}/amenities/closures`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to create amenity closure');
    }
    return res.json();
  },

  // Notices
  async listActiveNotices(lang: string = 'en', towerId?: string): Promise<NoticeRevisionItem[]> {
    const params = new URLSearchParams();
    if (lang) params.append('lang', lang);
    if (towerId) params.append('tower_id', towerId);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetchWithAuth(`${API_BASE}/notices${qs}`);
    if (!res.ok) throw new Error('Failed to fetch community notices');
    return res.json();
  },

  async getNoticeRevisions(noticeId: string, lang: string = 'en'): Promise<NoticeRevisionItem[]> {
    const res = await fetchWithAuth(`${API_BASE}/notices/${noticeId}/revisions?lang=${lang}`);
    if (!res.ok) throw new Error('Failed to fetch notice revisions');
    return res.json();
  },

  async createNotice(payload: {
    title: string;
    body_en: string;
    body_hi?: string;
    body_mr?: string;
    audience?: string;
    tower_id?: string;
    severity?: string;
    expires_at?: string;
  }) {
    const res = await fetchWithAuth(`${API_BASE}/notices`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to publish notice');
    }
    return res.json();
  },

  async updateNotice(noticeId: string, payload: {
    title: string;
    body_en: string;
    body_hi?: string;
    body_mr?: string;
    audience?: string;
    tower_id?: string;
    severity?: string;
    expires_at?: string;
  }) {
    const res = await fetchWithAuth(`${API_BASE}/notices/${noticeId}/revisions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error?.message || 'Failed to create notice revision');
    }
    return res.json();
  },

  async withdrawNotice(noticeId: string) {
    const res = await fetchWithAuth(`${API_BASE}/notices/${noticeId}/withdraw`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to withdraw notice');
    return res.json();
  },

  async markNoticeRead(revisionId: string) {
    const res = await fetchWithAuth(`${API_BASE}/notices/revisions/${revisionId}/read`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to mark notice read');
    return res.json();
  },

  // Committee Governance Reports
  async getCommitteeReport(period?: string): Promise<CommitteeReportData> {
    const qs = period ? `?period=${period}` : '';
    const res = await fetchWithAuth(`${API_BASE}/committee/report${qs}`);
    if (!res.ok) throw new Error('Failed to fetch committee report');
    return res.json();
  },

  async downloadCommitteeCsv(period?: string): Promise<string> {
    const qs = period ? `?period=${period}` : '';
    const res = await fetchWithAuth(`${API_BASE}/committee/report/csv${qs}`);
    if (!res.ok) throw new Error('Failed to download committee report CSV');
    return res.text();
  },

  async downloadCommitteePdf(period?: string): Promise<Blob> {
    const qs = period ? `?period=${period}` : '';
    const res = await fetchWithAuth(`${API_BASE}/committee/report/pdf${qs}`);
    if (!res.ok) throw new Error('Failed to download committee report PDF');
    return res.blob();
  },
};
