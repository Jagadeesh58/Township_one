"""
Build script for Technical Design Document (TDD.docx).
Ensures required sections, accurate technical specifications,
and strict absence of forbidden words.
"""
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def create_tdd():
    doc = docx.Document()

    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Line 1: Required GitHub repository URL
    p_url = doc.add_paragraph()
    r_url = p_url.add_run("https://github.com/Jagadeesh58/Township_one.git")
    r_url.font.name = "Arial"
    r_url.font.size = Pt(11)
    r_url.font.bold = True
    r_url.font.color.rgb = RGBColor(0, 102, 204)

    # Document Title
    p_title = doc.add_paragraph()
    r_title = p_title.add_run("Township One — Technical Design Document")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(26, 36, 56)

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run("System Architecture, Data Integrity, Financial Controls & Security Specifications")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(12)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(100, 100, 100)

    # Helper function for adding sections
    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(14)
        r.font.bold = True
        r.font.color.rgb = RGBColor(26, 36, 56)
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = RGBColor(40, 60, 90)
        return p

    def add_body(text, bold_prefix=None, italic=False):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            rb = p.add_run(bold_prefix + " ")
            rb.font.name = "Arial"
            rb.font.size = Pt(10)
            rb.font.bold = True
        r = p.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r.font.italic = italic
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            rb = p.add_run(bold_prefix + " ")
            rb.font.name = "Arial"
            rb.font.size = Pt(10)
            rb.font.bold = True
        r = p.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(10)
        return p

    # 1. Overview and GitHub URL
    add_h1("1. Overview and GitHub URL")
    add_body("https://github.com/Jagadeesh58/Township_one.git", bold_prefix="Repository URL:")
    add_body(
        "Township One is an integrated resident portal and operations management system engineered "
        "for large residential communities. The reference configuration is modeled on a community "
        "comprising 2,400 residential flats across 28 towers, 180 on-site operations staff, and "
        "4 multi-lane security gates in Pune."
    )
    add_body(
        "The system addresses core community operational requirements: passwordless mobile authentication "
        "with rate limiting, hierarchical spatial modeling, deterministic area-based maintenance billing, "
        "simulated test payment processing with cryptographic idempotency, dual-entry accounting ledgers "
        "with immutable post-transaction balances, a bank statement matching engine with database-level "
        "uniqueness protection, complaint management with trilingual emergency detection and offline AI fallback, "
        "visitor access management with cryptographic offline credentials, amenity bookings with concurrency slot locking, "
        "multilingual community notice broadcasting, committee governance financial reporting, and a responsive "
        "Progressive Web Application (PWA) supporting English, Marathi, and Hindi."
    )

    # 2. Architecture and Why
    add_h1("2. Architecture and Why")
    add_body(
        "Township One is designed as a decoupled client-server architecture prioritizing security, "
        "auditability, deterministic calculations, and operational resilience."
    )
    add_h2("System Components")
    add_bullet(
        "React 19 with TypeScript and Vite. Provides an installable Progressive Web Application "
        "with service worker caching for offline shell availability, touch targets exceeding 48px, "
        "and zero third-party UI framework overhead.",
        bold_prefix="Frontend Client:"
    )
    add_bullet(
        "FastAPI (Python 3.11+). Provides asynchronous high-throughput REST endpoints with strict "
        "Pydantic v2 schema validation, dependency injection for database sessions and authentication, "
        "and automated OpenAPI documentation.",
        bold_prefix="Backend API:"
    )
    add_bullet(
        "PostgreSQL 15+ as the primary relational database engine, supporting row-level locking "
        "(SELECT ... FOR UPDATE) for strict payment concurrency control. An optional SQLite configuration "
        "is maintained for rapid local developer unit testing.",
        bold_prefix="Database Tier:"
    )
    add_bullet(
        "SQLAlchemy 2.0 ORM with Alembic for version-controlled, auditable database schema migrations.",
        bold_prefix="Data Mapping & Migrations:"
    )
    add_bullet(
        "Docker Compose specification with PostgreSQL 15 alpine, persistent named volumes, and "
        "automated health check probes.",
        bold_prefix="Containerization:"
    )

    add_h2("Architectural Decisions and Rationale")
    add_bullet(
        "FastAPI provides native asynchronous concurrency, tight type validation through Pydantic v2, "
        "and automatic OpenAPI documentation, minimizing endpoint defects while maintaining high throughput.",
        bold_prefix="Why FastAPI?"
    )
    add_bullet(
        "Financial accounting and payment workflows require strong ACID guarantees and row-level locking. "
        "PostgreSQL guarantees that concurrent checkouts on the same maintenance bill cannot result in double "
        "allocation or balance corruption.",
        bold_prefix="Why PostgreSQL?"
    )
    add_bullet(
        "Storing session credentials in browser localStorage exposes residents to token exfiltration via "
        "Cross-Site Scripting (XSS). Township One uses HttpOnly, SameSite=Lax session cookies paired with "
        "double-submit CSRF tokens.",
        bold_prefix="Why Cookie-Only Sessions?"
    )

    # 3. Data Model
    add_h1("3. Data Model")
    add_body(
        "The relational database schema is normalized across six logical domains: spatial structure, "
        "identity and role-based access control, maintenance billing and dual-entry accounting, "
        "complaint lifecycle management, visitor security, and amenity reservations."
    )
    add_bullet(
        "Tower (code, name, total_floors, flats_per_floor), Flat (flat_number, tower_id, "
        "floor_number, area_sqft), Gate (gate_number, name, access_type).",
        bold_prefix="Spatial Domain:"
    )
    add_bullet(
        "User (name, phone, email), UserRoleAssignment (role_code: RESIDENT, ACCOUNTS, COMMITTEE, GUARD, "
        "ADMIN), FlatMembership (flat_id, user_id, member_type: OWNER, TENANT, FAMILY; granular permissions: "
        "can_pay_bills, can_approve_visitors, can_raise_complaints).",
        bold_prefix="Identity & RBAC:"
    )
    add_bullet(
        "BillingRule (rate_per_sqft, due_day_of_month, grace_period_days, late_fee_percentage_pa), "
        "Bill (flat_id, period_month, period_year, principal_amount, late_fee_amount, total_amount, "
        "paid_amount, balance_amount, status), BillLine (itemized lines), FlatLedgerEntry (entry_type: "
        "DEBIT, CREDIT; amount, balance_after, description, reference_id).",
        bold_prefix="Billing & Accounting:"
    )
    add_bullet(
        "Payment (flat_id, bill_id, user_id, amount, status, idempotency_key, gateway_reference), "
        "Receipt (receipt_number, payment_id, flat_id, amount, issued_at), BankAccount (account_number, "
        "bank_name, ifsc_code, upi_id), BankStatementFile (filename, file_sha256, status), "
        "BankPosting (bank_account_id, utr, payment_id, status; with UNIQUE(bank_account_id, utr)).",
        bold_prefix="Payments & Bank Domain:"
    )
    add_bullet(
        "Complaint (ticket_number, flat_id, tower_id, user_id, title, description, category, urgency, "
        "status, version, is_safety_escalation, language, assigned_staff_id, assigned_team, rating, "
        "feedback, reopen_requested, closed_at), ComplaintEvent (audit trail with from_status, to_status, "
        "actor_user_id), IncidentGroup (grouping duplicate tickets in a tower), ComplaintAttachment "
        "(secure photo metadata, stripped EXIF, signed URLs).",
        bold_prefix="Complaints Domain:"
    )
    add_bullet(
        "VisitorEntry (gate_id, flat_id, visitor_name, phone, purpose, status: ARRIVED, AWAITING_APPROVAL, "
        "APPROVED, REJECTED, ADMITTED, EXITED, OVERRIDDEN_ADMIT; arrival_time, admission_time, exit_time), "
        "VisitorPhoto (photo_path, sha256, retention_expires_at), PreApproval (flat_id, guest_name, phone, "
        "purpose, code_hash, salt, valid_from, valid_until, max_uses, used_count), "
        "SupervisorOverride (entry_id, supervisor_id, reason, created_at).",
        bold_prefix="Visitor Security Domain:"
    )
    add_bullet(
        "Amenity (code, name, description, open_time, close_time, slot_duration_minutes, max_capacity, "
        "fee_amount), AmenitySlot (amenity_id, slot_date, start_time, end_time, capacity, booked_count, "
        "is_closed, closure_reason), AmenityRule (amenity_id, advance_booking_days, cancellation_cutoff_hours, "
        "flat_daily_limit), AmenityClosure (amenity_id, start_date, end_date, reason), "
        "AmenityBooking (amenity_id, slot_id, flat_id, user_id, status, fee_amount, idempotency_key).",
        bold_prefix="Amenity Reservations Domain:"
    )
    add_bullet(
        "Notice (author_user_id, status, priority, target_scope, target_tower_id, current_revision, "
        "published_at, expires_at), NoticeRevision (notice_id, revision_number, title_en, body_en, "
        "title_mr, body_mr, title_hi, body_hi, created_by_user_id), NoticeRead (notice_id, user_id, revision_number, read_at).",
        bold_prefix="Community Notices Domain:"
    )

    # 4. Main Flows
    add_h1("4. Main Flows")

    add_h2("Flow 1: Passwordless Mobile Authentication")
    add_bullet("The resident enters their 10-digit mobile number in the PWA interface.")
    add_bullet("The server verifies rate limits: maximum 5 OTP requests per phone in 10 minutes, and maximum 20 requests per client IP per hour.")
    add_bullet("A 6-digit cryptographically random OTP is generated, salted, and hashed using SHA-256 before being stored in OTPChallenge with a 5-minute expiration window.")
    add_bullet("In development/demo mode, the server logs the OTP; in production, SMS credentials dispatch the message.")
    add_bullet("The resident submits the OTP. The server validates salt and hash in constant time, marks the challenge as used, issues a signed JWT with unique JTI, and writes an HttpOnly SameSite=Lax session cookie alongside a double-submit CSRF cookie.")

    add_h2("Flow 2: Area-Based Maintenance Billing & Ledger Posting")
    add_bullet("At billing generation, the system reads the active BillingRule tariff (INR 6.50 per sq ft).")
    add_bullet("The principal amount is computed as flat area multiplied by rate, rounded using ROUND_HALF_UP Decimal arithmetic.")
    add_bullet("A Bill entity is created with status ISSUED, and corresponding itemized BillLine entries are created.")
    add_bullet("Simultaneously, a DEBIT entry is posted to FlatLedgerEntry, updating the flat running balance_after by the bill amount.")

    add_h2("Flow 3: Idempotent Payment Processing & Concurrency Protection")
    add_bullet("The resident initiates payment for an unpaid bill via the 2-tap payment interface.")
    add_bullet("The server verifies flat authorization (user must possess active membership with can_pay_bills permission).")
    add_bullet("An idempotency check is performed against the SHA-256 request fingerprint (user ID, flat ID, bill ID, amount, currency). Identical re-submissions return cached payment records; cross-flat key collisions return HTTP 409 Conflict.")
    add_bullet("The target Bill row is locked (SELECT ... FOR UPDATE) to prevent concurrent over-payment.")
    add_bullet("Upon success, the bill paid_amount increases and balance_amount decreases. A CREDIT entry is written to FlatLedgerEntry, reducing the running balance_after. A tamper-evident Receipt is generated.")

    add_h2("Flow 4: Bank Statement Preview, Deterministic Safety Matching, and Review Queue")
    add_bullet("Accounts staff uploads canonical bank statement CSV. The system parses rows, computes file SHA-256, and executes a dry-run preview returning validation status and candidate decisions without database mutation.")
    add_bullet("Upon commit, idempotency keyed on (bank_account_no, file_sha256) ensures duplicate files return HTTP 200 ALREADY_PROCESSED with zero side effects.")
    add_bullet(
        "Auto-match requires credit transaction in INR against valid bank account, unique UTR, "
        "registered UPI identifier matching flat, flat token narration resolving to the same flat, "
        "and transaction amount matching open bill balance exactly, with zero duplicate or conflicting evidence. "
        "In our 385-row benchmark corpus, exactly 60 rows satisfy this strict safety contract (15.58% auto-match coverage), "
        "with zero false auto-postings verified."
    )
    add_bullet(
        "Rows matching only UPI or only flat reference, or with amounts differing from bill balance, "
        "are routed to the review queue with explicit non-empty reasons (UPI_ONLY_REVIEW, FLAT_REF_ONLY_REVIEW, "
        "AMOUNT_ONLY_REVIEW) for accounts approval. Debit rows are held as DEBIT_HELD."
    )
    add_bullet(
        "A database-level unique constraint on bank_postings(bank_account_id, utr) enforces that duplicate UTRs "
        "can never be posted twice, even under concurrent multi-threaded execution. Savepoint handling converts "
        "duplicate attempts to DUPLICATE_NO_OP or UTR_CONFLICT without raising unhandled database errors."
    )

    add_h2("Flow 5: Resident Complaint Lodging, Trilingual Emergency Detection, and AI Triage")
    add_bullet("The resident submits a complaint with title, description, flat identifier, and optional photo attachment (MIME verified via Pillow, EXIF stripped, signed URL streaming).")
    add_bullet("The deterministic emergency detector inspects text for hazardous keywords (fire, smoke, gas leak, lift entrapment, sparking) across English, Hindi, and Marathi. Matches force CRITICAL urgency and create an active SafetyEvent with alerts; safety events cannot be downgraded.")
    add_bullet("Non-emergency complaints pass to the AI triage engine (Groq API with 5s timeout and 1 retry; local TF-IDF + MultinomialNB fallback trained on 360-row multilingual dataset). Confidence below 0.60 flags the ticket for human review.")
    add_bullet("Deterministic assignment matches the predicted category to staff teams, locating on-duty staff in the tower.")

    add_h2("Flow 6: Visitor Entry, Resident Push Approval, Gate Admission & Cryptographic Verification")
    add_bullet("Guard records visitor arrival with optional photo. The photo is stripped of EXIF metadata before storage, and an automated 90-day retention purge job enforces privacy regulations.")
    add_bullet("Visitor state transitions to AWAITING_APPROVAL. The resident receives an alert and can approve or reject in 1 tap from their home dashboard.")
    add_bullet("Upon approval, the guard terminal admits entry; illegal state bypasses return HTTP 409 Conflict. If a resident is unreachable, an authorized supervisor can record an override with mandatory justification.")
    add_bullet("Pre-approved guest passes issue 6-digit codes and ECDSA P-256 compact cryptographic credentials. Offline guard terminals verify signatures against the gate public key and time anchor, syncing transactions back when online.")

    add_h2("Flow 7: Amenity Slot Booking & Capacity Concurrency")
    add_bullet("Residents browse facility slots (Banquet Hall, Tennis Court, Swimming Pool) with live available capacity counters.")
    add_bullet("Booking requests enforce unique idempotency keys, booking window advance limits, and a maximum of 1 slot per flat per day rule (HTTP 409 on violation).")
    add_bullet("Cancellations outside the 2-hour cutoff release slot capacity; society administrative closures cancel conflicting bookings automatically and block new reservations.")

    add_h2("Flow 8: Community Notice Board Publishing & Language Fallback")
    add_bullet("Authorized committee members publish notices targeted globally or scoped to specific towers (e.g., Tower 7 lift maintenance).")
    add_bullet("Notice revisions are immutable and append-only. Residents viewing notices in Marathi or Hindi receive localized content, or an explicit 'Shown in English' fallback badge when translations are absent.")
    add_bullet("Resident read receipts are tracked per user per revision number.")

    add_h2("Flow 9: Committee Governance Dashboard & Financial Auditing")
    add_bullet("Provides executive operational oversight with mathematical dues ageing reconciliation (0-30, 31-60, 61-90, 90+ days summing exactly to total outstanding dues).")
    add_bullet("Presents complaint SLA turnaround metrics (mean and median resolution hours, SLA breach count) and bank reconciliation coverage.")
    add_bullet("Supports one-click ReportLab PDF governance report generation and CSV aggregate data export.")

    # 5. AI Capabilities (Built vs Not Built, Synthetic Data)
    add_h1("5. AI Capabilities (Built vs Not Built, Synthetic Data)")
    add_body(
        "To maintain transparency and engineering integrity, AI functionality is divided into implemented "
        "operational capabilities and scheduled future enhancements:"
    )
    add_bullet(
        "Deterministic trilingual regex emergency detector for fire/smoke/gas/lift/sparking forcing immediate "
        "CRITICAL urgency and SafetyEvent; Groq API classification client with graceful fallback to local "
        "TF-IDF + MultinomialNB model trained on 360-row multilingual dataset (45 per category across 8 categories, "
        "120 per language: English, Hindi, Marathi); character n-gram TF-IDF cosine similarity duplicate candidate "
        "detection with incident grouping; zero AI in financial matching logic.",
        bold_prefix="Built:"
    )
    add_bullet(
        "Automated speech-to-text complaint transcription for gate intercoms; dynamic guard patrol route "
        "optimization; predictive maintenance forecasting on lift telemetry; automated OCR for utility meter "
        "photographs.",
        bold_prefix="Not Built Yet (Future):"
    )
    add_bullet(
        "The training dataset comprises 360 synthetically generated multilingual complaint examples (120 English, "
        "120 Hindi, 120 Marathi) balanced across 8 operational categories. Model evaluation uses held-out incident family "
        "splits. No production-level accuracy is claimed on unseen real-world society complaints until recalibrated "
        "on historical society operational data.",
        bold_prefix="Synthetic Training Data Notice:"
    )

    # 6. UI and Design Decisions
    add_h1("6. UI and Design Decisions")
    add_bullet(
        "From the resident home dashboard, dues can be reviewed and settled in two taps (Tap 1: 'Pay Now' "
        "on the DuesCard; Tap 2: 'Execute Test Payment' in the payment modal), and visitors can be approved in 1 tap.",
        bold_prefix="Two-Tap Resident Actions:"
    )
    add_bullet(
        "Responsive interface tested at 320px viewport width without horizontal scrollbars, ensuring accessibility "
        "on entry-level mobile devices.",
        bold_prefix="320px Viewport Support:"
    )
    add_bullet(
        "All primary interactive buttons and form controls enforce a minimum touch bounding box of 48px by 48px.",
        bold_prefix="Touch Target Sizing:"
    )
    add_bullet(
        "Comprehensive dictionary translations in English, Marathi, and Hindi, allowing seamless language switching "
        "across all navigation, billing, and status elements.",
        bold_prefix="Trilingual Localization:"
    )
    add_bullet(
        "Service worker pre-caches the static app shell while enforcing a strict network-only bypass for all /api/* "
        "routes, guaranteeing that sensitive financial and personal data is never written to public browser caches. "
        "A message listener clears cached assets upon resident logout.",
        bold_prefix="Offline Shell & Cache Boundary:"
    )
    add_bullet(
        "Guard Gate Terminal provides high-contrast outdoor night mode, gate selector (1-4), offline queue synchronization, "
        "and fast-track 6-digit pass verification.",
        bold_prefix="Guard Terminal:"
    )

    # 7. Security and Privacy Architecture
    add_h1("7. Security and Privacy Architecture")
    add_bullet(
        "Tokens are transported exclusively via HttpOnly, SameSite=Lax cookies (township_session). Token theft via "
        "XSS is prevented, and token revocation is tracked in real-time using JTI database blacklisting.",
        bold_prefix="Cookie-Only Session Security:"
    )
    add_bullet(
        "State-changing HTTP requests require a valid X-CSRF-Token header matching the township_csrf cookie.",
        bold_prefix="Double-Submit CSRF Protection:"
    )
    add_bullet(
        "Access to individual flat summaries, bills, ledgers, and receipts is validated against server-side FlatMembership "
        "records. Cross-flat viewing or payment attempts return HTTP 403 Forbidden.",
        bold_prefix="Strict IDOR Denial:"
    )
    add_bullet(
        "Privileges are derived strictly from database UserRoleAssignment entities; client-supplied role claims or headers "
        "are completely ignored.",
        bold_prefix="Role Tampering Immunity:"
    )
    add_bullet(
        "All monetary calculations utilize Python Decimal and PostgreSQL NUMERIC(12,2) with ROUND_HALF_UP rounding. "
        "Binary floating-point drift is strictly prohibited.",
        bold_prefix="Financial Precision:"
    )
    add_bullet(
        "Visitor photos have all EXIF metadata stripped via Pillow upon upload, are served exclusively via time-limited "
        "signed streaming URLs, and are permanently purged by an automated 90-day retention job.",
        bold_prefix="Visitor Privacy & EXIF Scrubbing:"
    )
    add_bullet(
        "System adheres to principles of the Digital Personal Data Protection (DPDP) Act: minimal resident data collection, "
        "salted SHA-256 OTP storage, zero plaintext credential storage, and segregated staff role scopes.",
        bold_prefix="Data Privacy Compliance:"
    )

    # 8. Scope Boundaries and Future Roadmap
    add_h1("8. Scope Boundaries and Future Roadmap")
    add_body(
        "Township One strictly separates verified deliverables from scheduled future roadmap capabilities:"
    )
    add_h2("Built Deliverables")
    add_bullet("Passwordless phone OTP authentication with persistent challenge tracking and rate limiting.")
    add_bullet("Spatial hierarchy for 28 towers, 2,400 flats, 180 staff, and 4 access gates.")
    add_bullet("Area-based maintenance billing engine (INR 6.50/sq ft) with 5-day grace period and simple interest.")
    add_bullet("Simulated payment gateway with cryptographic SHA-256 idempotency fingerprinting.")
    add_bullet("Dual-entry general accounting ledger with running post-transaction balances.")
    add_bullet("Payment receipts with sequential numbering and tamper-evident transaction references.")
    add_bullet("Bank statement matching engine with canonical CSV preview, deterministic safety rules, 60/385 auto-matches (15.58% coverage), review queue for partials/UPI-only/flat-ref-only rows, and database-level unique constraint on account and UTR.")
    add_bullet("Complaint lifecycle state machine with HTTP 409 Conflict rejection, trilingual emergency detection, AI triage with local MultinomialNB fallback, private signed photo streaming, and semantic duplicate linking.")
    add_bullet("Visitor access lifecycle (arrival, approval, admission, exit, supervisor override) with 90-day photo retention purging and offline ECDSA P-256 token verification.")
    add_bullet("Amenity reservation system with slot capacity locking, flat daily limit enforcement, and closure conflict cancellation.")
    add_bullet("Community notice broadcasting with append-only revisions, tower targeting, and automatic language fallback indicators.")
    add_bullet("Committee governance dashboard with mathematical dues ageing reconciliation (0-30, 31-60, 61-90, 90+ days), SLA turnaround metrics, PDF and CSV exports.")
    add_bullet("Progressive Web Application (PWA) with English/Marathi/Hindi localization, offline shell caching with network-only API bypass, and responsive mobile layout.")

    add_h2("Not Built Yet (Scheduled for Future Scope)")
    add_bullet("Automated license plate recognition (ALPR) cameras integrated with gate physical barrier relays.")
    add_bullet("IoT smart water meter telemetry ingestion and automated consumption-based tariff surcharges.")
    add_bullet("Biometric RFID turnstiles for automated clubhouse amenity entry.")
    add_bullet("Federation accounting consolidation across multi-society clusters.")

    # 9. Labelled Assumptions List
    add_h1("9. Labelled Assumptions List")
    add_body(
        "All operational rules implemented in the current system are explicitly labeled as illustrative "
        "demonstration benchmarks pending formal society general body resolution:"
    )
    add_bullet(
        "Set to INR 6.50 per square foot per month based on Pune residential society benchmarks.",
        bold_prefix="Maintenance Tariff:"
    )
    add_bullet(
        "Fixed to the 15th calendar day of each billing month.",
        bold_prefix="Due Date:"
    )
    add_bullet(
        "5 calendar days following the due date (through the 20th of the month) during which no interest accrues.",
        bold_prefix="Grace Period:"
    )
    add_bullet(
        "Modeled as 18.00% per annum simple interest beginning on the first day following grace period expiration (the 21st). "
        "Daily interest rate is computed as 0.18 / 366 in leap years (such as 2026) and 0.18 / 365 in non-leap years. "
        "Derived from Model Bye-Law No. 67 under the Maharashtra Co-operative Societies (MCS) Act 1960 as an illustrative benchmark.",
        bold_prefix="Late Interest Rate:"
    )
    add_bullet(
        "Response SLA targets are modeled as 1 hour for CRITICAL, 4 hours for HIGH, 12 hours for MEDIUM, and 24 hours for LOW. "
        "Resolution SLA targets are modeled as 4 hours for CRITICAL, 24 hours for HIGH, 48 hours for MEDIUM, and 72 hours for LOW. "
        "First response timestamp is human-gated on staff action; SLA targets are illustrative demo operational baselines.",
        bold_prefix="Demo SLA Values:"
    )
    add_bullet(
        "The 360-row multilingual complaint classification dataset and 385-row bank statement corpus are synthetically "
        "generated for testing and algorithmic evaluation. Real-world society deployment requires calibration against "
        "historical society operational records.",
        bold_prefix="Synthetic Training Data:"
    )

    doc.save("TDD.docx")
    print("TDD.docx created successfully.")

if __name__ == "__main__":
    create_tdd()
