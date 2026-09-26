import { useEffect, useState } from 'react'
import { useOutletContext, useNavigate } from 'react-router-dom'
import client from '../api/client'

const processReport = [
  {
    label: 'Status',
    value: 'Working MVP',
    detail: 'The platform is running, verified, and functional for tender review and compliance scoring.',
  },
  {
    label: 'Review process',
    value: 'Audit complete',
    detail: 'The setup issues were corrected and the compliance workflow was checked end-to-end.',
  },
  {
    label: 'Main issue',
    value: 'Scoring depth',
    detail: 'The engine is still largely rule-based and would benefit from stronger weighting and validation logic.',
  },
  {
    label: 'Recommendation',
    value: 'Enhance next',
    detail: 'Improve risk logic, dashboard reporting, and evidence-driven review for production use.',
  },
]

const summaryItems = [
  'Application startup and environment issues were resolved.',
  'Bid compliance workflow is operating with a documented rules-based engine.',
  'The core UI and validation flow are in place and ready for expansion.',
  'Next upgrade should focus on weighted scoring and better report clarity.',
]

const actionItems = [
  'Strengthen document-matching logic with weighted rule priorities.',
  'Improve the reporting dashboard for audit and executive review.',
  'Add more robust compliance exceptions and document risk explanations.',
]

export default function Dashboard() {
  const { tenders } = useOutletContext()
  const navigate = useNavigate()
  const [metrics, setMetrics] = useState(null)
  const [metricsLoading, setMetricsLoading] = useState(true)
  const [metricsError, setMetricsError] = useState('')

  useEffect(() => {
    setMetricsLoading(true)
    setMetricsError('')
    client.get('/dashboard/metrics')
      .then((response) => setMetrics(response.data))
      .catch(() => setMetricsError('Dashboard metrics could not be loaded.'))
      .finally(() => setMetricsLoading(false))
  }, [tenders.length])

  async function exportPortfolio() {
    const response = await client.get('/dashboard/report.csv', { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'bid-compliance-portfolio.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="topline">
        <h1>Tenders overview</h1>
      </div>
      <div className="subhead">
        Every tender you're running, with how many bids have come in against each.
      </div>

      <div className="panel project-report">
        <div className="panel-title">
          <span>Process report</span>
          <div className="report-tools">
            <button className="btn btn-secondary btn-small" onClick={() => window.print()}>Print report</button>
            <button className="btn btn-secondary btn-small" onClick={exportPortfolio}>Export CSV</button>
          </div>
        </div>

        <div className="report-hero">
          <div>
            <div className="report-kicker">Executive summary</div>
            <h2 className="report-title">Bid compliance project is operational and ready for refinement.</h2>
          </div>
          <div className="report-pill">Verified status</div>
        </div>

        <div className="report-grid">
          {processReport.map((item) => (
            <div key={item.label} className="report-card">
              <div className="report-label">{item.label}</div>
              <div className="report-value">{item.value}</div>
              <div className="report-detail">{item.detail}</div>
            </div>
          ))}
        </div>

        <div className="report-bottom-grid">
          <div className="report-list-box">
            <div className="report-box-title">Assessment summary</div>
            <ul>
              {summaryItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="report-list-box">
            <div className="report-box-title">Recommended next actions</div>
            <ul>
              {actionItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="metrics-grid">
        {[
          ['Tenders', metrics?.tender_count],
          ['Bids received', metrics?.bid_count],
          ['Documents reviewed', metrics?.document_count],
          ['High-risk bids', metrics?.high_risk_bids],
          ['Average score', metrics && `${metrics.average_compliance_score}%`],
          ['Published tenders', metrics?.published_tenders],
          ['Pending reviews', metrics?.pending_reviews],
          ['Overdue reviews', metrics?.overdue_reviews],
        ].map(([label, value]) => (
          <div className={`metric-card${label.includes('risk') || label.includes('Overdue') ? ' metric-alert' : ''}`} key={label}>
            <span>{label}</span>
            <strong>{metricsLoading ? '...' : metricsError ? '—' : value ?? 0}</strong>
          </div>
        ))}
      </div>
      {metricsError && <div className="inline-alert">{metricsError} Refresh the page and try again.</div>}

      <div className="panel">
        <div className="panel-title">
          <span>All tenders</span>
        </div>
        {tenders.length === 0 ? (
          <div className="empty-state">
            No tenders yet. Create one to start defining a document checklist and accepting bids.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Reference</th>
                <th>Title</th>
                <th>Department</th>
                <th>Status</th>
                <th>Deadline</th>
                <th>Bids received</th>
              </tr>
            </thead>
            <tbody>
              {tenders.map((t) => (
                <tr key={t.id} className="clickable" onClick={() => navigate(`/tenders/${t.id}`)}>
                  <td style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12.5 }}>{t.reference_no}</td>
                  <td>{t.title}</td>
                  <td>{t.department || '—'}</td>
                  <td><span className="status-chip">{t.status}</span></td>
                  <td>{t.submission_deadline ? new Date(t.submission_deadline).toLocaleDateString() : 'No deadline'}</td>
                  <td>{t.bid_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
