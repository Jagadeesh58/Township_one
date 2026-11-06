# Core Screen Map & Navigation Hierarchy

Township One organizes reviewer-facing and resident journeys into an uncluttered, role-aware hierarchy.

## 1. Resident Experience (Mobile-First PWA)

1. **Sign In & Flat Context (`/login`)**
   - Phone number input, OTP challenge entry.
   - Linked flat selection (for multi-unit residents) and active membership context (Owner / Tenant / Family).

2. **Resident Home (`/`)**
   - High-contrast immediate summary card:
     - Outstanding Dues & Due Date / Overdue indicator.
     - Open Complaints count & latest status badge.
     - Today's Expected Visitors.
     - Important Community Notices carousel.
   - Quick Action Bar (2-tap shortcuts):
     - [Pay Dues] -> opens Payment Checkout.
     - [Raise Complaint] -> opens Complaint Form.
     - [Visitor Approval] -> opens Today's Visitors.
     - [Book Amenity] -> opens Amenities calendar.

3. **Maintenance Bills & Payment Center (`/billing`)**
   - Current billing statement breakdown:
     - Area (sq ft) × Rate (₹6.50/sq ft).
     - Breakdown: Principal, Late Fee / Interest (illustrative bye-law formula).
     - Previous payments and current outstanding balance.
   - Simulated Payment Modal:
     - Outcome selector for demo: SUCCESS, PENDING, FAILED, EXPIRED.
     - Payment receipt generation and download.
   - Per-Flat Ledger Tab:
     - Running chronological statement of debits, credits, and balance.

4. **Complaints Hub (`/complaints`)**
   - Resident's active and resolved tickets.
   - Detail view with status timeline, assigned team, SLA timer, and resolution rating.
   - New complaint flow with AI category & urgency classification.

## 2. Staff & Committee Portals

5. **Help Desk Workspace (`/helpdesk`)**
   - Triage queue, AI suggestion with 1-tap human override, emergency escalation.

6. **Accounts Reconciliation Queue (`/accounts`)**
   - Bank CSV import, auto-match explanation, held rows review.

7. **Guard Tablet Entry (`/gate`)**
   - High-contrast night-readable tablet UI, visitor photo capture, offline queue.

8. **Committee Executive Dashboard (`/committee`)**
   - Collections KPI, dues ageing breakdown, complaint resolution metrics, monthly PDF report.
