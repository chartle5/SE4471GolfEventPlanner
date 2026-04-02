import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'

export default function ScheduleDraft() {
  const [schedule, setSchedule] = useState(null)
  const [brochure, setBrochure] = useState(null)
  const [tournament, setTournament] = useState(null)
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const { authHeaders } = useAuth()

  const loadFromStorage = useCallback(() => {
    try {
      const s = localStorage.getItem('golfDraftSchedule')
      const b = localStorage.getItem('golfDraftBrochure')
      const t = localStorage.getItem('golfDraftTournament')
      if (s) setSchedule(JSON.parse(s))
      if (b) setBrochure(JSON.parse(b))
      if (t) setTournament(JSON.parse(t))
    } catch {
      // ignore parse errors
    }
  }, [])

  useEffect(() => {
    loadFromStorage()
    // Refresh data when the tab regains focus (e.g. after chat edits)
    const onFocus = () => {
      setSaved(false)
      loadFromStorage()
    }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [loadFromStorage])

  async function handleSave() {
    if (!tournament || !schedule || !brochure) return
    setSaving(true)
    try {
      const existing = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      const entry = {
        id: Date.now(),
        savedAt: new Date().toISOString(),
        tournament,
        schedule,
        brochure,
        tournament_id: null,
        registration_token: null,
      }

      // Attempt to persist to MongoDB so we get a registration token
      try {
        const res = await fetch('http://localhost:8000/tournaments', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({ tournament, schedule, brochure }),
        })
        if (res.ok) {
          const data = await res.json()
          entry.tournament_id = data.tournament_id
          entry.registration_token = data.registration_token
        }
      } catch {
        // DB save failed — still save locally without the registration link
      }

      existing.push(entry)
      localStorage.setItem('savedReservations', JSON.stringify(existing))
      setSaved(true)
    } catch {
      alert('Failed to save — storage error.')
    } finally {
      setSaving(false)
    }
  }

  if (!schedule) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>
        <h2>No schedule found</h2>
        <p>Return to the planner and click <strong>Generate Documents</strong> to create a schedule.</p>
      </div>
    )
  }

  const meta = brochure?.meta || {}

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px', fontFamily: 'system-ui, sans-serif' }}>

      {/* Header */}
      <div style={{
        background: '#166534',
        color: '#fff',
        borderRadius: 10,
        padding: '20px 28px',
        marginBottom: 24,
      }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>{meta.name || 'Tournament Schedule'}</h1>
        <div style={{ marginTop: 6, opacity: 0.85, fontSize: 14 }}>
          {meta.date && <span>{meta.date}</span>}
          {meta.numberOfDays > 1 && <span> ({meta.numberOfDays} days)</span>}
          {meta.venue && <span> &nbsp;·&nbsp; {meta.venue}</span>}
          {meta.format && <span> &nbsp;·&nbsp; {meta.format}</span>}
          {meta.eventType && <span> &nbsp;·&nbsp; {meta.eventType === 'team' ? `Teams of ${meta.teamSize}` : 'Individual'}</span>}
        </div>
        <div style={{ marginTop: 4, opacity: 0.75, fontSize: 13 }}>
          {meta.playerCount} players &nbsp;·&nbsp; First tee: {meta.teeTimeStart} &nbsp;·&nbsp; {meta.teeTimeInterval}-min intervals
          {meta.registrationDeadline && <span> &nbsp;·&nbsp; Reg. closes: {meta.registrationDeadline}</span>}
          {meta.entryFee > 0 && <span> &nbsp;·&nbsp; Entry: ${meta.entryFee}</span>}
        </div>
      </div>

      {/* Draft banner */}
      <div style={{
        background: '#fef9c3',
        border: '1px solid #fde047',
        borderRadius: 8,
        padding: '10px 16px',
        fontSize: 13,
        marginBottom: 20,
        color: '#854d0e',
      }}>
        <strong>Draft</strong> — Return to the planner chat to make changes. This page auto-refreshes when you come back.
      </div>

      {/* Tee Time Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e7eb', fontWeight: 700, fontSize: 15 }}>
          Tee Time Schedule
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ background: '#f9fafb' }}>
              <th style={thStyle}>Group</th>
              <th style={thStyle}>Tee Time</th>
              <th style={thStyle}>Players</th>
            </tr>
          </thead>
          <tbody>
            {schedule.map((row) => (
              <tr key={row.group} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={tdStyle}>Group {row.group}</td>
                <td style={{ ...tdStyle, fontWeight: 600, color: '#166534' }}>{row.teeTime}</td>
                <td style={tdStyle}>{row.players.join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Save button */}
      <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 16 }}>
        {saved ? (
          <div style={{
            background: '#f0fdf4',
            border: '1px solid #86efac',
            borderRadius: 8,
            padding: '10px 20px',
            color: '#166534',
            fontWeight: 600,
            fontSize: 14,
          }}>
            Schedule saved! Return to the planner to continue editing, or visit the Reservations page.
          </div>
        ) : (
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              background: saving ? '#93c5fd' : '#2563eb',
              color: '#fff',
              border: 'none',
              padding: '10px 28px',
              borderRadius: 8,
              fontWeight: 700,
              fontSize: 15,
              cursor: saving ? 'default' : 'pointer',
            }}
          >
            {saving ? 'Saving…' : 'Save Schedule'}
          </button>
        )}
      </div>
    </div>
  )
}

const thStyle = {
  padding: '10px 16px',
  textAlign: 'left',
  fontWeight: 600,
  color: '#374151',
  borderBottom: '2px solid #e5e7eb',
  fontSize: 13,
}

const tdStyle = {
  padding: '10px 16px',
  color: '#111827',
}
