import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Topbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const initial = user?.username?.charAt(0)?.toUpperCase() ?? '?'

  return (
    <div className="topbar">
      <div style={{ fontSize: 14, color: '#64748b', fontWeight: 500 }}>
        Welcome back{user ? <span style={{ color: '#0f172a', fontWeight: 600 }}>, {user.username}</span> : ''}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {user && (
          <div style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #1d6a47 0%, #10b981 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 13,
            fontWeight: 700,
            color: '#fff',
            flexShrink: 0,
          }}>
            {initial}
          </div>
        )}
        <button
          onClick={handleLogout}
          style={{
            background: 'transparent',
            border: '1px solid #d1dbe8',
            borderRadius: 7,
            padding: '5px 14px',
            fontSize: 13,
            fontWeight: 500,
            cursor: 'pointer',
            color: '#475569',
            fontFamily: 'inherit',
            transition: 'border-color 0.15s, background 0.15s',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = '#f8fafc'
            e.currentTarget.style.borderColor = '#b0bcc8'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'transparent'
            e.currentTarget.style.borderColor = '#d1dbe8'
          }}
        >
          Sign out
        </button>
      </div>
    </div>
  )
}

