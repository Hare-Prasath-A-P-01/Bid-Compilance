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

      {/* ========================================================================= */}
      {/* FINAL VERIFICATION RESULT SECTION (SIH PRESENTATION READY) */}
      {/* ========================================================================= */}
      <section className="verification-result-section" id="final-verification-result">
        <div className="verification-header">
          <div>
            <span className="verification-badge-tag">SIH 2026 Automated Audit Platform</span>
            <h2 className="verification-title">Final Verification Result</h2>
            <div className="verification-subtitle">
              Comprehensive evidence-backed compliance audit for tender evaluation against statutory requirements
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <button className="btn btn-secondary btn-small" onClick={exportCsv}>Export CSV</button>
            <button className="btn btn-primary" onClick={exportPdf}>
              📄 Download Report (PDF)
            </button>
          </div>
        </div>

        {/* 9-Stage User Flow Stepper */}
        <div className="workflow-stepper">
          <div className="workflow-stepper-title">Verification Workflow Pipeline</div>
          <div className="stepper-track">
            <span className="step-node active">1. Upload Bid Document</span>
            <span className="step-arrow">→</span>
            <span className="step-node active">2. Extract Information</span>
            <span className="step-arrow">→</span>
            <span className="step-node active">3. Identify Requirements</span>
            <span className="step-arrow">→</span>
            <span className="step-node active">4. Apply Compliance Rules</span>
            <span className="step-arrow">→</span>
            <span className="step-node active">5. Cross-check Information</span>
            <span className="step-arrow">→</span>
            <span className="step-node active">6. Detect Missing / Mismatch</span>
            <span className="step-arrow">→</span>
            <span className="step-node active">7. Generate Score & Risk</span>
            <span className="step-arrow">→</span>
            <span className="step-node active">8. Show Evidence & Reason</span>
            <span className="step-arrow">→</span>
            <span className="step-node decision">9. Procurement Officer Review</span>
          </div>
        </div>

        {/* 4. COMPLIANCE SUMMARY */}
        <div className="summary-kpis-grid">
          <div className="kpi-card score-card">
            <div className="kpi-label">Overall Compliance</div>
            <div className={`kpi-val ${riskClass(report.risk_level)}`}>
              {report.compliance_score ?? 0}%
            </div>
            <div style={{ marginTop: 6 }}>
              <RiskBadge risk={report.risk_level} />
            </div>
            <div className="kpi-sub">Defensible multi-rule evaluation</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Total Checks</div>
            <div className="kpi-val">
              {report.summary_stats?.total_checks ?? (report.matched.length + report.mismatched.length + report.missing.length)}
            </div>
            <div className="kpi-sub">Statutory tender requirements</div>
          </div>

          <div className="kpi-card pass-card">
            <div className="kpi-label">Passed (Compliant)</div>
            <div className="kpi-val pass">
              {report.summary_stats?.passed ?? report.matched.length}
            </div>
            <div className="kpi-sub">Verified & valid documents</div>
          </div>

          <div className="kpi-card missing-card">
            <div className="kpi-label">Missing</div>
            <div className="kpi-val missing">
              {report.summary_stats?.missing ?? report.missing.length}
            </div>
            <div className="kpi-sub">Required files not uploaded</div>
          </div>

          <div className="kpi-card flagged-card">
            <div className="kpi-label">Mismatch / Needs Review</div>
            <div className="kpi-val flagged">
              {report.summary_stats?.mismatched_needs_review ?? report.mismatched.length}
            </div>
            <div className="kpi-sub">Expired, blank or flagged</div>
          </div>
        </div>

        {/* 1. DOCUMENT DETAILS & 2. EXTRACTED INFORMATION */}
        <div style={{ marginTop: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, margin: 0 }}>Document Details & Extracted Information</h3>
            <span style={{ fontSize: 12, color: 'var(--ink-soft)' }}>
              Processed: {report.details.length} document{report.details.length === 1 ? '' : 's'}
            </span>
          </div>

          {report.details.length === 0 ? (
            <div className="empty-state" style={{ padding: 20, marginBottom: 16 }}>
              No bid documents processed yet. Upload documents below to view extracted fields and verification results.
            </div>
          ) : (
            report.details.map((doc) => (
              <div className="doc-detail-card" key={doc.id}>
                <div className="doc-detail-header">
                  <div className="doc-detail-title">
                    <span>📄 {doc.original_filename}</span>
                    <span className="doc-type-pill">Type: {doc.document_type || 'General Bid Document'}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className={`status-chip ${doc.status === 'Matched' ? 'compliant' : 'mismatch'}`}>
                      {doc.status === 'Matched' ? '✓ Processed & Verified' : '⚠ Flagged / Needs Review'}
                    </span>
                    <span className="doc-file" style={{ fontSize: 11 }}>
                      Method: {doc.extraction_method || 'Text layer'} · Quality: {Math.round((doc.text_quality || 0) * 100)}%
                    </span>
                  </div>
                </div>

                {/* Structured Extracted Information */}
                <div>
                  <div className="workflow-stepper-title" style={{ marginBottom: 6 }}>
                    Extracted Information Fields
                  </div>
                  {doc.extracted_fields && Object.keys(doc.extracted_fields).length > 0 ? (
                    <div className="extracted-fields-grid">
                      {Object.entries(doc.extracted_fields).map(([k, v]) => (
                        <div className="field-tile" key={k}>
                          <div className="field-key">{k}</div>
                          <div className="field-val">{v}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="doc-note">
                      {doc.matched_keywords ? `Matched keywords: ${doc.matched_keywords}` : 'Text extracted cleanly without custom fields.'}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* 3. COMPLIANCE VERIFICATION TABLE */}
        <div style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 16, margin: '0 0 4px 0' }}>Statutory Compliance Verification Matrix</h3>
          <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginBottom: 10 }}>
            Requirement-by-requirement verification status with defensible evidence and extracted values
          </div>

          <div className="verification-table-wrap">
            <table className="verification-table">
              <thead>
                <tr>
                  <th style={{ width: '22%' }}>Requirement</th>
                  <th style={{ width: '25%' }}>Extracted Value</th>
                  <th style={{ width: '18%' }}>Verification Status</th>
                  <th style={{ width: '35%' }}>Evidence / Reason</th>
                </tr>
              </thead>
              <tbody>
                {(report.verification_checklist && report.verification_checklist.length > 0) ? (
                  report.verification_checklist.map((item) => {
                    const statusClass = item.status === 'Compliant' ? 'compliant'
                      : item.status === 'Missing' ? 'missing'
                      : item.status === 'Mismatch' ? 'mismatch'
                      : 'review'

                    return (
                      <tr key={item.requirement_id}>
                        <td>
                          <div className="req-name-box">
                            <span className="req-name-text">{item.requirement_name}</span>
                            {item.mandatory && <span className="req-mandatory-tag">Mandatory</span>}
                          </div>
                        </td>
                        <td>
                          <div style={{ fontSize: 12.5, fontWeight: 500, color: '#0f172a' }}>
                            {item.extracted_value || 'Not Submitted'}
                          </div>
                          {item.matched_document && (
                            <div className="doc-file" style={{ marginTop: 2, fontSize: 11 }}>
                              Source: {item.matched_document}
                            </div>
                          )}
                        </td>
                        <td>
                          <span className={`status-chip ${statusClass}`}>
                            {item.status_label || item.status}
                          </span>
                        </td>
                        <td>
                          <div className="reason-box">
                            <span className={item.status !== 'Compliant' ? 'reason-flag-text' : ''}>
                              {item.reason}
                            </span>
                            {item.evidence && item.evidence !== '—' && (
                              <div className="doc-file" style={{ marginTop: 3, fontSize: 11 }}>
                                Keywords detected: {item.evidence}
                              </div>
                            )}
                            <div className="portal-status-note">
                              Verification Check: {item.portal_verification || 'API integration ready (Demo mode)'}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                ) : (
                  [...report.matched.map((n) => ({ n, s: 'Compliant', l: '✓ Compliant', r: 'Statutory keywords matched and valid format confirmed.' })),
                   ...report.mismatched.map((n) => ({ n, s: 'Mismatch', l: '✕ Mismatch', r: 'Document flagged during automated inspection.' })),
                   ...report.missing.map((n) => ({ n, s: 'Missing', l: '✕ Missing', r: 'Required document not submitted by bidder.' }))
                  ].map((row, idx) => (
                    <tr key={idx}>
                      <td><div className="req-name-text">{row.n}</div></td>
                      <td>—</td>
                      <td>
                        <span className={`status-chip ${row.s.toLowerCase()}`}>{row.l}</span>
                      </td>
                      <td><div className="reason-box">{row.r}</div></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* 5. EVIDENCE-BASED RESULT (WHY FLAGGED) */}
        {(() => {
          const flagged = (report.verification_checklist || []).filter(
            (item) => item.status === 'Mismatch' || item.status === 'Missing' || item.status === 'Needs Review'
          )
          if (flagged.length === 0) return null
          return (
            <div className="flagged-findings-box">
              <div className="flagged-findings-title">
                <span>⚠️ Evidence-Based Flagged Findings ({flagged.length} item{flagged.length === 1 ? '' : 's'} require review)</span>
              </div>
              <ul className="flagged-list">
                {flagged.map((item) => (
                  <li key={item.requirement_id}>
                    <strong>{item.requirement_name} ({item.status}):</strong> {item.reason}
                  </li>
                ))}
              </ul>
            </div>
          )
        })()}

        {/* 6. FINAL REVIEW MESSAGE */}
        <div className="review-mandate-banner">
          <div className="mandate-icon">⚖️</div>
          <div>
            <div className="mandate-text-title">
              "AI-generated verification result. Final qualification/disqualification decision remains with the Procurement Officer."
            </div>
            <div className="mandate-text-desc">
              In accordance with Public Procurement Rules (GFR 2017), this automated evaluation serves as objective decision support. The final determination and award concurrence must be completed by the authorized Procurement Officer.
            </div>
          </div>
        </div>
      </section>

      {/* ---------- Document Upload Section ---------- */}
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

      {/* ---------- Uploaded Documents & Review Operations ---------- */}
      <div className="panel">
        <div className="panel-title">
          <span>Uploaded documents & Reviewer Decisions</span>
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
