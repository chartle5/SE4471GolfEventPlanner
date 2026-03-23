import React from 'react'
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/plan', label: 'Plan Tournament' },
  { to: '/knowledge', label: 'Knowledge Base' }
]

export default function Sidebar(){
  return (
    <aside className="sidebar">
      <div className="brand">Golf Tournament Planner</div>
      <div className="muted small">Organizer dashboard • Demo</div>
      <nav className="nav" style={{marginTop:18}}>
        {links.map(l=> (
          <NavLink key={l.to} to={l.to} className={({isActive})=> isActive ? 'active' : '' }>{l.label}</NavLink>
        ))}
      </nav>
    </aside>
  )
}
