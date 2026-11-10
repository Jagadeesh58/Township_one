# Township One — Payments, Reconciliation and Receipts

## Test payment behaviour

The resident payment flow is a simulated test checkout. It does not collect money from a bank account, card or UPI handle.

Supported test outcomes:

- `SUCCESS`: posts the validated payment allocation and creates a receipt.
- `PENDING`: leaves the bill outstanding while the test transaction is pending.
- `FAILED`: does not reduce the outstanding balance.
- `EXPIRED`: does not reduce the outstanding balance.

Invalid outcome values are rejected by request validation. A receipt is created only for a successfully posted test payment.

## Idempotency

A payment request includes an idempotency key. The backend binds the key to the authenticated principal and request details. Repeating the same logical request returns the original logical result rather than creating another payment. Reusing a key with different request details returns a conflict response. Responses must not disclose another resident's payment or receipt details.

## Allocation and balances

The service checks the bill's current outstanding balance before allocating a payment. Partial payment is supported, subject to the bill-specific intent and current balance. An allocation must belong to the same flat and bill as the validated payment intent. Overpayments and ambiguous allocations are rejected or sent to Accounts review; they are not silently distributed as resident credit.

Posted financial records should not be mutated. A correction uses an auditable compensating reversal or adjustment. Monetary arithmetic uses `Decimal` and numeric database columns.

## Concurrency evidence

The current local focused run is recorded in `docs/reports/payment-safety-validation.md`. SQLite passed the non-locking payment and precision tests. Three PostgreSQL row-lock tests were skipped because this execution environment did not provide PostgreSQL. The code's `SELECT ... FOR UPDATE` path is not considered verified until the PostgreSQL CI job or a local PostgreSQL test run passes.

## Bank statement matching

The bank importer accepts the project's documented synthetic CSV format. Rows retain import and source-row provenance. A row is eligible for automatic matching only when the evidence uniquely identifies an eligible bill or existing test payment and passes the configured account, direction, currency, reference, UPI, amount and duplicate checks. Amount-only, UPI-only, conflicting and otherwise ambiguous rows are held for Accounts review. Preview does not post a payment. Accounts approval revalidates current evidence and outstanding balance inside a database transaction.

The application does not connect to a live bank API and does not replace Tally.
