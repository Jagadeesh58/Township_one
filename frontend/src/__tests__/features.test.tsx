import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AccountsWorkspace } from '../pages/AccountsWorkspace';
import { HelpDeskQueue } from '../pages/HelpDeskQueue';
import { ResidentComplaints } from '../pages/ResidentComplaints';
import { NotificationBell } from '../components/NotificationBell';
import { api, UserProfile } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    getBankAccounts: vi.fn(),
    previewBankStatement: vi.fn(),
    commitBankStatement: vi.fn(),
    getBankReviewQueue: vi.fn(),
    submitBankReviewAction: vi.fn(),
    getBankImportHistory: vi.fn(),
    getActiveSafetyEvents: vi.fn(),
    getHelpdeskQueue: vi.fn(),
    getComplaintDetail: vi.fn(),
    getDuplicateCandidates: vi.fn(),
    correctComplaintClassification: vi.fn(),
    transitionComplaintStatus: vi.fn(),
    linkDuplicateComplaint: vi.fn(),
    acknowledgeSafetyEvent: vi.fn(),
    getMyComplaints: vi.fn(),
    raiseComplaint: vi.fn(),
    rateComplaint: vi.fn(),
    reopenComplaint: vi.fn(),
    getSignedPhotoUrl: vi.fn(),
    getNotifications: vi.fn(),
    getUnreadNotificationCount: vi.fn(),
    markNotificationsRead: vi.fn(),
    markAllNotificationsRead: vi.fn(),
  },
}));

const mockUser: UserProfile = {
  id: 'usr-123',
  phone: '9876543200',
  name: 'Anita Deshmukh',
  roles: [
    { role_code: 'ACCOUNTS', scope_type: 'TOWNSHIP' },
    { role_code: 'HELPDESK', scope_type: 'TOWNSHIP' },
  ],
  flats: [
    {
      flat_id: 'flat-1',
      flat_number: 'T07-1203',
      floor_number: 12,
      area_sqft: '1150.00',
      member_type: 'OWNER',
      can_pay_bills: true,
      can_approve_visitors: true,
      can_raise_complaints: true,
    },
  ],
};

describe('AccountsWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getBankAccounts as any).mockResolvedValue([
      { id: 'acc-1', account_no: '98765432100012', bank_name: 'HDFC Township Maintenance', ifsc_code: 'HDFC0001234', is_active: true },
    ]);
    (api.getBankReviewQueue as any).mockResolvedValue({
      items: [
        {
          id: 'row-1',
          import_file_id: 'file-1',
          original_row_number: 1,
          txn_date: '2026-11-04T10:00:00Z',
          narration: 'UPI/PARTIAL/T05-0101',
          direction: 'CREDIT',
          amount: '4000.00',
          utr: 'UTRCONCURR001',
          payer_upi: 'resident.t05.0101@okhdfcbank',
          parse_status: 'ACCEPTED',
          decision: 'REVIEW',
          decision_reason: 'Partial payment requires accounts approval',
          review_status: 'PENDING',
        },
      ],
      total: 1,
      page: 1,
      pages: 1,
    });
    (api.getBankImportHistory as any).mockResolvedValue([]);
  });

  it('renders accounts workspace with accounts list and review queue', async () => {
    render(<AccountsWorkspace user={mockUser} lang="en" />);

    expect(screen.getByText('Accounts Workspace')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Review Queue/)).toBeInTheDocument();
      expect(screen.getByText('UTRCONCURR001')).toBeInTheDocument();
      expect(screen.getByText('Partial payment requires accounts approval')).toBeInTheDocument();
    });
  });

  it('handles statement preview workflow', async () => {
    (api.previewBankStatement as any).mockResolvedValue({
      file_sha256: 'abc1234567890def',
      filename: 'demo.csv',
      total_rows: 1,
      accepted_rows: 1,
      invalid_rows: 0,
      total_credit: '7475.00',
      total_debit: '0.00',
      duplicate_file: false,
      rows: [
        {
          original_row_number: 1,
          txn_date: '2026-11-01T00:00:00Z',
          narration: 'UPI-NEERAJ-T07-1203',
          utr: 'UPI001',
          payer_upi: 'neeraj.t07.1203@okhdfcbank',
          amount: '7475.00',
          candidate_decision: 'AUTO_MATCH',
        },
      ],
    });

    render(<AccountsWorkspace user={mockUser} lang="en" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['dummy,content'], 'demo.csv', { type: 'text/csv' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const previewBtn = screen.getByText('Statement Preview');
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText('AUTO_MATCH')).toBeInTheDocument();
      expect(screen.getByText(/Commit & Post to Ledger/)).toBeInTheDocument();
    });
  });
});

describe('HelpDeskQueue Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getActiveSafetyEvents as any).mockResolvedValue([
      {
        id: 'safety-1',
        complaint_id: 'cmp-safety',
        event_type: 'GAS_LEAK',
        details: 'Strong LPG smell in kitchen',
        status: 'ACTIVE',
        ticket_number: 'CMP-2026-1025',
        flat_number: 'T12-0408',
        created_at: '2026-11-06T10:00:00Z',
      },
    ]);
    (api.getHelpdeskQueue as any).mockResolvedValue({
      items: [
        {
          id: 'cmp-1',
          ticket_number: 'CMP-2026-1001',
          flat_number: 'T12-0408',
          title: 'Kitchen pipe burst',
          description: 'Water spraying under the sink',
          category: 'PLUMBING',
          urgency: 'HIGH',
          status: 'ASSIGNED',
          version: 1,
          is_safety_escalation: false,
          created_at: '2026-11-06T10:00:00Z',
          sla_resolution_time_remaining_hours: 12,
        },
      ],
      total: 1,
      page: 1,
      pages: 1,
    });
  });

  it('renders safety escalation alert banner for active emergency events', async () => {
    render(<HelpDeskQueue user={mockUser} lang="en" />);

    await waitFor(() => {
      expect(screen.getByText(/Active Safety Escalation/)).toBeInTheDocument();
      expect(screen.getByText(/Strong LPG smell in kitchen/)).toBeInTheDocument();
      expect(screen.getByText('Acknowledge')).toBeInTheDocument();
    });
  });

  it('renders queue tickets with SLA indicators', async () => {
    render(<HelpDeskQueue user={mockUser} lang="en" />);

    await waitFor(() => {
      expect(screen.getByText('CMP-2026-1001')).toBeInTheDocument();
      expect(screen.getByText('Kitchen pipe burst')).toBeInTheDocument();
      expect(screen.getAllByText('PLUMBING').length).toBeGreaterThan(0);
      expect(screen.getAllByText('HIGH').length).toBeGreaterThan(0);
      expect(screen.getByText(/12h left/)).toBeInTheDocument();
    });
  });
});

describe('ResidentComplaints Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getMyComplaints as any).mockResolvedValue([
      {
        id: 'comp-1',
        ticket_number: 'CMP-2026-1001',
        title: 'Geyser not heating',
        description: 'Water heater in master bath is cold',
        category: 'ELECTRICAL',
        urgency: 'MEDIUM',
        status: 'RESOLVED',
        version: 2,
        created_at: '2026-11-05T12:00:00Z',
        assigned_team: 'Electrical Team',
      },
    ]);
  });

  it('renders my complaints list and raise complaint form', async () => {
    render(<ResidentComplaints user={mockUser} selectedFlatId="flat-1" lang="en" />);

    expect(screen.getByText(/Raise Complaint/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/CMP-2026-1001/)).toBeInTheDocument();
      expect(screen.getByText('Geyser not heating')).toBeInTheDocument();
      expect(screen.getByText(/Rate Resolution/)).toBeInTheDocument();
      expect(screen.getByText(/Request Reopen/)).toBeInTheDocument();
    });
  });

  it('submits a new complaint successfully', async () => {
    (api.raiseComplaint as any).mockResolvedValue({
      id: 'comp-new',
      ticket_number: 'CMP-2026-1030',
      title: 'Water tap leaking',
      assigned_team: 'Plumbing Team',
    });

    render(<ResidentComplaints user={mockUser} selectedFlatId="flat-1" lang="en" />);

    const titleInput = screen.getByPlaceholderText(/Kitchen tap leaking/);
    const descInput = screen.getByPlaceholderText(/Describe the issue in detail/);

    fireEvent.change(titleInput, { target: { value: 'Water tap leaking' } });
    fireEvent.change(descInput, { target: { value: 'Bathroom sink tap continues dripping' } });

    const submitBtn = screen.getByText('Submit Ticket');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.raiseComplaint).toHaveBeenCalled();
      expect(screen.getByText(/Ticket #CMP-2026-1030 created successfully/)).toBeInTheDocument();
    });
  });
});

describe('NotificationBell Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getUnreadNotificationCount as any).mockResolvedValue({ unread_count: 2 });
    (api.getNotifications as any).mockResolvedValue([
      {
        id: 'notif-1',
        notification_type: 'SAFETY_ESCALATION',
        title: 'URGENT: Safety Escalation',
        message: 'Gas leak detected in Flat T12-0408',
        is_read: false,
        created_at: '2026-11-06T10:00:00Z',
      },
      {
        id: 'notif-2',
        notification_type: 'PAYMENT_RECEIVED',
        title: 'Payment Successful',
        message: 'Your payment of ₹7,475 has been settled.',
        is_read: true,
        created_at: '2026-11-06T09:00:00Z',
      },
    ]);
  });

  it('displays unread count badge and opens notifications popover', async () => {
    render(<NotificationBell lang="en" />);

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    const bellBtn = screen.getByLabelText('Notifications');
    fireEvent.click(bellBtn);

    await waitFor(() => {
      expect(screen.getByText('Notifications')).toBeInTheDocument();
      expect(screen.getByText('URGENT: Safety Escalation')).toBeInTheDocument();
      expect(screen.getByText('Gas leak detected in Flat T12-0408')).toBeInTheDocument();
    });
  });
});
