# Frontend Validation Status

## TypeScript

The standalone TypeScript compilation command passed in this checkout:

```bash
node node_modules/typescript/bin/tsc --noEmit --pretty false
```

Exit code: `0`. The report is stored in `docs/reports/frontend-validation.json`.

## Vitest and production build

The project declares a supported Node range beginning at Node 22.22.2 (or Node 24.15.0 and later supported lines). The available runtime in this environment is Node 22.16.0.

The supplied `node_modules` was populated for Windows and contains `@rollup/rollup-win32-*`, not the Linux optional Rollup package required by this container. Vitest exits during startup with `Cannot find module @rollup/rollup-linux-x64-gnu`. A fresh `npm ci` attempt in this environment did not complete because npm registry access stalled; an offline retry confirmed that the required package tarball was not cached. The existing local `node_modules` directory must not be used as evidence.

Therefore these checks remain unverified here:

```bash
npm ci
npm test
npm run build
```

The test code includes a FileReader fallback for jsdom Blob implementations without `Blob.arrayBuffer()`, and the test setup provides Node WebCrypto for SHA-256. It also includes API fetch mocks for relative URL handling and dedicated notice/gate queue component tests. These changes are not claimed as Vitest-verified until the suite is run with a supported Node version and a clean Linux dependency install.

Do not use the existing cached `node_modules` directory as verification evidence. CI specifies Node 22.22.2 and installs dependencies with `npm ci`; its actual run is still required to verify the browser test and production build jobs.
