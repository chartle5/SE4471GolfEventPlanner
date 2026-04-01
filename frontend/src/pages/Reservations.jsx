import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'

export default function Reservations() {
  const { authHeaders } = useAuth()
  const [reservations, setReservations] = useState([])
  const [expandedId, setExpandedId] = useState(null)
  // liveData: { [tournament_id]: { schedule, registration_token, players_registered, total_players, status } }
  const [liveData, setLiveData] = useState({})

  // modal type: 'invite' | 'schedule' | null
  const [modalType, setModalType]       = useState(null)
  const [modalRes, setModalRes]         = useState(null)
  const [recipientInput, setRecipientInput] = useState('')
  const [sending, setSending]           = useState(false)
  const [sendResult, setSendResult]     = useState(null)  // { ok, message } | null

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      setReservations([...stored].reverse())
    } catch {
      setReservations([])
    }
  }, [])

  // Poll the backend every 15 s for live schedules on all saved tournaments
  useEffect(() => {
    const ids = reservations
      .filter((r) => r.tournament_id)
      .map((r) => r.tournament_id)
    if (ids.length === 0) return

    async function fetchLive() {
      const results = await Promise.allSettled(
        ids.map((id) =>
          fetch(`http://localhost:8000/tournaments/${id}/schedule`)
            .then((r) => (r.ok ? r.json() : null))
            .catch(() => null)
        )
      )
      setLiveData((prev) => {
        const next = { ...prev }
        ids.forEach((id, i) => {
          const val = results[i].status === 'fulfilled' ? results[i].value : null
          if (val) next[id] = val
        })
        return next
      })
    }

    fetchLive()
    const timer = setInterval(fetchLive, 15000)
    return () => clearInterval(timer)
  }, [reservations])

  function handleDelete(id) {
    if (!window.confirm('Remove this reservation?')) return
    try {
      const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      const updated = stored.filter((r) => r.id !== id)
      localStorage.setItem('savedReservations', JSON.stringify(updated))
      setReservations([...updated].reverse())
    } catch {
      // ignore
    }
  }

  function openModal(res, type) {
    setModalRes(res)
    setModalType(type)
    setRecipientInput('')
    setSendResult(null)
  }

  function closeModal() {
    if (sending) return
    setModalRes(null)
    setModalType(null)
    setSendResult(null)
  }

  function parseEmails(input) {
    return input
      .split(/[\s,;]+/)
      .map((e) => e.trim())
      .filter((e) => e.length > 0)
  }

  async function handleSendInvite() {
    if (!modalRes) return
    const emails = parseEmails(recipientInput)
    if (emails.length === 0) {
      setSendResult({ ok: false, message: 'Please enter at least one email address.' })
      return
    }
    setSending(true)
    setSendResult(null)
    try {
      // Prefer token already stored locally or fetched live
      let token =
        modalRes.registration_token ||
        liveData[modalRes.tournament_id]?.registration_token ||
        ''

      // No token yet — save to MongoDB now so the invite can include the
      // "Register Now" button with a real registration link.
      if (!token) {
        try {
          const saveRes = await fetch('http://localhost:8000/tournaments', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({
              tournament: modalRes.tournament,
              schedule: modalRes.schedule,
              brochure: modalRes.brochure,
            }),
          })
          if (saveRes.ok) {
            const saveData = await saveRes.json()
            token = saveData.registration_token
            // Persist back to localStorage so future invites work instantly
            const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
            const updated = stored.map((r) =>
              r.id === modalRes.id
                ? { ...r, tournament_id: saveData.tournament_id, registration_token: token }
                : r
            )
            localStorage.setItem('savedReservations', JSON.stringify(updated))
            setReservations([...updated].reverse())
          }
        } catch {
          // Fall through — invite sent without link rather than failing entirely
        }
      }

      const registrationLink = token
        ? `${window.location.origin}/player-register/${token}`
        : ''
      const res = await fetch('http://localhost:8000/email/send-invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipients: emails,
          tournament_meta: modalRes.brochure?.meta || modalRes.tournament || {},
          registration_link: registrationLink,
        }),
      })
      const data = await res.json()
      setSendResult({ ok: data.success, message: data.message })
      if (data.success) setTimeout(closeModal, 2000)
    } catch {
      setSendResult({ ok: false, message: 'Could not reach the server. Is the backend running?' })
    } finally {
      setSending(false)
    }
  }

  async function handleSendSchedule() {
    if (!modalRes) return
    const emails = parseEmails(recipientInput)
    if (emails.length === 0) {
      setSendResult({ ok: false, message: 'Please enter at least one email address.' })
      return
    }
    setSending(true)
    setSendResult(null)
    try {
      const t = modalRes.tournament || {}
      const meta = modalRes.brochure?.meta || {}
      const res = await fetch('http://localhost:8000/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipients: emails,
          subject: modalRes.brochure?.subject || 'Tournament Schedule',
          body: modalRes.brochure?.body || '',
          schedule: modalRes.schedule || [],
          tournament_name: t.name || meta.name || '',
          tournament_date: t.date || meta.date || '',
          tournament_venue: t.venue || meta.venue || '',
          tournament_format: t.format || meta.format || '',
        }),
      })
      const data = await res.json()
      setSendResult({ ok: data.success, message: data.message })
      if (data.success) setTimeout(closeModal, 2000)
    } catch {
      setSendResult({ ok: false, message: 'Could not reach the server. Is the backend running?' })
    } finally {
      setSending(false)
    }
  }

  if (reservations.length === 0) {
    return (
      <div>
        <h1 style={{ margin: 0 }}>Reservations</h1>
        <div className="muted small">Saved tournament schedules</div>
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
            Plan a tournament, generate a schedule, and click <strong>Save Schedule</strong> to see it here.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1 style={{ margin: 0 }}>Reservations</h1>
      <div className="muted small">Saved tournament schedules</div>
      <div style={{ height: 16 }} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {reservations.map((res) => {
          const t = res.tournament || {}
          const isExpanded = expandedId === res.id

          return (
            <div key={res.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>

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
                    {t.date} &nbsp;·&nbsp; {t.venue} &nbsp;·&nbsp; {t.format}
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.7, marginTop: 2 }}>
                    {t.playerCount} players &nbsp;·&nbsp; First tee: {t.teeTimeStart} &nbsp;·&nbsp; {t.teeTimeInterval}-min intervals
                  </div>
                </div>
                <div style={{ fontSize: 11, opacity: 0.65, textAlign: 'right', flexShrink: 0, marginLeft: 12 }}>
                  Saved {new Date(res.savedAt).toLocaleDateString()}
                </div>
              </div>

              {/* Action bar */}
              <div style={{
                padding: '10px 20px',
                display: 'flex',
                gap: 10,
                borderBottom: '1px solid #e5e7eb',
                background: '#f9fafb',
                flexWrap: 'wrap',
              }}>
                <button
                  onClick={() => setExpandedId(isExpanded ? null : res.id)}
                  style={outlineBtnStyle}
                >
                  {isExpanded ? 'Hide Brochure' : 'View Brochure'}
                </button>
                <button
                  onClick={() => openModal(res, 'invite')}
                  style={{ ...outlineBtnStyle, borderColor: '#2563eb', color: '#2563eb' }}
                >
                  Send Invite
                </button>
                <button
                  onClick={() => openModal(res, 'schedule')}
                  style={{ ...outlineBtnStyle, borderColor: '#166534', color: '#166534' }}
                >
                  Send Schedule
                </button>
                <button
                  onClick={() => handleDelete(res.id)}
                  style={{ ...outlineBtnStyle, borderColor: '#dc2626', color: '#dc2626' }}
                >
                  Delete
                </button>
              </div>

              {/* Tee schedule summary — uses live data from DB when available */}
              {(() => {
                const live = liveData[res.tournament_id]
                const displaySchedule = live?.schedule || res.schedule
                if (!displaySchedule || displaySchedule.length === 0) return null
                return (
                  <div style={{ padding: '12px 20px' }}>
                    <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      Tee Schedule
                      {live && (
                        <span style={{ fontSize: 11, background: '#d1fae5', color: '#166534', borderRadius: 4, padding: '1px 7px', fontWeight: 500 }}>
                          Live
                        </span>
                      )}
                      {live && live.players_registered != null && (
                        <span style={{ fontSize: 11, color: '#6b7280', fontWeight: 400 }}>
                          {live.players_registered}/{live.total_players} registered
                        </span>
                      )}
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                      <thead>
                        <tr style={{ background: '#f3f4f6' }}>
                          <th style={thStyle}>Group</th>
                          <th style={thStyle}>Tee Time</th>
                          <th style={thStyle}>Players</th>
                        </tr>
                      </thead>
                      <tbody>
                        {displaySchedule.map((row) => (
                          <tr key={row.group} style={{ borderBottom: '1px solid #f3f4f6' }}>
                            <td style={tdStyle}>Group {row.group}</td>
                            <td style={{ ...tdStyle, fontWeight: 600, color: '#166534' }}>{row.teeTime}</td>
                            <td style={tdStyle}>{row.players.join(', ')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
              })()}

              {/* Brochure preview (expandable) */}
              {isExpanded && res.brochure && (
                <div style={{
                  borderTop: '1px solid #e5e7eb',
                  padding: '16px 20px',
                  background: '#fff',
                }}>
                  <div style={{ fontWeight: 700, marginBottom: 6, fontSize: 14 }}>
                    Email Brochure Preview
                  </div>
                  <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 8, padding: '16px 20px' }}>
                    <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 10 }}>
                      <strong>To:</strong> {res.brochure.to}<br />
                      <strong>Subject:</strong> {res.brochure.subject}
                    </div>
                    <pre style={{
                      fontFamily: 'monospace',
                      fontSize: 12,
                      whiteSpace: 'pre-wrap',
                      margin: 0,
                      color: '#374151',
                      lineHeight: 1.6,
                    }}>
                      {res.brochure.body}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* ── Email Modal (shared for Invite + Schedule) ── */}
      {modalRes && modalType && (
        <div
          onClick={closeModal}
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.45)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: '#fff',
              borderRadius: 12,
              width: '100%',
              maxWidth: 520,
              boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
              overflow: 'hidden',
            }}
          >
            {/* Modal header */}
            <div style={{
              background: modalType === 'invite' ? '#1d4ed8' : '#166534',
              color: '#fff',
              padding: '16px 20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>
                  {modalType === 'invite' ? 'Send Invite' : 'Send Schedule'}
                </div>
                <div style={{ fontSize: 12, opacity: 0.8, marginTop: 2 }}>
                  {modalRes.tournament?.name || 'Tournament'}
                </div>
              </div>
              <button
                onClick={closeModal}
                style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}
                disabled={sending}
              >✕</button>
            </div>

            {/* Modal description */}
            <div style={{
              background: modalType === 'invite' ? '#eff6ff' : '#f0fdf4',
              borderBottom: '1px solid #e5e7eb',
              padding: '10px 20px',
              fontSize: 12,
              color: '#374151',
            }}>
              {modalType === 'invite'
                ? (() => {
                    const hasToken =
                      modalRes.registration_token ||
                      liveData[modalRes.tournament_id]?.registration_token
                    return `Sends tournament details + a "Register Now" button so players can claim a tee-time slot.${
                      !hasToken ? ' ⚠️ No registration link found — make sure you are logged in and re-save the schedule.' : ''
                    }`
                  })()
                : 'Sends the full tee-time brochure with all player assignments.'}
            </div>

            {/* Modal body */}
            <div style={{ padding: '20px 24px' }}>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 14, marginBottom: 6 }}>
                Recipient Emails
              </label>
              <textarea
                value={recipientInput}
                onChange={(e) => setRecipientInput(e.target.value)}
                placeholder="e.g. alice@example.com bob@example.com carol@example.com"
                rows={3}
                disabled={sending}
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  border: '1px solid #d1d5db',
                  borderRadius: 8,
                  padding: '10px 12px',
                  fontSize: 13,
                  fontFamily: 'inherit',
                  resize: 'vertical',
                  outline: 'none',
                  color: '#111827',
                }}
              />
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>
                Separate multiple addresses with spaces, commas, or newlines.
              </div>

              {/* Result feedback */}
              {sendResult && (
                <div style={{
                  marginTop: 12,
                  padding: '10px 14px',
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  background: sendResult.ok ? '#f0fdf4' : '#fef2f2',
                  color: sendResult.ok ? '#166534' : '#dc2626',
                  border: `1px solid ${sendResult.ok ? '#bbf7d0' : '#fecaca'}`,
                }}>
                  {sendResult.message}
                </div>
              )}
            </div>

            {/* Modal footer */}
            <div style={{
              padding: '12px 24px 20px',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 10,
            }}>
              <button onClick={closeModal} disabled={sending} style={outlineBtnStyle}>
                Cancel
              </button>
              <button
                onClick={modalType === 'invite' ? handleSendInvite : handleSendSchedule}
                disabled={sending}
                style={{
                  background: sending
                    ? '#86efac'
                    : modalType === 'invite' ? '#2563eb' : '#166534',
                  color: '#fff',
                  border: 'none',
                  padding: '7px 20px',
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: sending ? 'default' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {sending ? 'Sending…' : modalType === 'invite' ? 'Send Invite' : 'Send Schedule'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const outlineBtnStyle = {
  background: 'transparent',
  border: '1px solid #6b7280',
  color: '#374151',
  padding: '5px 14px',
  borderRadius: 6,
  fontSize: 13,
  cursor: 'pointer',
  fontWeight: 500,
}

const thStyle = {
  padding: '8px 12px',
  textAlign: 'left',
  fontWeight: 600,
  color: '#374151',
  borderBottom: '2px solid #e5e7eb',
  fontSize: 12,
}

const tdStyle = {
  padding: '8px 12px',
  color: '#111827',
  fontSize: 13,
}

