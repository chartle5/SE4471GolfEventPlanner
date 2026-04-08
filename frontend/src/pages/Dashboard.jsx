import React from 'react'
import { Link } from 'react-router-dom'
import { tournamentState } from '../data/tournament'

function StatCard({ label, value, sub, accentColor }) {
  return (
    <div className="card" style={{ borderTop: `3px solid ${accentColor}` }}>
      <div style={{
        fontSize: 10,
        fontWeight: 700,
        color: '#94a3b8',
        textTransform: 'uppercase',
        letterSpacing: '0.07em',
        marginBottom: 10,
      }}>
        {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 800, color: '#0f172a', lineHeight: 1.1 }}>
        {value || <span style={{ color: '#d1dbe8' }}>—</span>}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 7, fontWeight: 500 }}>
          {sub}
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const t = tournamentState

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1>Dashboard</h1>
        <div className="muted small" style={{ marginTop: 4 }}>Overview of your current tournament planning session</div>
      </div>

      <div className="cards" style={{ marginBottom: 20 }}>
        <StatCard
          label="Tournament"
          value={t.name}
          sub={[t.date, t.venue].filter(Boolean).join(' · ') || 'Not configured'}
          accentColor="#10b981"
        />
        <StatCard
          label="Players"
          value={t.playerCount || '—'}
          sub={t.format ? `Format: ${t.format}` : 'Format not set'}
          accentColor="#6366f1"
        />
        <StatCard
          label="Event Type"
          value={t.eventType || 'individual'}
          sub={t.teamSize > 1 ? `${t.teamSize} players per team` : 'Solo play'}
          accentColor="#f59e0b"
        />
        <StatCard
          label="Status"
          value="Planning"
          sub="Documents not yet generated"
          accentColor="#94a3b8"
        />
      </div>

      <div className="card" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 20,
        borderLeft: '4px solid #10b981',
      }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15, color: '#0f172a' }}>
            Ready to plan your tournament?
          </div>
          <div className="small muted" style={{ marginTop: 5 }}>
            Chat with the AI assistant to build your schedule, brochure, rule sheet, and more.
          </div>
        </div>
        <Link
          to="/plan"
          style={{
            background: '#1d6a47',
            color: '#fff',
            padding: '9px 20px',
            borderRadius: 8,
            textDecoration: 'none',
            fontSize: 14,
            fontWeight: 600,
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          Plan Tournament →
        </Link>
      </div>
    </div>
  )
}

