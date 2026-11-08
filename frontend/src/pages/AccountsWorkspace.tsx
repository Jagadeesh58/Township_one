import React, { useState, useEffect } from 'react';
import {
  api, BankAccountItem, BankRowItem, BankImportPreview, BankImportCommit, UserProfile
} from '../api/client';
import { Language, translations } from '../i18n/translations';
import { formatINR } from '../utils/money';

interface AccountsWorkspaceProps {
  user: UserProfile;
  lang: Language;
}

export const AccountsWorkspace: React.FC<AccountsWorkspaceProps> = ({ user, lang }) => {
  const t = translations[lang];

  const [accounts, setAccounts] = useState<BankAccountItem[]>([]);
  const [selectedAccountNo, setSelectedAccountNo] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Preview state
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<BankImportPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Commit state
  const [commitLoading, setCommitLoading] = useState<boolean>(false);
  const [commitResult, setCommitResult] = useState<BankImportCommit | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);

  // Review Queue state
  const [reviewRows, setReviewRows] = useState<BankRowItem[]>([]);
  const [reviewLoading, setReviewLoading] = useState<boolean>(false);
  const [reviewPage, setReviewPage] = useState<number>(1);
  const [totalReviewRows, setTotalReviewRows] = useState<number>(0);

  // Action Modal state
  const [activeActionRow, setActiveActionRow] = useState<BankRowItem | null>(null);
  const [actionType, setActionType] = useState<'APPROVE' | 'REJECT' | 'HOLD' | 'CORRECT_MAPPING'>('APPROVE');
  const [actionReason, setActionReason] = useState<string>('');
  const [targetFlatId, setTargetFlatId] = useState<string>('');
  const [actionSubmitting, setActionSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Import history
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    loadAccounts();
    loadReviewQueue();
    loadHistory();
  }, []);

  const loadAccounts = async () => {
    try {
      const list = await api.getBankAccounts();
      setAccounts(list);
      if (list.length > 0 && !selectedAccountNo) {
        setSelectedAccountNo(list[0].account_no);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadReviewQueue = async () => {
    setReviewLoading(true);
    try {
      const res = await api.getBankReviewQueue({ page: reviewPage, review_status: 'PENDING' });
      setReviewRows(res.items);
      setTotalReviewRows(res.total);
    } catch (e) {
      console.error(e);
    } finally {
      setReviewLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const items = await api.getBankImportHistory();
      setHistory(items);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setPreviewData(null);
      setPreviewError(null);
      setCommitResult(null);
      setCommitError(null);
    }
  };

  const handlePreview = async () => {
    if (!selectedFile) return;
    setPreviewLoading(true);
    setPreviewError(null);
    setCommitResult(null);
    try {
      const res = await api.previewBankStatement(selectedFile, selectedAccountNo);
      setPreviewData(res);
    } catch (err: any) {
      setPreviewError(err.message || 'Statement preview failed');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCommit = async () => {
    if (!previewData || !selectedAccountNo) return;
    setCommitLoading(true);
    setCommitError(null);
    try {
      const res = await api.commitBankStatement(selectedAccountNo, previewData.file_sha256);
      setCommitResult(res);
      // Reload queue and history after commit
      loadReviewQueue();
      loadHistory();
    } catch (err: any) {
      setCommitError(err.message || 'Statement commit failed');
    } finally {
      setCommitLoading(false);
    }
  };

  const openActionModal = (row: BankRowItem, action: 'APPROVE' | 'REJECT' | 'HOLD' | 'CORRECT_MAPPING') => {
    setActiveActionRow(row);
    setActionType(action);
    setActionReason('');
    setTargetFlatId(row.matched_flat_id || '');
    setActionError(null);
  };

  const submitAction = async () => {
    if (!activeActionRow) return;
    setActionSubmitting(true);
    setActionError(null);
    try {
      await api.submitBankReviewAction(activeActionRow.id, {
        action: actionType,
        target_flat_id: actionType === 'CORRECT_MAPPING' ? targetFlatId : undefined,
        reason: actionReason || `Action ${actionType} performed by ${user.name}`,
      });
      setActiveActionRow(null);
      loadReviewQueue();
    } catch (err: any) {
      setActionError(err.message || 'Action failed');
    } finally {
      setActionSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.8rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0, color: 'var(--text-main)' }}>
            {t.accounts_workspace}
          </h1>
          <p style={{ margin: '0.2rem 0 0 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            {t.bank_matching} • Dual-Entry Accounting & Ledger Reconciliation
          </p>
        </div>

        {/* Bank Account Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>Account:</span>
          <select
            value={selectedAccountNo}
            onChange={(e) => setSelectedAccountNo(e.target.value)}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              border: '1px solid var(--border)',
              background: '#f8fafc',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.account_no}>
                {acc.bank_name} ({acc.account_no})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Section 1: Statement Upload & Preview */}
      <div style={{ background: '#ffffff', borderRadius: '10px', border: '1px solid var(--border)', padding: '1.2rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: 0, marginBottom: '0.8rem' }}>
          {t.upload_statement}
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            style={{ fontSize: '0.85rem' }}
          />
          <button
            onClick={handlePreview}
            disabled={!selectedFile || previewLoading}
            style={{
              background: 'var(--primary)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: (!selectedFile || previewLoading) ? 'not-allowed' : 'pointer',
              opacity: (!selectedFile || previewLoading) ? 0.6 : 1,
            }}
          >
            {previewLoading ? t.processing : t.statement_preview}
          </button>
        </div>

        {previewError && (
          <div style={{ marginTop: '0.8rem', padding: '0.6rem 0.8rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', color: '#b91c1c', fontSize: '0.85rem' }}>
            ⚠️ {previewError}
          </div>
        )}

        {/* Preview Results Banner */}
        {previewData && (
          <div style={{ marginTop: '1.2rem' }}>
            <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
              <div style={{ padding: '0.6rem 0.9rem', background: '#f8fafc', border: '1px solid var(--border)', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Rows</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{previewData.total_rows}</div>
              </div>
              <div style={{ padding: '0.6rem 0.9rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.72rem', color: '#166534', textTransform: 'uppercase' }}>Valid Credit Total</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#166534' }}>{formatINR(previewData.total_credit)}</div>
              </div>
              <div style={{ padding: '0.6rem 0.9rem', background: '#fefce8', border: '1px solid #fef08a', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.72rem', color: '#854d0e', textTransform: 'uppercase' }}>Debit (Review) Total</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#854d0e' }}>{formatINR(previewData.total_debit)}</div>
              </div>
              <div style={{ padding: '0.6rem 0.9rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.72rem', color: '#991b1b', textTransform: 'uppercase' }}>{t.invalid_rows}</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#991b1b' }}>{previewData.invalid_rows}</div>
              </div>
            </div>

            {previewData.duplicate_file && (
              <div style={{ marginBottom: '1rem', padding: '0.6rem 0.8rem', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '6px', color: '#92400e', fontSize: '0.85rem' }}>
                ℹ️ <strong>{t.duplicate_file}:</strong> This exact file (SHA-256: {previewData.file_sha256.slice(0, 12)}...) was already imported. Committing will skip all previously committed rows idempotently.
              </div>
            )}

            {/* Preview Table */}
            <div style={{ overflowX: 'auto', border: '1px solid var(--border)', borderRadius: '6px', maxHeight: '350px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                    <th style={{ padding: '0.5rem 0.6rem' }}>#</th>
                    <th style={{ padding: '0.5rem 0.6rem' }}>Date</th>
                    <th style={{ padding: '0.5rem 0.6rem' }}>Narration</th>
                    <th style={{ padding: '0.5rem 0.6rem' }}>UTR / Ref</th>
                    <th style={{ padding: '0.5rem 0.6rem' }}>Payer UPI / Flat</th>
                    <th style={{ padding: '0.5rem 0.6rem', textAlign: 'right' }}>Amount</th>
                    <th style={{ padding: '0.5rem 0.6rem', textAlign: 'center' }}>Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {previewData.rows.map((r, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '0.45rem 0.6rem', color: 'var(--text-muted)' }}>{r.original_row_number}</td>
                      <td style={{ padding: '0.45rem 0.6rem', whiteSpace: 'nowrap' }}>{r.txn_date ? r.txn_date.slice(0, 10) : '-'}</td>
                      <td style={{ padding: '0.45rem 0.6rem', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={r.narration}>
                        {r.narration || '-'}
                      </td>
                      <td style={{ padding: '0.45rem 0.6rem', fontFamily: 'monospace' }}>{r.utr || '-'}</td>
                      <td style={{ padding: '0.45rem 0.6rem' }}>{r.payer_upi || r.flat_ref || '-'}</td>
                      <td style={{ padding: '0.45rem 0.6rem', textAlign: 'right', fontWeight: 600 }}>{formatINR(r.amount || 0)}</td>
                      <td style={{ padding: '0.45rem 0.6rem', textAlign: 'center' }}>
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          background:
                            r.candidate_decision === 'AUTO_MATCH' ? '#dcfce7' :
                            r.candidate_decision === 'REVIEW' ? '#fef9c3' :
                            r.candidate_decision === 'DUPLICATE_NO_OP' ? '#e2e8f0' : '#fee2e2',
                          color:
                            r.candidate_decision === 'AUTO_MATCH' ? '#15803d' :
                            r.candidate_decision === 'REVIEW' ? '#a16207' :
                            r.candidate_decision === 'DUPLICATE_NO_OP' ? '#475569' : '#b91c1c',
                        }}>
                          {r.candidate_decision}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Commit Button */}
            <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <button
                onClick={handleCommit}
                disabled={commitLoading}
                style={{
                  background: '#16a34a',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '0.6rem 1.2rem',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  cursor: commitLoading ? 'not-allowed' : 'pointer',
                  opacity: commitLoading ? 0.7 : 1,
                }}
              >
                {commitLoading ? 'Committing & Posting...' : `✅ ${t.commit_statement}`}
              </button>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Atomic database commit • Idempotent by (account_no, file_sha256)
              </span>
            </div>

            {commitError && (
              <div style={{ marginTop: '0.8rem', padding: '0.6rem 0.8rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', color: '#b91c1c', fontSize: '0.85rem' }}>
                ❌ {commitError}
              </div>
            )}

            {commitResult && (
              <div style={{ marginTop: '1rem', padding: '0.8rem 1rem', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '6px' }}>
                <h3 style={{ margin: '0 0 0.4rem 0', color: '#166534', fontSize: '0.95rem' }}>
                  Statement Processed Successfully ({commitResult.status})
                </h3>
                <div style={{ fontSize: '0.82rem', color: '#14532d', display: 'flex', gap: '1.2rem', flexWrap: 'wrap' }}>
                  <span>Auto-Matched & Settled: <strong>{commitResult.auto_matched_rows}</strong></span>
                  <span>Held for Review: <strong>{commitResult.held_for_review_rows}</strong></span>
                  <span>Duplicates Skipped: <strong>{commitResult.duplicate_rows}</strong></span>
                  <span>Total Amount Posted: <strong>{formatINR(commitResult.total_credit_settled)}</strong></span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Section 2: Review Queue (Human-in-the-Loop) */}
      <div style={{ background: '#ffffff', borderRadius: '10px', border: '1px solid var(--border)', padding: '1.2rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0 }}>
              {t.review_queue} ({totalReviewRows} items)
            </h2>
            <p style={{ margin: '0.2rem 0 0 0', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              Rows requiring accounts review (partial payments, unmatched UPIs, debit charges)
            </p>
          </div>
          <button
            onClick={loadReviewQueue}
            style={{
              background: '#f8fafc',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '0.35rem 0.7rem',
              fontSize: '0.8rem',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            🔄 Refresh Queue
          </button>
        </div>

        {reviewLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Loading review items...
          </div>
        ) : reviewRows.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            🎉 No transactions currently waiting in the review queue.
          </div>
        ) : (
          <div style={{ overflowX: 'auto', border: '1px solid var(--border)', borderRadius: '6px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ background: '#f8fafc', borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                  <th style={{ padding: '0.5rem 0.6rem' }}>Date</th>
                  <th style={{ padding: '0.5rem 0.6rem' }}>Narration</th>
                  <th style={{ padding: '0.5rem 0.6rem' }}>UTR</th>
                  <th style={{ padding: '0.5rem 0.6rem' }}>Payer UPI / Flat</th>
                  <th style={{ padding: '0.5rem 0.6rem', textAlign: 'right' }}>Amount</th>
                  <th style={{ padding: '0.5rem 0.6rem' }}>Reason Held</th>
                  <th style={{ padding: '0.5rem 0.6rem', textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reviewRows.map((row) => (
                  <tr key={row.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '0.45rem 0.6rem', whiteSpace: 'nowrap' }}>{row.txn_date ? row.txn_date.slice(0, 10) : '-'}</td>
                    <td style={{ padding: '0.45rem 0.6rem', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={row.narration}>
                      {row.narration || '-'}
                    </td>
                    <td style={{ padding: '0.45rem 0.6rem', fontFamily: 'monospace' }}>{row.utr || '-'}</td>
                    <td style={{ padding: '0.45rem 0.6rem' }}>{row.payer_upi || row.flat_ref || '-'}</td>
                    <td style={{ padding: '0.45rem 0.6rem', textAlign: 'right', fontWeight: 600 }}>{formatINR(row.amount || 0)}</td>
                    <td style={{ padding: '0.45rem 0.6rem', color: '#92400e', fontSize: '0.75rem' }}>{row.decision_reason || 'Pending verification'}</td>
                    <td style={{ padding: '0.45rem 0.6rem', textAlign: 'center' }}>
                      <div style={{ display: 'flex', gap: '0.3rem', justifyContent: 'center' }}>
                        <button
                          onClick={() => openActionModal(row, 'APPROVE')}
                          title="Approve & Post"
                          style={{ background: '#16a34a', color: '#fff', border: 'none', borderRadius: '4px', padding: '3px 7px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600 }}
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => openActionModal(row, 'CORRECT_MAPPING')}
                          title="Remap Flat"
                          style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', padding: '3px 7px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600 }}
                        >
                          Remap
                        </button>
                        <button
                          onClick={() => openActionModal(row, 'HOLD')}
                          title="Hold"
                          style={{ background: '#ca8a04', color: '#fff', border: 'none', borderRadius: '4px', padding: '3px 7px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600 }}
                        >
                          Hold
                        </button>
                        <button
                          onClick={() => openActionModal(row, 'REJECT')}
                          title="Reject"
                          style={{ background: '#dc2626', color: '#fff', border: 'none', borderRadius: '4px', padding: '3px 7px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600 }}
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Review Action Modal */}
      {activeActionRow && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100
        }}>
          <div style={{ background: '#ffffff', borderRadius: '10px', padding: '1.5rem', width: '480px', maxWidth: '92vw' }}>
            <h3 style={{ marginTop: 0, marginBottom: '0.5rem' }}>
              Confirm Review Action: {actionType}
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '0 0 1rem 0' }}>
              Transaction: UTR {activeActionRow.utr} • Amount {formatINR(activeActionRow.amount || 0)}
            </p>

            {actionType === 'CORRECT_MAPPING' && (
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                  Target Flat ID / UUID:
                </label>
                <input
                  type="text"
                  value={targetFlatId}
                  onChange={(e) => setTargetFlatId(e.target.value)}
                  placeholder="Enter Flat ID"
                  style={{ width: '100%', padding: '0.45rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
                />
              </div>
            )}

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                Reason / Audit Note:
              </label>
              <textarea
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                placeholder="Reason for this review decision..."
                rows={3}
                style={{ width: '100%', padding: '0.45rem', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}
              />
            </div>

            {actionError && (
              <div style={{ marginBottom: '1rem', padding: '0.5rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', color: '#b91c1c', fontSize: '0.8rem' }}>
                {actionError}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => setActiveActionRow(null)}
                style={{ border: '1px solid var(--border)', background: '#fff', borderRadius: '6px', padding: '0.45rem 0.9rem', fontSize: '0.85rem', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                onClick={submitAction}
                disabled={actionSubmitting}
                style={{
                  background: actionType === 'APPROVE' ? '#16a34a' : actionType === 'REJECT' ? '#dc2626' : 'var(--primary)',
                  color: '#fff', border: 'none', borderRadius: '6px', padding: '0.45rem 1rem', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer'
                }}
              >
                {actionSubmitting ? 'Saving...' : `Confirm ${actionType}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
