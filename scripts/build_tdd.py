"""Generate the Technical Design Document from the current project facts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/Jagadeesh58/Township_one"
SUMMARY_PATH = ROOT / "docs" / "reports" / "summary.json"
OUTPUT_PATH = ROOT / "TDD.docx"
NAVY = "1E3557"
BLUE = "315B82"
PALE_BLUE = "EAF1F7"
LIGHT_GREY = "F2F4F7"
DARK_GREY = "505A66"


def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_text(cell, text: str, *, bold: bool = False, color: str = "263445", size: int = 9) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(2)
    run = paragraph.add_run(str(text))
    run.bold = bold
    run.font.name = "Aptos"
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = True
    for index, label in enumerate(headers):
        set_cell_text(table.rows[0].cells[index], label, bold=True, color="FFFFFF", size=9)
        shade_cell(table.rows[0].cells[index], NAVY)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        row_properties = table.rows[-1]._tr.get_or_add_trPr()
        row_properties.append(OxmlElement("w:cantSplit"))
        for index, value in enumerate(values):
            set_cell_text(cells[index], value, size=8)
            if row_index % 2 == 1:
                shade_cell(cells[index], LIGHT_GREY)
    if widths:
        for row in table.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_body(doc: Document, text: str, *, bold_prefix: str | None = None) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(5)
    paragraph.paragraph_format.line_spacing = 1.12
    if bold_prefix:
        lead = paragraph.add_run(f"{bold_prefix} ")
        lead.bold = True
        lead.font.color.rgb = RGBColor.from_string(NAVY)
    run = paragraph.add_run(text)
    run.font.name = "Aptos"
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGBColor.from_string("263445")


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.left_indent = Inches(0.23)
        paragraph.paragraph_format.first_line_indent = Inches(-0.12)
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.line_spacing = 1.05
        run = paragraph.add_run(item)
        run.font.name = "Aptos"
        run.font.size = Pt(9.2)


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.space_before = Pt(11 if level == 1 else 7)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    run.font.name = "Aptos Display"
    run.font.bold = True
    run.font.color.rgb = RGBColor.from_string(NAVY if level == 1 else BLUE)
    run.font.size = Pt(14 if level == 1 else 11)


def load_summary() -> dict:
    if not SUMMARY_PATH.exists():
        return {"overall_status": "NOT RUN", "gates": {}}
    try:
        return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"overall_status": "UNAVAILABLE", "gates": {}}


def extract_test_line(gate: dict) -> str:
    output = gate.get("stdout", "")
    match = re.search(r"\d+ passed[^\n]*", output)
    return match.group(0) if match else gate.get("status", "Not recorded")


def build_document() -> None:
    summary = load_summary()
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.72)
    section.right_margin = Inches(0.72)

    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9.5)
    styles["Normal"].font.color.rgb = RGBColor.from_string("263445")
    styles["Normal"].paragraph_format.space_after = Pt(4)
    for name in ("Heading 1", "Heading 2"):
        styles[name].font.name = "Aptos Display"
        styles[name].font.bold = True
        styles[name].font.color.rgb = RGBColor.from_string(NAVY)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header.add_run("TOWNSHIP ONE  |  TECHNICAL DESIGN")
    header_run.font.name = "Aptos"
    header_run.font.size = Pt(8)
    header_run.font.color.rgb = RGBColor.from_string(DARK_GREY)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer.add_run("Company A — Brief 2  |  Page ")
    footer_run.font.name = "Aptos"
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor.from_string(DARK_GREY)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)

    top = doc.add_paragraph()
    top.paragraph_format.space_after = Pt(12)
    url_run = top.add_run(REPOSITORY_URL)
    url_run.bold = True
    url_run.font.size = Pt(10)
    url_run.font.color.rgb = RGBColor.from_string(BLUE)

    title = doc.add_paragraph()
    title.paragraph_format.space_after = Pt(2)
    title_run = title.add_run("Township One")
    title_run.font.name = "Aptos Display"
    title_run.font.size = Pt(25)
    title_run.bold = True
    title_run.font.color.rgb = RGBColor.from_string(NAVY)

    subtitle = doc.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(12)
    subtitle_run = subtitle.add_run("Technical Design Document | Gated Township Resident Application")
    subtitle_run.font.size = Pt(11)
    subtitle_run.font.color.rgb = RGBColor.from_string(DARK_GREY)
    deployment_note = doc.add_paragraph()
    deployment_note.paragraph_format.space_after = Pt(10)
    note_run = deployment_note.add_run("Live app URL: not deployed yet. The free-tier deployment is documented in deployment.md; owner-managed provider accounts and secrets are still required.")
    note_run.font.name = "Aptos"
    note_run.font.size = Pt(8.5)
    note_run.font.italic = True
    note_run.font.color.rgb = RGBColor.from_string(DARK_GREY)

    add_table(
        doc,
        ["Project context", "Reference configuration"],
        [["Client brief", "Company A, Pune — Brief 2"], ["Community", "2,400 apartments across 28 towers"],
         ["Operations", "180 on-site staff and four gates"], ["Financial reference", "₹22–26 crore annual maintenance budget in the supplied brief"],
         ["Document basis", "Repository implementation and the supplied assignment brief"]],
        [1.6, 5.5],
    )

    add_heading(doc, "1. Problem and scope")
    add_body(
        doc,
        "Township One brings resident maintenance tasks, complaints, visitor approvals and amenity bookings into one mobile-first application. Staff workflows support bank statement reconciliation, complaint triage and gate operations. The committee view reports collections, outstanding dues and complaint timing. The product is a demonstration implementation using synthetic data and simulated external transactions."
    )
    add_body(
        doc,
        "The mandatory Core Build centres on resident login, maintenance bills with test payment, bank CSV matching, complaints with assignment/status and the committee view. The additional Brief 2 functions are resident notices, gate visitor management and amenity booking. General accounting remains with Tally; CCTV, boom barriers and marketplace functionality are outside scope."
    )

    add_heading(doc, "2. Architecture and technology choices")
    add_table(
        doc,
        ["Layer", "Technology", "Reason"],
        [
            ["Resident/staff UI", "React 19, TypeScript, Vite, PWA", "Mobile-first resident journeys and role-specific staff screens."],
            ["API", "FastAPI and Pydantic", "Typed request validation, dependency-based authorization and OpenAPI."],
            ["Persistence", "SQLAlchemy 2.0 and Alembic", "Explicit data relationships and versioned schema changes."],
            ["Shared database", "PostgreSQL", "Transactions, uniqueness and row locking for concurrent finance/booking workflows."],
            ["Local tests", "SQLite plus pytest", "Fast portable tests; PostgreSQL-specific guarantees still require PostgreSQL execution."],
            ["AI", "Local TF-IDF / MultinomialNB; optional Groq adapter", "Works without a paid API key; provider failures fall back to local classification or human review. Money decisions remain deterministic."],
            ["Photo storage", "Private local adapter or Cloudinary authenticated assets", "Hosted photos use authenticated delivery and are read through short-lived signed download URLs behind application routes."],
        ],
        [1.2, 2.0, 4.0],
    )

    add_body(
        doc,
        "Hosted reviewer profile: one Render Free Docker service serves the compiled React app and FastAPI from the same origin; Neon Free provides PostgreSQL; Cloudinary Free stores authenticated photo assets; and a scheduled GitHub Actions workflow calls a token-protected retention endpoint. The app uses a local complaint classifier by default, so no paid AI API is required. Provider quotas, sleep/cold-start behaviour and account limits make this a challenge/demo deployment profile, not a production availability guarantee."
    )

    add_heading(doc, "3. Data model")
    add_bullets(doc, [
        "Identity and access: User, OTPChallenge, RevokedToken, UserRoleAssignment, FlatMembership, Tower, Flat and Gate.",
        "Staff operations: StaffMember, StaffTeam, staff skills/shifts and gate-scoped GateDevice enrollment.",
        "Maintenance finance: BillingRule, Bill, BillLine, Payment, PaymentIntent/idempotency records, PaymentAllocation, Receipt and FlatLedgerEntry.",
        "Bank reconciliation: BankAccount, registered UPI mappings, BankImportFile/BankRow and bank posting/review records.",
        "Complaints: Complaint, ComplaintEvent, assignment/SLA records, ClassificationDecision, SafetyEvent, attachments and incident grouping.",
        "Visitors: VisitorEntry, VisitorPhoto, VisitorEvent, PreApproval, gate device identity/generation/sequence and audit events.",
        "Community: Amenity, AmenityRule, AmenitySlot, AmenityBooking, Notice, NoticeRevision and revision-specific NoticeRead records.",
    ])

    add_heading(doc, "4. Core workflows")
    add_heading(doc, "4.1 Resident identity and maintenance", 2)
    add_body(
        doc,
        "Residents authenticate through an OTP challenge and are authorized against active server-side flat membership. The resident home prioritizes dues, active complaints and today's visitors. Maintenance principal uses the approved area snapshot multiplied by the configured rate; the supplied sample rate is ₹6.50 per square foot per month. Issued bills retain their calculation inputs so later configuration changes do not rewrite prior bills."
    )
    add_body(
        doc,
        "The payment interface runs in test mode. Only a validated successful test result creates a posted payment allocation and receipt. Pending, failed or expired states do not reduce the outstanding balance. Monetary calculations use Decimal values and database numeric columns. Posted ledger events are not edited; corrections use reversal events."
    )
    add_heading(doc, "4.2 Bank statement matching", 2)
    add_body(
        doc,
        "The bank import uses a canonical synthetic CSV adapter. Each imported row retains source-file and row provenance. Deterministic matching considers the account, credit/debit direction, currency, amount, UTR/reference, registered UPI evidence and flat/bill references. A candidate is posted automatically only when the evidence uniquely identifies an eligible bill or payment and passes the configured checks. Amount-only, UPI-only, conflicting, overpaid, debit, reversed, uncleared or ambiguous rows are held for Accounts review. Preview does not post. Accounts approval rechecks the current state inside a transaction."
    )
    add_body(
        doc,
        "The matching logic does not use AI to authorize money movement. The synthetic test corpus is maintained under `tests/bank_corpus`; measured results belong in the generated verification report. No live bank API is connected."
    )
    add_heading(doc, "4.3 Complaints, AI and safety", 2)
    add_body(
        doc,
        "A resident submits a categorized or free-text complaint and may attach a photograph. The service assigns a team/staff member using operational rules, starts a response clock and records status changes in a timeline. Help Desk can correct the AI category/urgency suggestion; the human decision is stored separately from the original suggestion."
    )
    add_body(
        doc,
        "When configured, the backend calls Groq with a constrained output format. Provider failures, timeouts, malformed output or missing configuration use the local classifier or route the complaint to human review. The local model is trained on synthetic examples; production accuracy is not established. Deterministic emergency phrase rules create SafetyEvent records independently of AI. Similar complaints may be suggested for linking, but staff confirms the link and each resident ticket remains independently tracked."
    )
    add_heading(doc, "4.4 Visitor and gate operations", 2)
    add_body(
        doc,
        "A guard records a visitor at an assigned gate and captures a photograph. A resident with active permission for the target flat approves or rejects the visit. The guard records admission and exit after the allowed state transition. Pre-approved guest credentials are signed using an ECDSA P-256 key. Configure a stable `SIGNING_KEY` or protected `SIGNING_KEY_FILE` so credentials remain verifiable after a backend restart."
    )
    add_body(
        doc,
        "The guard PWA stages offline visit metadata and the actual photo Blob in IndexedDB. The queue records event/photo UUIDs, gate/device/generation, sequence, capture time, hash and upload state. A signed server time anchor is bound to the guard, gate and enrolled device. Reconnect synchronization uploads the image, checks its hash and acknowledges the event/photo before local photo bytes are removed. Offline entries remain pending; the offline path does not create resident approval. Browser tests must be run to prove reload/reconnect behaviour on a real browser."
    )
    add_body(
        doc,
        "Visitor-photo expiry is calculated from original capture time plus 90 days. Local operations use `python -m backend.app.jobs.purge_visitor_photos`; the hosted profile uses the token-protected `/api/v1/ops/retention/visitor-photos` endpoint, invoked daily by `.github/workflows/visitor-photo-retention.yml`. Local disk remains a development adapter; hosted files use authenticated Cloudinary assets and application-mediated reads. A PWA cannot run local expiry cleanup while the browser is closed or the tablet is powered off; a strict device-level guarantee depends on managed kiosk/OS policy or a native cleanup component. The scheduled workflow is configured in source but must be enabled and supplied with owner-managed secrets after deployment."
    )
    add_heading(doc, "4.5 Amenities, notices and committee reporting", 2)
    add_body(
        doc,
        "Amenity slots expose rules, fees and availability. Booking attempts are checked against slot capacity and resident eligibility; PostgreSQL concurrency behaviour needs PostgreSQL testing. Notices support draft/published/withdrawn status, all-resident or tower audiences, English/Hindi/Marathi text, revisions and read receipts keyed to the exact revision. Residents see active notices within their audience, with a visible English fallback label when their selected translation is unavailable."
    )
    add_body(
        doc,
        "The committee dashboard reports collections, outstanding dues, ageing bands and complaint response/resolution timing. Reports should identify their period and definitions. The client success measures (payment punctuality from 70% to 90%, an 80% reduction in matching time, and reopened complaints from 25% to below 8%) are targets, not results achieved by this prototype."
    )

    add_heading(doc, "5. Security and privacy")
    add_bullets(doc, [
        "API permissions are resolved from active server-side roles and flat memberships; guard operations also verify the assigned gate and enrolled device.",
        "Authentication cookies are HttpOnly and state-changing requests use CSRF protection. OTP challenges are stored as salted hashes and are rate-limited.",
        "Visitor photographs are stored outside public frontend assets, validated and re-encoded to strip image metadata, and served through short-lived application-signed URLs. Hosted storage uses Cloudinary authenticated delivery; public delivery URLs are not used.",
        "Visitor photo deletion uses original capture time. The scheduled endpoint requires a separate high-entropy token; failed object deletions are not marked successful and remain retryable.",
        "The current SMS provider is simulated for development/demo; the production placeholder fails closed because no real SMS gateway adapter is implemented.",
        "Synthetic names, phone numbers, complaints and bank rows are used. Do not place real resident data, photos or bank statements in the repository.",
    ])

    add_heading(doc, "6. User experience and localization")
    add_body(
        doc,
        "The visual direction uses a restrained palette, clear hierarchy and mobile-first layouts. Resident home exposes dues, open complaints and today's visitors. Staff screens prioritize queue state, urgency and the next action. The guard terminal uses high-contrast controls and visible connectivity/queue state. English, Marathi and Hindi dictionaries support resident and staff text; critical translation coverage should be verified with the frontend tests and narrow-screen browser review."
    )

    add_heading(doc, "7. Assumptions and scope boundaries")
    add_table(
        doc,
        ["Item", "Treatment in this prototype"],
        [
            ["Maintenance rate", "₹6.50/sq ft/month from the supplied brief."],
            ["Due date, grace period and late interest", "Illustrative configuration only; actual bye-law values require federation approval."],
            ["Payments", "Test/simulated only; no real funds are collected."],
            ["SMS and notifications", "Development/demo simulation; no live SMS transport or WhatsApp integration."],
            ["Bank data", "Synthetic canonical CSV; no live bank integration."],
            ["AI data", "Synthetic training examples; no production accuracy claim."],
            ["Gate storage", "Local private disk for development; Cloudinary Free authenticated assets for hosted preview."],
            ["Retention scheduler", "Daily GitHub Actions workflow calls a token-protected API route; enable it and add repository secrets after hosting."],
            ["External systems", "Tally, CCTV, boom barriers and live bank/payment systems are not integrated."],
        ],
        [2.0, 5.2],
    )

    add_heading(doc, "8. Verification evidence")
    gates = summary.get("gates", {})
    if not gates:
        add_body(doc, "No release-verification report was available when this document was generated. Run `python scripts/verify_release.py` and regenerate this document.")
    else:
        rows = []
        for name, result in gates.items():
            if name in {"backend_tests", "backend_tests_and_coverage", "backend_coverage"}:
                detail = extract_test_line(result)
                coverage = result.get("coverage_percentage")
                if coverage is not None:
                    detail += f"; coverage {coverage}%"
            elif name == "database_seed_and_ground_truth":
                if result.get("error"):
                    detail = result["error"]
                else:
                    counts = result.get("counts", {})
                    truth = result.get("ground_truth", {})
                    count_text = ", ".join(f"{key}: {value}" for key, value in counts.items())
                    balance_text = "; ".join(
                        f"{flat}: ₹{value.get('outstanding')} / {value.get('overdue_days')} days"
                        for flat, value in truth.items()
                    )
                    detail = f"{count_text}; {balance_text}; seed runs: {result.get('seed_runs', 'not recorded')}"
            elif name == "frontend_typescript":
                node_version = result.get("stdout", "").strip().splitlines()[0] if result.get("stdout") else "Node version not recorded"
                detail = f"TypeScript compiler exited 0 ({node_version})."
            elif name == "wording_scan":
                detail = f"{result.get('count', 'unknown')} finding(s)."
            else:
                detail = (
                    result.get("stderr", "")[:220].replace("\n", " ")
                    or result.get("stdout", "")[-220:].replace("\n", " ")
                    or result.get("status", "Not recorded")
                )
            rows.append([name, result.get("status", "UNKNOWN"), detail])
        add_table(doc, ["Check", "Result", "Evidence"], rows, [2.0, 0.9, 4.3])
        add_body(doc, f"Overall verifier result: {summary.get('overall_status', 'UNKNOWN')}. Full command outputs are recorded in `docs/reports/summary.json`.")

    add_heading(doc, "9. Known limitations and next work")
    add_bullets(doc, [
        "Run the Docker frontend build with the Node 24.15 builder image and execute browser-level PWA/offline tests in the deployed preview; the local container used for this revision had Node 22.16 and could not prove that build.",
        "Run PostgreSQL migration and concurrency tests against a disposable PostgreSQL service; SQLite does not prove row-lock behaviour.",
        "Complete the account-side Render/Neon/Cloudinary setup, enable the scheduled GitHub Actions workflow and verify a real 90-day purge on synthetic photo data before operational use.",
        "Integrate a real SMS gateway and payment provider only with approved accounts, credentials and end-to-end tests; run a measured load test and privacy/security review before operational use.",
        "Review billing and late-interest assumptions with the federation before using the application for real maintenance collections.",
    ])

    doc.core_properties.title = "Township One Technical Design Document"
    doc.core_properties.subject = "Gated township resident application — Brief 2"
    doc.core_properties.author = "Township One Project"
    doc.core_properties.keywords = "resident app, maintenance, complaints, visitors, bank reconciliation"
    doc.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    build_document()
