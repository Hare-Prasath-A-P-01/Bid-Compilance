import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err?.response?.status === 429
        ? 'Too many unsuccessful attempts. Please wait and try again.'
        : 'Sign-in could not be completed. Check your credentials and try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-screen">
      <div className="login-intro">
        <div className="login-intro-mark">BB</div>
        <div className="login-eyebrow">Byte Busters</div>
        <h1>Intelligent compliance.<br />Explainable decisions.</h1>
        <p>Review procurement submissions, trace evidence, and move decisions through a defensible workflow.</p>
        <div className="login-flow">Evidence <span>→</span> Intelligence <span>→</span> Review <span>→</span> Audit</div>
      </div>
      <div className="login-card">
        <div className="login-mark">BB</div>
        <h2>AI Bid Compliance Checker</h2>
        <div className="subhead" style={{ marginBottom: 20 }}>
          Procurement officer sign-in
        </div>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
          </div>
          <div className="field">
            <label>Password</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
          </div>
          {error && <div className="login-error">{error}</div>}
          <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <div className="hint">Use your organization account to access assigned tenders and reviews.</div>
      </div>
      <footer className="login-footer">Byte Busters <span>·</span> AI Bid Compliance Checker <span>·</span> Secure workspace</footer>
    </div>
  )
}
