import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Reservations() {
  const navigate = useNavigate()
  const [reservations, setReservations] = useState([])

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      setReservations([...stored].reverse())
    } catch {
      setReservations([])
    }
  }, [])

  function handleDelete(e, id) {
    e.stopPropagation()
    if (!window.confirm('Remove this reservation?')) return
    try {
      const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      const updated = stored.filter(r => String(r.id) !== String(id))
      localStorage.setItem('savedReservations', JSON.stringify(updated))
      setReservations([...updated].reverse())
    } catch {}
  }

  if (reservations.length === 0) {
    return (
      <div>
        <h1 style={{ margin: 0 }}>Reservations</h1>
        <div className="muted small">Saved tournaments</div>
        <div style={{
          marginTop: 40,
          textAlign: 'center',
          color: '#6b7280',
          padding: 32,
          border: '2px dashed #e5e7eb',
          borderRadius: 10,
        }}>
          <p style={{ margin: 0, fontSize: 15 }}>No reservations saved yet.</p>
          <p style={{ margin: '8px 0 0', fontSize: 13 }}>
            Plan a tournament and click <strong>Save Tournament</strong> to see it here.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1 style={{ margin: 0 }}>Reservations</h1>
      <div className="muted small">Saved tournaments — select one to view documents and send options</div>
      <div style={{ height: 16 }} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {reservations.map(res => {
          const t = res.tournament || {}
          return (
            <div
              key={res.id}
              className="card"
              style={{ padding: 0, overflow: 'hidden', cursor: 'pointer' }}
              onClick={() => navigate(`/reservations/${res.id}`)}
            >
              {/* Card header */}
              <div style={{
                background: '#166534',
                color: '#fff',
                padding: '14px 20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
              }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 16 }}>{t.name || 'Unnamed Tournament'}</div>
                  <div style={{ fontSize: 13, opacity: 0.85, marginTop: 3 }}>
                    {[t.date, t.venue, t.format].filter(Boolean).join(' · ')}
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.7, marginTop: 2 }}>
                    {t.playerCount > 0 && <span>{t.playerCount} players</span>}
                    {t.teeTimeStart && <span> · First tee: {t.teeTimeStart}</span>}
                    {t.teeTimeInterval > 0 && <span> · {t.teeTimeInterval}-min intervals</span>}
                  </div>
                </div>
                <div style={{ fontSize: 11, opacity: 0.65, textAlign: 'right', flexShrink: 0, marginLeft: 12 }}>
                  Saved {new Date(res.savedAt).toLocaleDateString()}
                </div>
              </div>

              {/* Action bar */}
              <div
                style={{
                  padding: '10px 20px',
                  display: 'flex',
                  gap: 10,
                  alignItems: 'center',
                  background: '#f9fafb',
                }}
                onClick={e => e.stopPropagation()}
              >
                <button
                  onClick={() => navigate(`/reservations/${res.id}`)}
                  style={{
                    background: '#166534',
                    color: '#fff',
                    border: 'none',
                    padding: '6px 16px',
                    borderRadius: 6,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  View Documents
                </button>

                {res.tournament_id && (
                  <span style={{
                    fontSize: 11,
                    background: '#d1fae5',
                    color: '#166534',
                    borderRadius: 4,
                    padding: '2px 8px',
                    fontWeight: 500,
                  }}>
                    DB
                  </span>
                )}

                <div style={{ flex: 1 }} />

                <button
                  onClick={e => handleDelete(e, res.id)}
                  style={{
                    background: 'transparent',
                    border: '1px solid #dc2626',
                    color: '#dc2626',
                    padding: '5px 14px',
                    borderRadius: 6,
                    fontSize: 13,
                    cursor: 'pointer',
                    fontWeight: 500,
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

