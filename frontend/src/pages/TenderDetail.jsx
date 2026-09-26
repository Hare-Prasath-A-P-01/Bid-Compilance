import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import client from '../api/client'
import RiskBadge from '../components/RiskBadge'

export default function TenderDetail() {
  const { tenderId } = useParams()
  const navigate = useNavigate()
  const [tender, setTender] = useState(null)
  const [bids, setBids] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [bidderName, setBidderName] = useState('')
  const [bidderCompany, setBidderCompany] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const nextStatuses = {
    Draft: ['Published', 'Archived'],
    Published: ['Closed', 'Archived'],
    Closed: ['Awarded', 'Archived'],
    Awarded: ['Archived'],
    Archived: [],
  }

  async function load() {
    const [t, b] = await Promise.all([
      client.get(`/tenders/${tenderId}`),
      client.get(`/tenders/${tenderId}/bids`),
    ])
    setTender(t.data)
    setBids(b.data)
  }

  useEffect(() => {
    load()
    setShowForm(false)
  }, [tenderId])

  async function handleAddBid(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const { data } = await client.post(`/tenders/${tenderId}/bids`, {
        bidder_name: bidderName,
        bidder_company: bidderCompany,
      })
      setBidderName('')
      setBidderCompany('')
      setShowForm(false)
      navigate(`/tenders/${tenderId}/bids/${data.id}`)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not register bid.')
    } finally {
      setBusy(false)
    }
  }

  async function changeStatus(status) {
    try {
      await client.patch(`/tenders/${tenderId}/status`, { status })
      await load()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not update tender status.')
    }
  }

  if (!tender) return null

  return (
    <div>
      <div className="topline">
        <h1>{tender.title}</h1>
        <span className="ref">{tender.reference_no}</span>
      </div>
      <div className="subhead">{tender.department}{tender.theme ? ` · ${tender.theme}` : ''}</div>

      <div className="panel tender-overview">
        <div>
          <div className="report-label">Tender status</div>
          <div className="tender-status">{tender.status}</div>
          {tender.description && <div className="doc-note">{tender.description}</div>}
          {tender.submission_deadline && <div className="doc-file">Deadline: {new Date(tender.submission_deadline).toLocaleString()}</div>}
        </div>
        <div className="status-actions">
          {(nextStatuses[tender.status] || []).map((status) => (
            <button key={status} className="btn btn-secondary" onClick={() => changeStatus(status)}>{status}</button>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-title"><span>Required documents ({tender.requirements.length})</span></div>
        <table>
          <thead>
            <tr><th>Document</th><th>Match keywords</th><th>Priority</th><th>Mandatory</th></tr>
          </thead>
          <tbody>
            {tender.requirements.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td style={{ color: 'var(--ink-soft)', fontSize: 13 }}>{r.keywords}</td>
                <td>{r.critical ? 'Critical' : `Weight ${r.weight}`}</td>
                <td>{r.mandatory ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <div className="panel-title">
          <span>Bids received ({bids.length})</span>
          <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
            {showForm ? 'Cancel' : '+ Register bid'}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleAddBid} style={{ marginBottom: 20, paddingBottom: 18, borderBottom: '1px solid var(--line)' }}>
            <div className="field">
              <label>Bidder name</label>
              <input value={bidderName} onChange={(e) => setBidderName(e.target.value)} required />
            </div>
            <div className="field">
              <label>Company (optional)</label>
              <input value={bidderCompany} onChange={(e) => setBidderCompany(e.target.value)} />
            </div>
            {error && <div className="login-error" style={{ marginBottom: 10 }}>{error}</div>}
            <button className="btn btn-primary" disabled={busy}>{busy ? 'Registering…' : 'Register bid'}</button>
          </form>
        )}

        {bids.length === 0 ? (
          <div className="empty-state">No bids registered yet for this tender.</div>
        ) : (
          <table>
            <thead>
              <tr><th>Bidder</th><th>Documents uploaded</th><th>Compliance score</th><th>Risk</th></tr>
            </thead>
            <tbody>
              {bids.map((b) => (
                <tr key={b.id} className="clickable" onClick={() => navigate(`/tenders/${tenderId}/bids/${b.id}`)}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{b.bidder_name}</div>
                    {b.bidder_company && <div style={{ fontSize: 12.5, color: 'var(--ink-soft)' }}>{b.bidder_company}</div>}
                  </td>
                  <td>{b.documents.length}</td>
                  <td>{b.compliance_score != null ? `${b.compliance_score}%` : '—'}</td>
                  <td><RiskBadge risk={b.risk_level} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
