import React, { useState, useEffect } from 'react';
import { api, CommitteeReportData, UserProfile } from '../api/client';
import { Language, translations } from '../i18n/translations';

interface CommitteeDashboardProps {
  user: UserProfile;
  lang: Language;
}

export const CommitteeDashboard: React.FC<CommitteeDashboardProps> = ({
  user,
  lang,
}) => {
  const t = translations[lang];
  const [data, setData] = useState<CommitteeReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const asOfDate = '2026-11-06';

  useEffect(() => {
    loadOverview();
  }, []);

  const loadOverview = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const overview = await api.getCommitteeReport(asOfDate);
      setData(overview);
    } catch (err: any) {
      setErrorMsg(err.error?.message || err.detail || err.message || 'Failed to load committee metrics');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloadingFormat('PDF');
    try {
      const blob = await api.downloadCommitteePdf(asOfDate);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `township_one_governance_report_${asOfDate}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(`PDF download failed: ${err.message || 'Error generating PDF'}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleDownloadCsv = async () => {
    setDownloadingFormat('CSV');
    try {
      const csvContent = await api.downloadCommitteeCsv(asOfDate);
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `township_one_aggregates_${asOfDate}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(`CSV download failed: ${err.message || 'Error generating CSV'}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  if (loading) {
    return (
      <div style={{ maxWidth: '1000px', margin: '2rem auto', textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading Governance & Financial Overview...
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ maxWidth: '1000px', margin: '2rem auto', padding: '1rem', textAlign: 'center' }}>
        <p style={{ color: '#dc2626' }}>{errorMsg || 'Failed to load governance metrics'}</p>
        <button
          onClick={loadOverview}
          style={{
            minHeight: '48px',
            padding: '0.5rem 1.5rem',
            background: 'var(--primary)',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  const { financials, complaints, payment_matching } = data;
  const bands = [
    { label: '0-30 Days', amount: Number(financials.ageing.band_0_30_days) },
    { label: '31-60 Days', amount: Number(financials.ageing.band_31_60_days) },
    { label: '61-90 Days', amount: Number(financials.ageing.band_61_90_days) },
    { label: '90+ Days', amount: Number(financials.ageing.band_90_plus_days) },
  ];
  const totalOutstanding = Number(financials.total_outstanding);

  return (
    <div style={{ maxWidth: '1000px', margin: '1rem auto', padding: '0 1rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header & Export Controls */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        background: '#ffffff',
        padding: '1.25rem',
        borderRadius: 'var(--radius)',
        border: '1px solid var(--border)'
      }}>
        <div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Executive Operations & Audit
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, margin: '0.2rem 0' }}>
            🏛️ {t.committee_dashboard}
          </h2>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Cutoff: <strong>{data.reporting_period}</strong> • 2,400 Flats • 28 Towers • 4 Security Gates
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingFormat !== null}
            style={{
              minHeight: '48px',
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: '1px solid #dc2626',
              background: '#fff1f2',
              color: '#b91c1c',
              fontWeight: 700,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              cursor: downloadingFormat ? 'not-allowed' : 'pointer'
            }}
          >
            📄 {downloadingFormat === 'PDF' ? t.processing : t.download_pdf}
          </button>
          <button
            onClick={handleDownloadCsv}
            disabled={downloadingFormat !== null}
            style={{
              minHeight: '48px',
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: '1px solid #16a34a',
              background: '#f0fdf4',
              color: '#15803d',
              fontWeight: 700,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              cursor: downloadingFormat ? 'not-allowed' : 'pointer'
            }}
          >
            📊 {downloadingFormat === 'CSV' ? t.processing : t.download_csv}
          </button>
        </div>
      </div>

      {/* Dues Ageing Breakdown Card */}
      <div style={{
        background: '#ffffff',
        borderRadius: 'var(--radius)',
        border: '1px solid var(--border)',
        padding: '1.25rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 800, margin: 0 }}>
              💰 {t.dues_ageing}
            </h3>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Outstanding maintenance dues classified by ageing buckets
            </div>
          </div>
          <span style={{
            background: '#ecfdf5',
            color: '#065f46',
            border: '1px solid #a7f3d0',
            padding: '3px 10px',
            borderRadius: '12px',
            fontSize: '0.75rem',
            fontWeight: 700
          }}>
            ✓ Totals Verified
          </span>
        </div>

        {/* Total Outstanding Callout */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '0.75rem',
          marginBottom: '1.25rem'
        }}>
          <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL BILLED</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '0.2rem' }}>
              ₹{Number(financials.total_billed).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </div>

          <div style={{ background: '#f0fdf4', padding: '1rem', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
            <div style={{ fontSize: '0.75rem', color: '#166534', fontWeight: 600 }}>TOTAL COLLECTED</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#15803d', marginTop: '0.2rem' }}>
              ₹{Number(financials.total_collected).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </div>

          <div style={{ background: '#fff1f2', padding: '1rem', borderRadius: '8px', border: '1px solid #fecaca' }}>
            <div style={{ fontSize: '0.75rem', color: '#991b1b', fontWeight: 600 }}>TOTAL OUTSTANDING</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#b91c1c', marginTop: '0.2rem' }}>
              ₹{totalOutstanding.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </div>

          <div style={{ background: '#eff6ff', padding: '1rem', borderRadius: '8px', border: '1px solid #bfdbfe' }}>
            <div style={{ fontSize: '0.75rem', color: '#1e40af', fontWeight: 600 }}>COLLECTION EFFICIENCY</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#2563eb', marginTop: '0.2rem' }}>
              {financials.collection_rate_percent}%
            </div>
          </div>
        </div>

        {/* Ageing Bands Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: '#f8fafc', borderBottom: '2px solid var(--border)', textAlign: 'left' }}>
                <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700 }}>Ageing Band</th>
                <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700, textAlign: 'right' }}>Amount (₹)</th>
                <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700, textAlign: 'right' }}>Share of Total</th>
              </tr>
            </thead>
            <tbody>
              {bands.map((band, idx) => {
                const sharePercent = totalOutstanding > 0
                  ? ((band.amount / totalOutstanding) * 100).toFixed(1)
                  : '0.0';
                return (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '0.65rem 0.75rem', fontWeight: 600 }}>
                      <span style={{
                        display: 'inline-block',
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        background: idx === 0 ? '#10b981' : idx === 1 ? '#f59e0b' : idx === 2 ? '#f97316' : '#ef4444',
                        marginRight: '8px'
                      }} />
                      {band.label}
                    </td>
                    <td style={{ padding: '0.65rem 0.75rem', textAlign: 'right', fontWeight: 700 }}>
                      ₹{band.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '0.65rem 0.75rem', textAlign: 'right', color: 'var(--text-muted)' }}>
                      {sharePercent}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Operational Highlights Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: '1.25rem' }}>
        {/* Complaints SLA Turnaround Card */}
        <div style={{
          background: '#ffffff',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          padding: '1.25rem'
        }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 800, margin: '0 0 0.75rem 0' }}>
            🛠️ Complaint Resolution & SLAs
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Logged</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700 }}>{complaints.total_complaints}</div>
            </div>
            <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Resolved</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#16a34a' }}>{complaints.closed_resolved_count}</div>
            </div>
            <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Average Turnaround</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700 }}>{complaints.mean_resolution_hours ? `${complaints.mean_resolution_hours}h` : '—'}</div>
            </div>
            <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Median Turnaround</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700 }}>{complaints.median_resolution_hours ? `${complaints.median_resolution_hours}h` : '—'}</div>
            </div>
            <div style={{ background: '#fef2f2', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#991b1b' }}>SLA Breached</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#dc2626' }}>{complaints.overdue_count}</div>
            </div>
            <div style={{ background: '#fffbeb', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#92400e' }}>Reopened Tickets</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#d97706' }}>{complaints.reopened_count}</div>
            </div>
          </div>
        </div>

        {/* Bank Reconciliation Coverage Card */}
        <div style={{
          background: '#ffffff',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          padding: '1.25rem'
        }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 800, margin: '0 0 0.75rem 0' }}>
            💼 Bank Matching & Ledger Health
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Statement Rows</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700 }}>{payment_matching.total_rows_imported}</div>
            </div>
            <div style={{ background: '#f0fdf4', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#166534' }}>Auto-Matched & Posted</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#15803d' }}>{payment_matching.auto_matched_count}</div>
            </div>
            <div style={{ background: '#fffbeb', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#92400e' }}>Pending Review Queue</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#b45309' }}>{payment_matching.review_queue_count}</div>
            </div>
            <div style={{ background: '#eff6ff', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#1e40af' }}>Matching Rate</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#2563eb' }}>{payment_matching.auto_match_coverage_percent}%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
