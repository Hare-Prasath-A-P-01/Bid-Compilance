import { useEffect, useState } from 'react'
import { Outlet, Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Shell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { tenderId } = useParams()
  const [tenders, setTenders] = useState([])
  const [unreadNotifications, setUnreadNotifications] = useState(0)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    Promise.all([client.get('/tenders'), client.get('/notifications')])
      .then(([tenderResponse, notificationResponse]) => {
        setTenders(tenderResponse.data)
        setUnreadNotifications(notificationResponse.data.filter((item) => !item.read_at).length)
      })
      .catch(() => {})
  }, [])

  const pageLabel = location.pathname === '/'
    ? 'Overview'
    : location.pathname.includes('/reviews')
      ? 'Review queue'
      : location.pathname.includes('/notifications')
        ? 'Notifications'
        : location.pathname.includes('/admin')
          ? 'Administration'
          : 'Tender workspace'

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <button className="mobile-menu-button" onClick={() => setMobileOpen((open) => !open)} aria-label="Open navigation">
        {mobileOpen ? 'Close' : 'Menu'}
      </button>
      <aside className={`sidebar${mobileOpen ? ' mobile-open' : ''}`}>
        <div className="brand">
          <div className="mark">BB</div>
          <div className="name">Bid Compliance<br />Checker</div>
          <div className="sub">Byte Busters — SIH 2026</div>
        </div>

        <nav className="sidebar-nav" onClick={() => setMobileOpen(false)}>
          <div className="nav-section-label">Active tenders</div>
          {tenders.map((t) => (
            <button
              key={t.id}
              className={'tender-nav-item' + (String(t.id) === tenderId ? ' active' : '')}
              onClick={() => navigate(`/tenders/${t.id}`)}
            >
              {t.title}
            </button>
          ))}
          {tenders.length === 0 && (
            <div style={{ fontSize: 12.5, color: '#8b96b5' }}>No tenders yet.</div>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="who">{user?.full_name}</div>
          <div>{user?.role?.replaceAll('_', ' ')}{user?.department ? ` · ${user.department}` : ''}</div>
          <div className="sidebar-email">{user?.email}</div>
          <button className="logout-link" onClick={handleLogout}>Sign out</button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="breadcrumb">Byte Busters <span>/</span> {pageLabel}</div>
            <div className="topbar-context">AI Bid Compliance Checker</div>
          </div>
          <nav className="top-nav" onClick={() => setMobileOpen(false)} aria-label="Primary navigation">
            <Link to="/" className={location.pathname === '/' ? 'active' : ''}>Overview</Link>
            {(user?.role === 'admin' || user?.role === 'reviewer') && (
              <Link to="/reviews/queue" className={location.pathname.includes('/reviews') ? 'active' : ''}>Reviews</Link>
            )}
            <Link to="/notifications" className={location.pathname.includes('/notifications') ? 'active' : ''}>
              Alerts {unreadNotifications > 0 && <span className="nav-count">{unreadNotifications}</span>}
            </Link>
            <Link to="/tenders/new" className="top-nav-primary">Create tender</Link>
            {user?.role === 'admin' && <Link to="/admin/users" className={location.pathname.includes('/admin') ? 'active' : ''}>Admin</Link>}
          </nav>
          <div className="topbar-actions">
            <div className="topbar-profile">
              <span className="profile-avatar">{user?.full_name?.slice(0, 1).toUpperCase()}</span>
              <span className="profile-copy"><strong>{user?.full_name}</strong><small>{user?.role?.replaceAll('_', ' ')}</small></span>
            </div>
            <button className="topbar-user" onClick={() => navigate('/notifications')} aria-label="Open notifications">
              <span className="alert-dot" />
              {unreadNotifications > 0 ? `${unreadNotifications} alerts` : 'No new alerts'}
            </button>
          </div>
        </header>
        <Outlet context={{ tenders, refreshTenders: () => client.get('/tenders').then((r) => setTenders(r.data)) }} />
        <footer className="app-footer">
          <div className="footer-brand">
            <strong>Byte Busters</strong>
            <span>AI Bid Compliance Checker</span>
            <small>© 2026 Byte Busters. All rights reserved.</small>
          </div>
          <div className="footer-meta">
            <span>Evidence-led procurement workspace</span>
            <span>Authorized access only</span>
            <span>System online</span>
          </div>
        </footer>
      </main>
    </div>
  )
}
