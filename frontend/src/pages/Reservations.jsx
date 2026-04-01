import React, { useState, useEffect } from 'react'

export default function Reservations() {
  const [reservations, setReservations] = useState([])
  const [expandedId, setExpandedId] = useState(null)
  const [modalRes, setModalRes] = useState(null)       // reservation whose modal is open
  const [recipientInput, setRecipientInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState(null)  // { ok, message } | null

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      // Show most recently saved first
      setReservations([...stored].reverse())
    } catch {
      setReservations([])
    }
  }, [])

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

  function openEmailModal(res) {
    setModalRes(res)
    setRecipientInput('')
    setSendResult(null)
  }

  function closeEmailModal() {
    if (sending) return
    setModalRes(null)
    setSendResult(null)
  }

  async function handleSendEmail() {
    if (!modalRes) return
    const emails = recipientInput
      .split(/[\s,;]+/)
      .map((e) => e.trim())
      .filter((e) => e.length > 0)
    if (emails.length === 0) {
      setSendResult({ ok: false, message: 'Please enter at least one email address.' })
      return
    }
    setSending(true)
    setSendResult(null)
    try {
      const res = await fetch('http://localhost:8000/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipients: emails,
          subject: modalRes.brochure?.subject || 'Tournament Brochure',
          body: modalRes.brochure?.body || '',
        }),
      })
      const data = await res.json()
      setSendResult({ ok: data.success, message: data.message })
      if (data.success) setTimeout(closeEmailModal, 2000)
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
                  onClick={() => openEmailModal(res)}
                  style={{ ...outlineBtnStyle, borderColor: '#2563eb', color: '#2563eb' }}
                >
                  Send Email Brochure
                </button>
                <button
                  onClick={() => handleDelete(res.id)}
                  style={{ ...outlineBtnStyle, borderColor: '#dc2626', color: '#dc2626' }}
                >
                  Delete
                </button>
              </div>



              {/* Tee schedule summary */}
              {res.schedule && res.schedule.length > 0 && (
                <div style={{ padding: '12px 20px' }}>
                  <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>Tee Schedule</div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#f3f4f6' }}>
                        <th style={thStyle}>Group</th>
                        <th style={thStyle}>Tee Time</th>
                        <th style={thStyle}>Players</th>
                      </tr>
                    </thead>
                    <tbody>
                      {res.schedule.map((row) => (
                        <tr key={row.group} style={{ borderBottom: '1px solid #f3f4f6' }}>
                          <td style={tdStyle}>Group {row.group}</td>
                          <td style={{ ...tdStyle, fontWeight: 600, color: '#166534' }}>{row.teeTime}</td>
                          <td style={tdStyle}>{row.players.join(', ')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

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

      {/* ── Email Brochure Modal ── */}
      {modalRes && (
        <div
          onClick={closeEmailModal}
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
              background: '#166534',
              color: '#fff',
              padding: '16px 20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>Send Email Brochure</div>
                <div style={{ fontSize: 12, opacity: 0.8, marginTop: 2 }}>
                  {modalRes.tournament?.name || 'Tournament'}
                </div>
              </div>
              <button
                onClick={closeEmailModal}
                style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}
                disabled={sending}
              >✕</button>
            </div>

            {/* Modal body */}
            <div style={{ padding: '20px 24px' }}>
              <div style={{ marginBottom: 6, fontSize: 12, color: '#6b7280' }}>
                <strong>Subject:</strong> {modalRes.brochure?.subject || '—'}
              </div>

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
              <button onClick={closeEmailModal} disabled={sending} style={outlineBtnStyle}>
                Cancel
              </button>
              <button
                onClick={handleSendEmail}
                disabled={sending}
                style={{
                  background: sending ? '#86efac' : '#166534',
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
                {sending ? 'Sending…' : 'Send Email'}
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
