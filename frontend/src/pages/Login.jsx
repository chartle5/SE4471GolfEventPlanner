import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

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
      const res = await fetch('http://localhost:8000/auth/login', {
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
    <div style={pageStyle}>
      <div style={cardStyle}>
        {/* Header */}
        <div style={headerStyle}>
          <div style={{ fontSize: 28, marginBottom: 4 }}>⛳</div>
          <div style={{ fontWeight: 700, fontSize: 20, color: '#0b1b2b' }}>Golf Event Planner</div>
          <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>Sign in to your account</div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={labelStyle}>Username or Email</label>
            <input
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="username or email@example.com"
              required
              autoFocus
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              style={inputStyle}
            />
          </div>

          {error && <div style={errorStyle}>{error}</div>}

          <button type="submit" disabled={loading} style={btnStyle(loading)}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <div style={{ marginTop: 20, textAlign: 'center', fontSize: 13, color: '#64748b' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: '#166534', fontWeight: 600, textDecoration: 'none' }}>
            Create one
          </Link>
        </div>
      </div>
    </div>
  )
}

const pageStyle = {
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 50%, #f0fdf4 100%)',
  padding: 20,
}

const cardStyle = {
  background: '#fff',
  borderRadius: 16,
  padding: '36px 40px',
  width: '100%',
  maxWidth: 400,
  boxShadow: '0 10px 40px rgba(0,0,0,0.10)',
  border: '1px solid #e5e7eb',
}

const headerStyle = {
  textAlign: 'center',
  marginBottom: 28,
}

const labelStyle = {
  display: 'block',
  fontSize: 13,
  fontWeight: 600,
  color: '#374151',
  marginBottom: 5,
}

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 8,
  border: '1px solid #d1d5db',
  fontSize: 14,
  boxSizing: 'border-box',
  outline: 'none',
  color: '#111827',
}

const errorStyle = {
  background: '#fef2f2',
  border: '1px solid #fecaca',
  color: '#dc2626',
  borderRadius: 8,
  padding: '10px 14px',
  fontSize: 13,
  fontWeight: 500,
}

const btnStyle = (loading) => ({
  background: loading ? '#86efac' : '#166534',
  color: '#fff',
  border: 'none',
  padding: '11px 0',
  borderRadius: 8,
  fontSize: 14,
  fontWeight: 700,
  cursor: loading ? 'default' : 'pointer',
  transition: 'background 0.15s',
  marginTop: 4,
})
