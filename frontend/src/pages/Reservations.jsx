import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from '../components/Icon'
import ConfirmDialog from '../components/ConfirmDialog'

export default function Reservations() {
  const navigate = useNavigate()
  const [reservations, setReservations] = useState([])
  const [pendingDelete, setPendingDelete] = useState(null)

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      setReservations([...stored].reverse())
    } catch {
      setReservations([])
    }
  }, [])

  function confirmDelete() {
    const id = pendingDelete
    setPendingDelete(null)
    try {
      const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      const updated = stored.filter(r => String(r.id) !== String(id))
      localStorage.setItem('savedReservations', JSON.stringify(updated))
      setReservations([...updated].reverse())
    } catch {}
  }

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">Saved Events</div>
        <h1 className="page-title">Reservations</h1>
        <div className="page-sub">Select a tournament to view documents and send options</div>
      </div>

      {reservations.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><Icon name="trophy" size={26} /></div>
          <h3>No reservations yet</h3>
          <p style={{ margin: '6px 0 18px' }}>
            Plan a tournament and click <strong>Save Tournament</strong> to see it here.
          </p>
          <button className="btn btn-primary" onClick={() => navigate('/plan')}>
            <Icon name="flag" size={16} /> Plan a Tournament
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {reservations.map(res => {
            const t = res.tournament || {}
            return (
              <div
                key={res.id}
                className="card card-flush card-hover"
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/reservations/${res.id}`)}
              >
                <div style={{
                  background: 'linear-gradient(135deg, var(--forest) 0%, var(--pine) 100%)',
                  color: '#fff',
                  padding: '18px 22px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: 12,
                }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 700, fontSize: 20, letterSpacing: 0.3 }}>
                      {t.name || 'Unnamed Tournament'}
                    </div>
                    <div style={{ fontSize: 13, opacity: 0.9, marginTop: 5, display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
                      {[t.date, t.venue, t.format].filter(Boolean).join(' · ')}
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.78, marginTop: 4 }}>
                      {t.playerCount > 0 && <span>{t.playerCount} players</span>}
                      {t.teeTimeStart && <span> · First tee {t.teeTimeStart}</span>}
                      {t.teeTimeInterval > 0 && <span> · {t.teeTimeInterval}-min intervals</span>}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, opacity: 0.7, textAlign: 'right', flexShrink: 0 }}>
                    Saved {new Date(res.savedAt).toLocaleDateString()}
                  </div>
                </div>

                <div
                  style={{ padding: '12px 22px', display: 'flex', gap: 10, alignItems: 'center', background: 'var(--paper)' }}
                  onClick={e => e.stopPropagation()}
                >
                  <button className="btn btn-primary btn-sm" onClick={() => navigate(`/reservations/${res.id}`)}>
                    <Icon name="doc" size={15} /> View Documents
                  </button>
                  {res.tournament_id && <span className="badge badge-dot">Saved to DB</span>}
                  <div className="spacer" />
                  <button className="btn btn-danger btn-sm" onClick={() => setPendingDelete(res.id)}>
                    <Icon name="trash" size={15} /> Delete
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {pendingDelete != null && (
        <ConfirmDialog
          title="Remove reservation?"
          message="This will remove the saved tournament from this device. This cannot be undone."
          confirmLabel="Remove"
          onConfirm={confirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  )
}
