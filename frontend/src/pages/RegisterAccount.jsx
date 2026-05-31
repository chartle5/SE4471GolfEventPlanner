import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Icon from '../components/Icon'

export default function Register() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', username: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (form.password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: form.email,
          username: form.username,
          password: form.password,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || 'Registration failed.')
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
      <div className="auth-card" style={{ maxWidth: 440 }}>
        <div className="auth-brand">
          <div className="auth-mark">
            <Icon name="flag" size={26} strokeWidth={1.9} />
          </div>
          <div className="eyebrow" style={{ marginBottom: 4 }}>Organizer Suite</div>
          <div className="auth-title">Golf Event Planner</div>
          <div className="auth-sub">Create a new account</div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="field">
            <label className="field-label">Email</label>
            <input type="email" value={form.email} onChange={set('email')} placeholder="you@example.com" required autoFocus />
          </div>

          <div className="field">
            <label className="field-label">Username</label>
            <input type="text" value={form.username} onChange={set('username')} placeholder="your_username" required />
          </div>

          <div className="field">
            <label className="field-label">Password</label>
            <input type="password" value={form.password} onChange={set('password')} placeholder="••••••••" required />
          </div>

          <div className="field">
            <label className="field-label">Confirm Password</label>
            <input type="password" value={form.confirm} onChange={set('confirm')} placeholder="••••••••" required />
          </div>

          {error && <div className="notice notice-danger">{error}</div>}

          <button type="submit" disabled={loading} className="btn btn-gold btn-block" style={{ marginTop: 2 }}>
            {loading ? <><span className="spinner" /> Creating account…</> : 'Create Account'}
          </button>
        </form>

        <div className="auth-foot">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  )
}
