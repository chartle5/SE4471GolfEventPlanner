import React from 'react'
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/plan', label: 'Plan Tournament', end: false },
  { to: '/knowledge', label: 'Knowledge Base', end: false },
  { to: '/reservations', label: 'Reservations', end: false },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-name">⛳ Golf Event Planner</div>
        <div className="brand-sub">Organizer dashboard</div>
      </div>
      <nav className="nav">
        {links.map(l => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => isActive ? 'active' : ''}
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div style={{
        padding: '14px 18px',
        borderTop: '1px solid rgba(255,255,255,0.07)',
        fontSize: 11,
        color: 'rgba(148,163,184,0.45)',
        letterSpacing: '0.02em',
      }}>
        SE4471 · Golf Event Planner
      </div>
    </aside>
  )
}

