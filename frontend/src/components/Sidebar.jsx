import React from 'react'
import { NavLink } from 'react-router-dom'
import Icon from './Icon'

const links = [
  { to: '/', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/plan', label: 'Plan Tournament', icon: 'flag', end: false },
  { to: '/knowledge', label: 'Knowledge Base', icon: 'book', end: false },
  { to: '/reservations', label: 'Reservations', icon: 'trophy', end: false },
]

export default function Sidebar({ open = false, onClose }) {
  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="brand">
        <div className="brand-mark">
          <Icon name="flag" size={21} strokeWidth={1.9} />
        </div>
        <div>
          <div className="brand-name">Golf Event Planner</div>
          <div className="brand-sub">Organizer Suite</div>
        </div>
      </div>

      <nav className="nav">
        <div className="nav-label">Menu</div>
        {links.map(l => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            onClick={onClose}
            className={({ isActive }) => isActive ? 'active' : ''}
          >
            <Icon name={l.icon} size={18} />
            {l.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-foot">
        SE4471 · Golf Event Planner
      </div>
    </aside>
  )
}
