import { useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import client from '../api/client'

const STARTER_REQUIREMENTS = [
  { name: 'GST Registration Certificate', keywords: 'gst, goods and services tax, gstin', aliases: 'tax registration', mandatory: true, critical: true, weight: 2 },
  { name: 'PAN Card', keywords: 'pan, permanent account number', aliases: 'tax identity', mandatory: true, critical: false, weight: 1 },
  { name: 'Technical Bid Document', keywords: 'technical bid, technical proposal, specifications', aliases: 'technical offer', mandatory: true, critical: true, weight: 2 },
  { name: 'Financial Bid Document', keywords: 'financial bid, price bid, quotation, boq', aliases: 'commercial offer', mandatory: true, critical: true, weight: 2 },
]

export default function NewTender() {
  const navigate = useNavigate()
  const { refreshTenders } = useOutletContext()
  const [referenceNo, setReferenceNo] = useState('')
  const [title, setTitle] = useState('')
  const [department, setDepartment] = useState('')
  const [theme, setTheme] = useState('')
  const [description, setDescription] = useState('')
  const [submissionDeadline, setSubmissionDeadline] = useState('')
  const [tenderBrief, setTenderBrief] = useState('')
  const [requirements, setRequirements] = useState(STARTER_REQUIREMENTS)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [aiBusy, setAiBusy] = useState(false)

  function updateReq(i, field, value) {
    setRequirements((rs) => rs.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))
  }

  function addReq() {
    setRequirements((rs) => [...rs, { name: '', keywords: '', aliases: '', mandatory: true, critical: false, weight: 1 }])
  }

  function removeReq(i) {
    setRequirements((rs) => rs.filter((_, idx) => idx !== i))
  }

  async function suggestRequirements() {
    if (!tenderBrief.trim()) return
    setAiBusy(true)
    setError('')
    try {
      const { data } = await client.post('/ai/suggest-requirements', { tender_text: tenderBrief })
      setRequirements((current) => {
        const existing = new Set(current.map((item) => item.name.toLowerCase()))
        return [...current, ...data.filter((item) => !existing.has(item.name.toLowerCase()))]
      })
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not generate suggestions.')
    } finally {
      setAiBusy(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const clean = requirements.filter((r) => r.name.trim() && r.keywords.trim())
    if (clean.length === 0) {
      setError('Add at least one required document with matching keywords.')
      return
    }
    setBusy(true)
    try {
      const { data } = await client.post('/tenders', {
        reference_no: referenceNo,
        title,
        department,
        theme,
        description,
        submission_deadline: submissionDeadline ? new Date(submissionDeadline).toISOString() : null,
        requirements: clean,
      })
      await refreshTenders()
      navigate(`/tenders/${data.id}`)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not create tender.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="topline"><h1>New tender</h1></div>
      <div className="subhead">
        Define the tender and the document checklist bids will be checked against. Keywords drive
        automatic matching — list the words most likely to appear in a genuine copy of that document.
      </div>

      <form onSubmit={handleSubmit}>
        <div className="panel">
          <div className="panel-title"><span>Tender details</span></div>
          <div className="field">
            <label>Reference number</label>
            <input value={referenceNo} onChange={(e) => setReferenceNo(e.target.value)} placeholder="e.g. TN/2026/IT-0042" required />
          </div>
          <div className="field">
            <label>Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Supply of networking equipment" required />
          </div>
          <div className="field">
            <label>Department</label>
            <input value={department} onChange={(e) => setDepartment(e.target.value)} placeholder="e.g. Public Works Department" />
          </div>
          <div className="field">
            <label>Theme / category</label>
            <input value={theme} onChange={(e) => setTheme(e.target.value)} placeholder="e.g. Infrastructure" />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows="3" placeholder="Scope and evaluation context" />
          </div>
          <div className="field">
            <label>Submission deadline</label>
            <input type="datetime-local" value={submissionDeadline} onChange={(e) => setSubmissionDeadline(e.target.value)} />
          </div>
        </div>

        <div className="panel">
          <div className="panel-title"><span>Required documents</span></div>
          <div className="ai-assist-box">
            <label>AI checklist assistant</label>
            <textarea value={tenderBrief} onChange={(e) => setTenderBrief(e.target.value)} rows="3" placeholder="Paste a tender brief to suggest document requirements" />
            <button type="button" className="btn btn-secondary" onClick={suggestRequirements} disabled={aiBusy || !tenderBrief.trim()}>
              {aiBusy ? 'Suggesting…' : 'Suggest requirements'}
            </button>
            <div className="doc-note">Suggestions are advisory. Review and edit them before creating the tender.</div>
          </div>
          <div className="req-row" style={{ marginBottom: 10 }}>
            <div className="nav-section-label" style={{ color: 'var(--ink-soft)' }}>Document name</div>
            <div className="nav-section-label" style={{ color: 'var(--ink-soft)' }}>Match keywords (comma-separated)</div>
            <div className="nav-section-label" style={{ color: 'var(--ink-soft)' }}>Aliases / synonyms</div>
            <div className="nav-section-label" style={{ color: 'var(--ink-soft)' }}>Mandatory</div>
            <div className="nav-section-label" style={{ color: 'var(--ink-soft)' }}>Critical</div>
            <div className="nav-section-label" style={{ color: 'var(--ink-soft)' }}>Weight</div>
            <div />
          </div>
          {requirements.map((r, i) => (
            <div className="req-row" key={i}>
              <input value={r.name} onChange={(e) => updateReq(i, 'name', e.target.value)} placeholder="Document name" />
              <input value={r.keywords} onChange={(e) => updateReq(i, 'keywords', e.target.value)} placeholder="keyword, keyword, keyword" />
              <input value={r.aliases || ''} onChange={(e) => updateReq(i, 'aliases', e.target.value)} placeholder="synonym, alternate phrase" />
              <select value={r.mandatory ? 'yes' : 'no'} onChange={(e) => updateReq(i, 'mandatory', e.target.value === 'yes')}>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
              <select value={r.critical ? 'yes' : 'no'} onChange={(e) => updateReq(i, 'critical', e.target.value === 'yes')}>
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
              <input type="number" min="0.1" max="10" step="0.1" value={r.weight} onChange={(e) => updateReq(i, 'weight', Number(e.target.value))} />
              <button type="button" className="link-btn" onClick={() => removeReq(i)}>Remove</button>
            </div>
          ))}
          <button type="button" className="btn btn-secondary" onClick={addReq} style={{ marginTop: 8 }}>
            + Add document requirement
          </button>
        </div>

        {error && <div className="login-error" style={{ marginBottom: 14 }}>{error}</div>}

        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Creating…' : 'Create tender'}
        </button>
      </form>
    </div>
  )
}
