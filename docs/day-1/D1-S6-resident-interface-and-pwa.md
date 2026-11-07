# D1-S6 — Resident Interface and PWA

**Day:** Day 1  
**Session ID:** D1-S6  
**Session Name:** Resident interface and PWA  
**Responsibility:** Resident home, billing, payment UI, icons, offline shell and error states  

---

## 1. Objective
Deliver a responsive, mobile-first Progressive Web App (PWA) resident interface in React + TypeScript + Vite. Support 2-tap direct dues payment from the home screen, multi-flat switching, localized bilingual text (English and Marathi), offline shell caching with runtime asset caching, and strict network passthrough for API endpoints.

---

## 2. Files Created or Modified
- `frontend/src/api/client.ts` — Extended `BillingSummary` interface with `total_outstanding_due`, `total_outstanding_due_inr`, and `unpaid_bills` array; API fetch wrapper.
- `frontend/src/components/PaymentModal.tsx` — Multi-bill selection dropdown for flats with multiple outstanding bills, stable idempotency key generation per payment attempt, deliberate test outcome buttons (SUCCESS, PENDING, FAILED, EXPIRED), and error handling.
- `frontend/src/components/DuesCard.tsx` — 2-tap payment call to action displaying total outstanding dues, multi-bill count, area-rate calculations, and late fee warnings.
- `frontend/src/pages/ResidentHomePage.tsx` — Clean resident dashboard displaying active flat memberships, welcome banner, quick action cards, dues card, and tab switcher.
- `frontend/public/sw.js` — Service Worker caching strategy: precaching shell assets (index.html, manifest, icons), runtime caching for hashed Vite bundles (`/assets/*`), offline navigation fallback to cached shell, and strict bypass for `/api/*` routes.
- `frontend/package.json` — Direct node path scripts for reliable Windows cross-platform builds.

---

## 3. Implementation Completed
1. **2-Tap Resident Payment CTA:**
   - Tap 1: Click "Pay Now" on `DuesCard` from home screen -> Opens `PaymentModal`.
   - Tap 2: Click "Confirm Payment" in `PaymentModal` -> Executes `/payments/checkout` and displays official `ReceiptModal`.
2. **Multi-Bill Selection:**
   - When a resident owes multiple unpaid bills (e.g. Swati Joshi with August and September bills), the modal displays a select dropdown with bill periods and balances, allowing targeted bill settlement.
3. **PWA Offline Shell & Caching Rules:**
   - Pre-caches core app shell on install (`/`, `/index.html`, `/manifest.json`, `/icons/*`, `/favicon.ico`).
   - Caches runtime hashed JS and CSS assets (`/assets/*.js`, `/assets/*.css`).
   - Strictly passes all `/api/*` network requests through without caching to prevent stale financial or session data.
   - For offline navigation requests, falls back to `/index.html`.
4. **Bilingual Localization:**
   - Full English and Marathi support across all labels, dues tags, and receipt cards.

---

## 4. UI Components
- `ResidentHomePage`: Main resident portal.
- `DuesCard`: Home screen maintenance dues card.
- `PaymentModal`: Test payment checkout modal.
- `ReceiptModal`: Official receipt view with transaction reference and print/download options.
- `LedgerView`: Running ledger of debits and credits.

---

## 5. Build and Validation Results
Command:
```bash
cd frontend; npm run build
```
Output:
```text
vite v6.4.5 building for production...
transforming...
✓ 39 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.80 kB │ gzip:  0.44 kB
dist/assets/index-CxXMJiAj.css    0.58 kB │ gzip:  0.39 kB
dist/assets/index-BtSFoCh6.js   265.17 kB │ gzip: 79.48 kB
✓ built in 7.14s
```

---

## 6. Acceptance Criteria
- [x] Responsive PWA compiles with 0 TypeScript and 0 Vite errors.
- [x] 2-tap payment flow operational from resident home screen.
- [x] Multi-bill selection supported in payment modal.
- [x] Service worker strictly bypasses `/api/*` requests while caching app shell.

---

## 7. Remaining Defects or Limitations
- Push notifications via web push API will be activated in Day 2 for complaint status transitions.
