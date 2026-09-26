import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

export default function ReviewQueue() {
  const navigate = useNavigate()
  const [queue, setQueue] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      setLoading(true)
      setError('')
      const response = await client.get('/reviews/queue')
      setQueue(response.data)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not load the review queue.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div>
      <div className="topline"><h1>Review queue</h1></div>
      <div className="subhead">Pending documents assigned to your review scope, including overdue work.</div>
      <div className="panel">
        <div className="panel-title"><span>{queue.length} pending document{queue.length === 1 ? '' : 's'}</span></div>
        {error && <div className="inline-alert">{error} <button className="link-btn" onClick={load}>Retry</button></div>}
        {loading ? <div className="empty-state">Loading review queue...</div> : !error && queue.length === 0 ? (
          <div className="empty-state">No pending documents in the queue.</div>
        ) : (
          <table>
            <thead><tr><th>Document</th><th>Bidder</th><th>Tender</th><th>Due</th><th>Status</th></tr></thead>
            <tbody>
              {queue.map((item) => (
                <tr key={item.document_id} className="clickable" onClick={() => navigate(`/tenders/${item.tender_id}/bids/${item.bid_id}`)}>
                  <td>{item.filename}</td>
                  <td>{item.bidder_name}</td>
                  <td>{item.tender_title}</td>
                  <td>{item.due_at ? new Date(item.due_at).toLocaleString() : 'No due date'}</td>
                  <td className={item.overdue ? 'queue-overdue' : ''}>{item.overdue ? 'Overdue' : 'Pending'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}