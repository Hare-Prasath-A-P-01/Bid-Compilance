import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

export default function Notifications() {
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      setLoading(true)
      setError('')
      const response = await client.get('/notifications')
      setNotifications(response.data)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not load notifications.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function markRead(notification) {
    if (!notification.read_at) {
      await client.patch(`/notifications/${notification.id}/read`)
      await load()
    }
    if (notification.link) navigate(notification.link)
  }

  async function markAllRead() {
    await client.patch('/notifications/read-all')
    await load()
  }

  const unreadCount = notifications.filter((notification) => !notification.read_at).length

  return (
    <div>
      <div className="topline">
        <h1>Notifications</h1>
        {unreadCount > 0 && <button className="btn btn-secondary" onClick={markAllRead}>Mark all read</button>}
      </div>
      <div className="subhead">Assignments, review updates, and bid workflow alerts.</div>
      <div className="panel">
        {error && <div className="inline-alert">{error} <button className="link-btn" onClick={load}>Retry</button></div>}
        {loading ? <div className="empty-state">Loading notifications...</div> : !error && notifications.length === 0 ? (
          <div className="empty-state">No notifications yet.</div>
        ) : (
          notifications.map((notification) => (
            <button
              className={`notification-item${notification.read_at ? '' : ' unread'}`}
              key={notification.id}
              onClick={() => markRead(notification)}
            >
              <div>
                <div className="notification-title">{notification.title}</div>
                <div className="doc-note">{notification.message}</div>
              </div>
              <div className="doc-file">{new Date(notification.created_at).toLocaleString()}</div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
