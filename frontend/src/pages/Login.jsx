import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Icon from '../components/Icon'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || 'Login failed.')
        return
      }
      login(data.token, { user_id: data.user_id, username: data.username, email: data.email })
      navigate('/')
    } catch {
      setError('Could not reach the server. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-mark">
            <Icon name="flag" size={26} strokeWidth={1.9} />
          </div>
          <div className="eyebrow" style={{ marginBottom: 4 }}>Organizer Suite</div>
          <div className="auth-title">Golf Event Planner</div>
          <div className="auth-sub">Sign in to your account</div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="field">
            <label className="field-label">Username or Email</label>
            <input
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="username or email@example.com"
              required
              autoFocus
            />
          </div>

          <div className="field">
            <label className="field-label">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {error && <div className="notice notice-danger">{error}</div>}

          <button type="submit" disabled={loading} className="btn btn-gold btn-block" style={{ marginTop: 2 }}>
            {loading ? <><span className="spinner" /> Signing in…</> : 'Sign In'}
          </button>
        </form>

        <div className="auth-foot">
          Don't have an account? <Link to="/register">Create one</Link>
        </div>
      </div>
    </div>
  )
}
