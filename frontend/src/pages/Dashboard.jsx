import React from 'react'
import { Link } from 'react-router-dom'
import { tournamentState } from '../data/tournament'
import Icon from '../components/Icon'

function StatCard({ label, value, sub, icon, accent }) {
  return (
    <div className="card card-hover" style={{ position: 'relative', overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 3,
        background: accent,
      }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div className="eyebrow">{label}</div>
        <div style={{
          width: 34, height: 34, borderRadius: 9,
          background: 'var(--green-tint)', border: '1px solid var(--success-bd)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--fairway)',
        }}>
          <Icon name={icon} size={18} />
        </div>
      </div>
      <div style={{
        fontFamily: 'var(--font-serif)', fontSize: 30, fontWeight: 700,
        color: 'var(--ink)', lineHeight: 1.1, marginTop: 12,
        textTransform: label === 'Event Type' ? 'capitalize' : 'none',
      }}>
        {value || <span style={{ color: 'var(--line)' }}>—</span>}
      </div>
      {sub && <div style={{ fontSize: 12.5, color: 'var(--muted)', marginTop: 7, fontWeight: 500 }}>{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const t = tournamentState

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">Overview</div>
        <h1 className="page-title">Dashboard</h1>
        <div className="page-sub">A snapshot of your current tournament planning session</div>
      </div>

      <div className="cards" style={{ marginBottom: 22 }}>
        <StatCard
          label="Tournament"
          value={t.name}
          sub={[t.date, t.venue].filter(Boolean).join(' · ') || 'Not configured'}
          icon="trophy"
          accent="linear-gradient(90deg, var(--fairway), var(--fairway-lt))"
        />
        <StatCard
          label="Players"
          value={t.playerCount || '—'}
          sub={t.format ? `Format: ${t.format}` : 'Format not set'}
          icon="users"
          accent="linear-gradient(90deg, var(--champagne), var(--champagne-dark))"
        />
        <StatCard
          label="Event Type"
          value={t.eventType || 'individual'}
          sub={t.teamSize > 1 ? `${t.teamSize} players per team` : 'Solo play'}
          icon="flag"
          accent="linear-gradient(90deg, var(--forest), var(--fairway))"
        />
        <StatCard
          label="Status"
          value="Planning"
          sub="Documents not yet generated"
          icon="clock"
          accent="linear-gradient(90deg, var(--faint), var(--muted))"
        />
      </div>

      <div className="card" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 24,
        flexWrap: 'wrap',
        background: 'linear-gradient(135deg, #FFFFFF 0%, var(--green-tint) 130%)',
        borderColor: 'var(--success-bd)',
      }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', minWidth: 240 }}>
          <div style={{
            width: 46, height: 46, borderRadius: 12, flexShrink: 0,
            background: 'linear-gradient(140deg, var(--fairway), var(--forest))',
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff',
          }}>
            <Icon name="sparkle" size={22} />
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 600, fontSize: 19, color: 'var(--ink)' }}>
              Ready to plan your tournament?
            </div>
            <div className="small muted" style={{ marginTop: 4 }}>
              Chat with the AI assistant to build your schedule, brochure, rule sheet, and more.
            </div>
          </div>
        </div>
        <Link to="/plan" className="btn btn-gold">
          Plan Tournament
          <Icon name="arrowRight" size={16} />
        </Link>
      </div>
    </div>
  )
}
