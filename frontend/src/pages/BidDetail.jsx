import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import client from '../api/client'
import RiskBadge, { riskClass, StatusBadge } from '../components/RiskBadge'

export default function BidDetail() {
  const { tenderId, bidId } = useParams()
  const [report, setReport] = useState(null)
  const [auditLog, setAuditLog] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState('')
  const [reviewComments, setReviewComments] = useState({})
  const [loadError, setLoadError] = useState('')
  const fileInput = useRef(null)

  async function load() {
    try {
      setLoadError('')
      const [r, a] = await Promise.all([
        client.get(`/tenders/${tenderId}/bids/${bidId}/compliance`),
        client.get(`/tenders/${tenderId}/bids/${bidId}/audit-log`),
      ])
      setReport(r.data)
      setAuditLog(a.data)
    } catch (err) {
      setLoadError(err?.response?.data?.detail || 'This bid could not be loaded.')
    }
  }

  useEffect(() => { load() }, [tenderId, bidId])

  async function handleFiles(files) {
    if (!files || files.length === 0) return
    setUploading(true)
    setUploadError('')
    try {
      for (const file of files) {
        const form = new FormData()
        form.append('file', file)
        await client.post(`/tenders/${tenderId}/bids/${bidId}/documents`, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (event) => {
            if (event.total) setUploadProgress(Math.round((event.loaded / event.total) * 100))
          },
        })
      }
      await load()
    } catch (err) {
      setUploadError(err?.response?.data?.detail || 'Upload failed.')
    } finally {
      setUploading(false)
      setUploadProgress(0)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  async function handleDelete(docId) {
    await client.delete(`/tenders/${tenderId}/bids/${bidId}/documents/${docId}`)
    await load()
  }

  async function reviewDocument(docId, decision) {
    await client.patch(`/tenders/${tenderId}/bids/${bidId}/documents/${docId}/review`, {
      decision,
      comment: reviewComments[docId] || null,
    })
    await load()
  }

  async function assignDocument(docId) {
    const reviewerId = window.prompt('Reviewer user ID')
    if (!reviewerId) return
    const dueAt = window.prompt('Due date/time (optional, ISO format)')
    await client.patch(`/tenders/${tenderId}/bids/${bidId}/documents/${docId}/assignment`, {
      reviewer_id: Number(reviewerId),
      due_at: dueAt || null,
    })
    await load()
  }

  async function exportCsv() {
    const response = await client.get(`/tenders/${tenderId}/bids/${bidId}/export.csv`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `bid-${bidId}-compliance.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  async function exportPdf() {
    const response = await client.get(`/tenders/${tenderId}/bids/${bidId}/export.pdf`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `bid-${bidId}-compliance-certificate.pdf`
    anchor.click()
    URL.revokeObjectURL(url)
  }


  async function changeBidStatus(status) {
    await client.patch(`/tenders/${tenderId}/bids/${bidId}/status`, { status })
    await load()
  }

  const nextStatuses = {
    Draft: ['Submitted', 'Withdrawn'],
    Submitted: ['Under review', 'Withdrawn'],
    'Under review': ['Accepted', 'Rejected', 'Withdrawn'],
    Accepted: [],
    Rejected: [],
    Withdrawn: ['Draft'],
  }

  if (!report && loadError) {
    return <div className="page-state error-state"><h1>Bid unavailable</h1><p>{loadError}</p><button className="btn btn-secondary" onClick={load}>Retry</button></div>
  }
  if (!report) return <div className="page-state"><div className="loading-mark">Loading bid workspace...</div></div>

  return (
    <div>
      <div className="topline">
        <h1>{report.bidder_name}</h1>
      </div>
      <div className="subhead">Bid against {report.tender_title}</div>

      <div className="panel bid-status-panel">
        <div>
          <div className="report-label">Submission status</div>
          <div className="tender-status">{report.submission_status}</div>
          <div className="doc-file">Submitted versions: {report.submitted_version}</div>
        </div>
        <div className="status-actions">
          {(nextStatuses[report.submission_status] || []).map((status) => (
            <button key={status} className="btn btn-secondary" onClick={() => changeBidStatus(status)}>{status}</button>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="advisory-note"><strong>Advisory compliance result</strong><span>Automated evidence supports review; it does not replace the procurement decision.</span></div>
        <div className="score-row">
          <div className="score-figure">
            <div className={`score-number ${riskClass(report.risk_level)}`}>{report.compliance_score}%</div>
            <div className="score-label">Compliance score</div>
          </div>
          <div>
            <RiskBadge risk={report.risk_level} />
            <div className="doc-note">Risk is derived from missing, mismatched, and critical requirements.</div>
          </div>
          <div className="stat-strip" style={{ marginLeft: 'auto' }}>
            <div className="stat">
              <div className="n">{report.matched.length}</div>
              <div className="l">Matched</div>
            </div>
            <div className="stat">
              <div className="n">{report.mismatched.length}</div>
              <div className="l">Flagged</div>
            </div>
            <div className="stat">
              <div className="n">{report.missing.length}</div>
              <div className="l">Missing</div>
            </div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title"><span>Upload bid documents</span></div>
        <div
          className="dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); handleFiles(e.dataTransfer.files) }}
        >
          {uploading ? `Uploading ${uploadProgress}%…` : 'Drag & drop a PDF, image, or text file here, or'}{' '}
          {!uploading && report.submission_status === 'Draft' && (
            <button className="link-btn" onClick={() => fileInput.current?.click()}>browse files</button>
          )}
          <input
            ref={fileInput}
            type="file"
            style={{ display: 'none' }}
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>
        {report.submission_status !== 'Draft' && <div className="doc-note">Documents are locked after submission. Withdraw the bid to manage it through a new version.</div>}
        {uploadError && <div className="login-error" style={{ marginTop: 10 }}>{uploadError}</div>}
      </div>

      <div className="panel">
        <div className="panel-title"><span>Requirement checklist</span></div>
        {report.missing.length === 0 && report.mismatched.length === 0 && report.matched.length === 0 && (
          <div className="empty-state">This tender has no defined requirements.</div>
        )}
        {[...report.matched.map((n) => ({ n, s: 'Matched' })),
          ...report.mismatched.map((n) => ({ n, s: 'Mismatched' })),
          ...report.missing.map((n) => ({ n, s: 'Missing' }))].map((row, i) => (
          <div className="doc-list-item" key={i}>
            <div className="doc-name">{row.n}</div>
            <StatusBadge status={row.s} />
          </div>
        ))}
      </div>

      <div className="panel">
        <div className="panel-title">
          <span>Uploaded documents</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-secondary btn-small" onClick={exportCsv}>Export CSV</button>
            <button className="btn btn-primary btn-small" onClick={exportPdf}>Download PDF Certificate</button>
          </div>
        </div>
        {report.details.length === 0 ? (
          <div className="empty-state">No documents uploaded yet.</div>
        ) : (
          report.details.map((d) => (
            <div className="doc-list-item" key={d.id}>
              <div>
                <div className="doc-name">{d.original_filename}</div>
                {d.notes && <div className="doc-note">{d.notes}</div>}
                {d.review_comment && <div className="doc-note">Review: {d.review_comment}</div>}
                {d.matched_keywords && <div className="doc-file">Evidence: {d.matched_keywords}</div>}
                <div className="doc-file">Extraction: {d.extraction_method || 'unknown'} · quality {Math.round((d.text_quality || 0) * 100)}%</div>
                {d.expiry_date && <div className="doc-file">Expiry: {new Date(d.expiry_date).toLocaleDateString()}</div>}
                <div className="doc-file">confidence {Math.round(d.match_confidence * 100)}%</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                <StatusBadge status={d.status} />
                <div className="review-status">Review: {d.review_status}</div>
                {d.assigned_reviewer_id && <div className="review-status">Assigned reviewer: {d.assigned_reviewer_id}</div>}
                <input
                  className="review-input"
                  value={reviewComments[d.id] || ''}
                  onChange={(e) => setReviewComments((comments) => ({ ...comments, [d.id]: e.target.value }))}
                  placeholder="Reviewer comment"
                  maxLength={1000}
                />
                <div className="review-actions">
                  <button className="link-btn" onClick={() => assignDocument(d.id)}>Assign</button>
                  <button className="link-btn" onClick={() => reviewDocument(d.id, 'approved')}>Approve</button>
                  <button className="link-btn review-reject" onClick={() => reviewDocument(d.id, 'rejected')}>Reject</button>
                </div>
                <button className="link-btn" onClick={() => handleDelete(d.id)}>Remove</button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="panel">
        <div className="panel-title"><span>Audit log</span></div>
        {auditLog.length === 0 ? (
          <div className="empty-state">No activity recorded yet.</div>
        ) : (
          auditLog.map((a) => (
            <div className="doc-list-item" key={a.id}>
              <div>
                <div className="doc-name">{a.action.replaceAll('_', ' ')}</div>
                <div className="doc-note">{a.details}</div>
              </div>
              <div className="doc-file">{new Date(a.timestamp).toLocaleString()}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
