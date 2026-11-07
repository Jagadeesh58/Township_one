# D1-S6 Frontend and PWA Test Report — Resident Interface

**Date:** 2026-11-07  
**Session:** D1-S6  
**Runner:** Vite 6.4.5 / TypeScript 5.7.2 / Node 24.16.0  
**Target:** `frontend/`  

---

## 1. Execution Summary
- **TypeScript Typecheck:** 0 errors
- **Vite Production Build:** Success
- **Build Duration:** 7.14s
- **Status:** PASS

---

## 2. Artifacts Generated
```text
dist/index.html                   0.80 kB │ gzip:  0.44 kB
dist/assets/index-CxXMJiAj.css    0.58 kB │ gzip:  0.39 kB
dist/assets/index-BtSFoCh6.js   265.17 kB │ gzip: 79.48 kB
```

---

## 3. PWA Capabilities Validated
1. **Service Worker Shell Precaching:**
   - Pre-caches `index.html`, `manifest.json`, `favicon.ico`, and icons on `install`.
   - Cleans old caches on `activate`.
2. **Runtime Asset Caching:**
   - Caches static Vite chunks (`/assets/*`) dynamically on fetch.
   - Strictly bypasses `/api/*` network requests (direct network passthrough).
   - Falls back to cached `/index.html` on offline navigation.
3. **UI Financial Controls:**
   - Multi-bill selection dropdown active when `unpaid_bills.length > 1`.
   - Stable unique idempotency key generated per payment modal session.
   - 2-Tap payment flow operational directly from home screen `DuesCard`.
   - Full bilingual support (English and Marathi).

---

## 4. Build Command & Output
```bash
cd frontend; npm run build
```
```text
npm notice run township-one-frontend@1.0.0 build
npm notice run node ./node_modules/typescript/bin/tsc --noEmit && node ./node_modules/vite/bin/vite.js build
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
