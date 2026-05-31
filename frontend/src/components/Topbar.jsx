import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Icon from './Icon'

export default function Topbar({ onMenu }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const initial = user?.username?.charAt(0)?.toUpperCase() ?? '?'

  return (
    <div className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
        <button className="nav-toggle" onClick={onMenu} aria-label="Open menu">
          <Icon name="menu" size={20} />
        </button>
        <div className="topbar-greet">
          Welcome back{user ? <span>, <strong>{user.username}</strong></span> : ''}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        {user && <div className="avatar">{initial}</div>}
        <button className="btn btn-ghost btn-sm" onClick={handleLogout}>
          <Icon name="logout" size={15} />
          Sign out
        </button>
      </div>
    </div>
  )
}
