# Reviewer Walkthrough

This route is designed to show the Brief 2 core workflows before exploring additional functions. Use a freshly seeded local database and the development/demo OTP. The identities are synthetic.

## Local startup

Follow the root `deployment.md` instructions. Confirm that migrations and the single seed command have run before opening the app.

## Resident and maintenance

1. Sign in as Swati Joshi (`9876543211`) with development/demo OTP `123456`.
2. Confirm flat T12-0408, outstanding maintenance of ₹6,370.00 and 47 overdue days in the `2026-11-06` seed snapshot.
3. Open the bill and inspect the area × rate calculation and separately labelled illustrative late-fee rule.
4. Use test payment. Confirm that a successful test result creates the receipt and updates the flat ledger. Do not describe this as a real bank or payment-gateway transaction.
5. Open the resident notice list and inspect language fallback and revision-specific read tracking.

## Complaint and AI

1. Create a water-supply or lift complaint.
2. Inspect the AI category/urgency suggestion and provider/fallback information.
3. Sign in as Help Desk (`9876543220`) and inspect assignment, response timer and status actions.
4. Correct a suggestion and verify that the human decision is preserved.
5. Submit an emergency example and inspect the deterministic safety escalation.
6. Inspect the related lift incident group. Each resident complaint must remain individually visible.

## Bank reconciliation

1. Sign in as Accounts (`9876543240`).
2. Import the synthetic CSV fixture.
3. Inspect one strong-evidence candidate and at least one ambiguous/review item.
4. Confirm that preview does not post and that unclear rows remain in the Accounts review queue.
5. Inspect the resulting ledger only after an authorized decision.

## Gate visitor workflow

1. Sign in as Guard (`9876543230`), assigned to Gate 1 in the seed.
2. Capture an online visitor and photograph.
3. Sign in as the linked resident and approve or reject.
4. Record admission and exit from the guard account.
5. To inspect offline behaviour, enroll the device while online, obtain a signed time anchor, disconnect the network, capture a visitor with a photo, reload while still offline, reconnect and verify that one event and one photo are acknowledged. Do not claim this browser journey passed unless it was actually exercised.
6. Explain that local expiry cleanup cannot run while the browser is stopped and requires device-management controls for a strict powered-off-device guarantee.

## Amenity and committee

1. Sign in as a resident and inspect amenity rules, fees and available slots.
2. Attempt a booking and verify the displayed result.
3. Sign in as Committee (`9876543250`).
4. Review collection, dues ageing and complaint metrics.
5. Open the notice editor, create a draft, publish a tower-targeted notice and inspect its revision history.
6. Confirm that only residents in the target audience see that notice.

## Close-out

Show the README verification table and `docs/reports/summary.json`. Identify mocked integrations and unverified infrastructure plainly. Do not use screenshots as substitutes for failed live checks.
