import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Topbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="topbar">
      <div>
        <h2 style={{ margin: 0 }}>Golf Planner</h2>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Link to="/plan" className="small">Plan</Link>
        {user && (
          <span style={{ fontSize: 13, color: '#64748b' }}>
            {user.username}
          </span>
        )}
        <button
          onClick={handleLogout}
          style={{
            background: 'transparent',
            border: '1px solid #d1d5db',
            borderRadius: 6,
            padding: '4px 12px',
            fontSize: 13,
            cursor: 'pointer',
            color: '#374151',
          }}
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
