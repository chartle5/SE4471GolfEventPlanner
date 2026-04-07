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

  // registrants modal
  const [registrantsRes, setRegistrantsRes]       = useState(null)
  const [registrantsData, setRegistrantsData]     = useState(null)
  const [registrantsLoading, setRegistrantsLoading] = useState(false)

  // cart placards download
  const [placardLoading, setPlacardLoading]       = useState(null)  // tournament_id | null

  // club sheet modal
  const [clubSheetRes, setClubSheetRes]           = useState(null)
  const [clubSheetEmails, setClubSheetEmails]     = useState('')
  const [clubOrgName, setClubOrgName]             = useState('')
  const [clubOrgEmail, setClubOrgEmail]           = useState('')
  const [clubOrgPhone, setClubOrgPhone]           = useState('')
  const [clubSheetSending, setClubSheetSending]   = useState(false)
  const [clubSheetResult, setClubSheetResult]     = useState(null)

  // rule sheet modal
  const [ruleSheetRes, setRuleSheetRes]           = useState(null)
  const [ruleSheetEmails, setRuleSheetEmails]     = useState('')
  const [ruleSheetSending, setRuleSheetSending]   = useState(false)
  const [ruleSheetResult, setRuleSheetResult]     = useState(null)

  // F&B summary modal
  const [fnbRes, setFnbRes]                       = useState(null)
  const [fnbEmails, setFnbEmails]                 = useState('')
  const [fnbSending, setFnbSending]               = useState(false)
  const [fnbResult, setFnbResult]                 = useState(null)

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

  async function openRegistrantsModal(res) {
    setRegistrantsRes(res)
    setRegistrantsData(null)
    setRegistrantsLoading(true)
    try {
      const r = await fetch(
        `http://localhost:8000/tournaments/${res.tournament_id}/registrations`,
        { headers: authHeaders() }
      )
      if (r.ok) {
        setRegistrantsData(await r.json())
      } else {
        setRegistrantsData({ error: 'Failed to load registrations.' })
      }
    } catch {
      setRegistrantsData({ error: 'Could not reach the server.' })
    } finally {
      setRegistrantsLoading(false)
    }
  }

  function closeModal() {
    if (sending) return
    setModalRes(null)
    setModalType(null)
    setSendResult(null)
  }

  async function handleDownloadPlacards(res) {
    if (placardLoading) return
    setPlacardLoading(res.tournament_id)
    try {
      const response = await fetch(
        `http://localhost:8000/tournaments/${res.tournament_id}/cart-placards`,
        { headers: authHeaders() }
      )
      if (!response.ok) {
        alert('Failed to generate cart placards. Is the backend running?')
        return
      }
      const blob = await response.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      const safeName = (res.tournament?.name || 'tournament').replace(/\s+/g, '-').toLowerCase()
      a.href     = url
      a.download = `cart-placards-${safeName}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      alert('Could not reach the server. Is the backend running?')
    } finally {
      setPlacardLoading(null)
    }
  }

  async function handleSendClubSheet() {
    if (!clubSheetRes) return
    const emails = parseEmails(clubSheetEmails)
    if (emails.length === 0) {
      setClubSheetResult({ ok: false, message: 'Please enter at least one email address.' })
      return
    }
    setClubSheetSending(true)
    setClubSheetResult(null)
    try {
      const res = await fetch(
        `http://localhost:8000/tournaments/${clubSheetRes.tournament_id}/send-club-sheet`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          body: JSON.stringify({
            emails,
            organizer_name: clubOrgName,
            organizer_email: clubOrgEmail,
            organizer_phone: clubOrgPhone,
          }),
        }
      )
      const data = await res.json()
      setClubSheetResult({ ok: data.success, message: data.message })
      if (data.success) setTimeout(() => setClubSheetRes(null), 2000)
    } catch {
      setClubSheetResult({ ok: false, message: 'Could not reach the server. Is the backend running?' })
    } finally {
      setClubSheetSending(false)
    }
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
                  onClick={() => openRegistrantsModal(res)}
                  disabled={!res.tournament_id}
                  style={{ ...outlineBtnStyle, borderColor: '#7c3aed', color: '#7c3aed' }}
                >
                  View Registrants
                </button>
                <button
                  onClick={() => handleDownloadPlacards(res)}
                  disabled={!res.tournament_id || placardLoading === res.tournament_id}
                  style={{ ...outlineBtnStyle, borderColor: '#0369a1', color: '#0369a1' }}
                >
                  {placardLoading === res.tournament_id ? 'Generating…' : 'Cart Placards'}
                </button>
                <button
                  onClick={() => {
                    setClubSheetRes(res)
                    setClubSheetEmails('')
                    setClubOrgName('')
                    setClubOrgEmail('')
                    setClubOrgPhone('')
                    setClubSheetResult(null)
                  }}
                  disabled={!res.tournament_id}
                  style={{ ...outlineBtnStyle, borderColor: '#d97706', color: '#d97706' }}
                >
                  Send Club Sheet
                </button>
                <button
                  onClick={() => { setRuleSheetRes(res); setRuleSheetEmails(''); setRuleSheetResult(null) }}
                  disabled={!res.tournament_id}
                  style={{ ...outlineBtnStyle, borderColor: '#0891b2', color: '#0891b2' }}
                >
                  Send Rule Sheet
                </button>
                {res.tournament?.cateringEnabled && (
                  <button
                    onClick={() => { setFnbRes(res); setFnbEmails(''); setFnbResult(null) }}
                    disabled={!res.tournament_id}
                    style={{ ...outlineBtnStyle, borderColor: '#b45309', color: '#b45309' }}
                  >
                    F&amp;B Summary
                  </button>
                )}
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

      {/* ── Registrants Modal ── */}
      {registrantsRes && (
        <div
          onClick={() => setRegistrantsRes(null)}
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
              maxWidth: 820,
              maxHeight: '80vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
              overflow: 'hidden',
            }}
          >
            {/* Modal header */}
            <div style={{
              background: '#7c3aed',
              color: '#fff',
              padding: '16px 20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexShrink: 0,
            }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>Registered Players</div>
                <div style={{ fontSize: 12, opacity: 0.8, marginTop: 2 }}>
                  {registrantsRes.tournament?.name || 'Tournament'}
                </div>
              </div>
              <button
                onClick={() => setRegistrantsRes(null)}
                style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}
              >✕</button>
            </div>

            {/* Modal body */}
            <div style={{ overflowY: 'auto', flex: 1, padding: '20px 24px' }}>
              {registrantsLoading && (
                <p style={{ color: '#6b7280', textAlign: 'center' }}>Loading…</p>
              )}
              {registrantsData?.error && (
                <p style={{ color: '#dc2626', textAlign: 'center' }}>{registrantsData.error}</p>
              )}
              {registrantsData && !registrantsData.error && (
                registrantsData.registrations?.length === 0 ? (
                  <p style={{ color: '#6b7280', textAlign: 'center', padding: '24px 0' }}>
                    No players have registered yet.
                  </p>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: '#f3f4f6', borderBottom: '2px solid #e5e7eb' }}>
                        <th style={regThStyle}>#</th>
                        <th style={regThStyle}>Name</th>
                        <th style={regThStyle}>Phone</th>
                        <th style={regThStyle}>Rental Clubs</th>
                        {registrantsData.event_type === 'team' && <th style={regThStyle}>Team</th>}
                        <th style={regThStyle}>Tee Slot</th>
                        <th style={regThStyle}>Registered At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {registrantsData.registrations.map((reg, i) => (
                        <tr key={reg.registration_id || i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                          <td style={regTdStyle}>{i + 1}</td>
                          <td style={{ ...regTdStyle, fontWeight: 600 }}>{reg.first_name} {reg.last_name}</td>
                          <td style={regTdStyle}>{reg.phone_number || '—'}</td>
                          <td style={regTdStyle}>
                            {reg.rental_clubs
                              ? `Yes — ${reg.club_hand === 'left' ? 'Left' : 'Right'} Handed`
                              : 'No'}
                          </td>
                          {registrantsData.event_type === 'team' && (
                            <td style={regTdStyle}>{reg.team_name || '—'}</td>
                          )}
                          <td style={regTdStyle}>{reg.slot_description || '—'}</td>
                          <td style={regTdStyle}>
                            {reg.registered_at
                              ? new Date(reg.registered_at).toLocaleString()
                              : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
              )}
            </div>

            {/* Modal footer */}
            <div style={{ padding: '12px 24px 20px', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setRegistrantsRes(null)}
                style={outlineBtnStyle}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      {/* ── Club Sheet Modal ── */}
      {clubSheetRes && (
        <div
          onClick={() => { if (!clubSheetSending) setClubSheetRes(null) }}
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
            {/* Header */}
            <div style={{
              background: '#d97706',
              color: '#fff',
              padding: '16px 20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>Send Club Operations Sheet</div>
                <div style={{ fontSize: 12, opacity: 0.85, marginTop: 2 }}>
                  {clubSheetRes.tournament?.name || 'Tournament'}
                </div>
              </div>
              <button
                onClick={() => setClubSheetRes(null)}
                disabled={clubSheetSending}
                style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}
              >✕</button>
            </div>

            {/* Description bar */}
            <div style={{
              background: '#fffbeb',
              borderBottom: '1px solid #e5e7eb',
              padding: '10px 20px',
              fontSize: 12,
              color: '#374151',
            }}>
              Sends the full operations sheet to golf club staff — headcount, carts, rental clubs,
              confirmed tee pairings, and organizer contact.
            </div>

            {/* Body */}
            <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontWeight: 600, fontSize: 14, marginBottom: 5 }}>
                  Club Email(s)
                </label>
                <textarea
                  value={clubSheetEmails}
                  onChange={(e) => setClubSheetEmails(e.target.value)}
                  placeholder="e.g. proshop@pinevalley.com events@pinevalley.com"
                  rows={3}
                  disabled={clubSheetSending}
                  style={{
                    width: '100%', boxSizing: 'border-box',
                    border: '1px solid #d1d5db', borderRadius: 8,
                    padding: '9px 12px', fontSize: 13,
                    fontFamily: 'inherit', resize: 'vertical', outline: 'none', color: '#111827',
                  }}
                />
                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 3 }}>
                  Separate multiple addresses with spaces, commas, or newlines.
                </div>
              </div>

              <div style={{ borderTop: '1px solid #f3f4f6', paddingTop: 12 }}>
                <div style={{ fontWeight: 600, fontSize: 13, color: '#6b7280', marginBottom: 10 }}>
                  Your Contact Info (shown at bottom of sheet)
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {[
                    ['Your Name', clubOrgName, setClubOrgName, 'e.g. Jane Smith'],
                    ['Your Email', clubOrgEmail, setClubOrgEmail, 'e.g. jane@example.com'],
                    ['Your Phone', clubOrgPhone, setClubOrgPhone, 'e.g. 555-867-5309'],
                  ].map(([label, val, setter, ph]) => (
                    <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <label style={{ width: 90, fontSize: 13, fontWeight: 500, flexShrink: 0 }}>{label}</label>
                      <input
                        type="text"
                        value={val}
                        onChange={(e) => setter(e.target.value)}
                        placeholder={ph}
                        disabled={clubSheetSending}
                        style={{
                          flex: 1,
                          border: '1px solid #d1d5db', borderRadius: 6,
                          padding: '7px 10px', fontSize: 13,
                          outline: 'none', color: '#111827',
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Feedback */}
              {clubSheetResult && (
                <div style={{
                  padding: '10px 14px', borderRadius: 8,
                  fontSize: 13, fontWeight: 600,
                  background: clubSheetResult.ok ? '#f0fdf4' : '#fef2f2',
                  color: clubSheetResult.ok ? '#166534' : '#dc2626',
                  border: `1px solid ${clubSheetResult.ok ? '#bbf7d0' : '#fecaca'}`,
                }}>
                  {clubSheetResult.message}
                </div>
              )}
            </div>

            {/* Footer */}
            <div style={{ padding: '12px 24px 20px', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                onClick={() => setClubSheetRes(null)}
                disabled={clubSheetSending}
                style={outlineBtnStyle}
              >
                Cancel
              </button>
              <button
                onClick={handleSendClubSheet}
                disabled={clubSheetSending}
                style={{
                  background: clubSheetSending ? '#fcd34d' : '#d97706',
                  color: '#fff', border: 'none',
                  padding: '7px 20px', borderRadius: 6,
                  fontSize: 13, fontWeight: 600,
                  cursor: clubSheetSending ? 'default' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {clubSheetSending ? 'Sending…' : 'Send Club Sheet'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Rule Sheet Modal ── */}
      {ruleSheetRes && (
        <div
          onClick={() => { if (!ruleSheetSending) setRuleSheetRes(null) }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ background: '#fff', borderRadius: 12, width: '100%', maxWidth: 520, boxShadow: '0 20px 60px rgba(0,0,0,0.25)', overflow: 'hidden' }}
          >
            <div style={{ background: '#0891b2', color: '#fff', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>Send Player Information Guide</div>
                <div style={{ fontSize: 12, opacity: 0.85, marginTop: 2 }}>{ruleSheetRes.tournament?.name || 'Tournament'}</div>
              </div>
              <button onClick={() => setRuleSheetRes(null)} disabled={ruleSheetSending} style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>✕</button>
            </div>
            <div style={{ background: '#ecfeff', borderBottom: '1px solid #e5e7eb', padding: '10px 20px', fontSize: 12, color: '#374151' }}>
              Emails the full Player Information Guide — event details, format, conduct rules, and catering info.
            </div>
            <div style={{ padding: '20px 24px' }}>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Recipient Emails</label>
              <textarea
                value={ruleSheetEmails}
                onChange={(e) => setRuleSheetEmails(e.target.value)}
                placeholder="e.g. alice@example.com bob@example.com"
                rows={3}
                disabled={ruleSheetSending}
                style={{ width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db', borderRadius: 8, padding: '10px 12px', fontSize: 13, fontFamily: 'inherit', resize: 'vertical', outline: 'none', color: '#111827' }}
              />
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
              {ruleSheetResult && (
                <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, fontSize: 13, fontWeight: 600, background: ruleSheetResult.ok ? '#f0fdf4' : '#fef2f2', color: ruleSheetResult.ok ? '#166534' : '#dc2626', border: `1px solid ${ruleSheetResult.ok ? '#bbf7d0' : '#fecaca'}` }}>
                  {ruleSheetResult.message}
                </div>
              )}
            </div>
            <div style={{ padding: '12px 24px 20px', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button onClick={() => setRuleSheetRes(null)} disabled={ruleSheetSending} style={outlineBtnStyle}>Cancel</button>
              <button
                onClick={async () => {
                  const emails = parseEmails(ruleSheetEmails)
                  if (!emails.length) { setRuleSheetResult({ ok: false, message: 'Please enter at least one email address.' }); return }
                  setRuleSheetSending(true); setRuleSheetResult(null)
                  try {
                    const r = await fetch('http://localhost:8000/email/send-rule-sheet', {
                      method: 'POST', headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ recipients: emails, tournament_meta: ruleSheetRes.tournament || {} })
                    })
                    const d = await r.json()
                    setRuleSheetResult({ ok: d.success, message: d.message })
                    if (d.success) setTimeout(() => setRuleSheetRes(null), 2000)
                  } catch { setRuleSheetResult({ ok: false, message: 'Could not reach the server.' }) }
                  finally { setRuleSheetSending(false) }
                }}
                disabled={ruleSheetSending}
                style={{ background: ruleSheetSending ? '#67e8f9' : '#0891b2', color: '#fff', border: 'none', padding: '7px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: ruleSheetSending ? 'default' : 'pointer' }}
              >
                {ruleSheetSending ? 'Sending…' : 'Send Guide'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── F&B Summary Modal ── */}
      {fnbRes && (
        <div
          onClick={() => { if (!fnbSending) setFnbRes(null) }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ background: '#fff', borderRadius: 12, width: '100%', maxWidth: 520, boxShadow: '0 20px 60px rgba(0,0,0,0.25)', overflow: 'hidden' }}
          >
            <div style={{ background: '#b45309', color: '#fff', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>Send Food &amp; Beverage Summary</div>
                <div style={{ fontSize: 12, opacity: 0.85, marginTop: 2 }}>{fnbRes.tournament?.name || 'Tournament'}</div>
              </div>
              <button onClick={() => setFnbRes(null)} disabled={fnbSending} style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>✕</button>
            </div>
            <div style={{ background: '#fffbeb', borderBottom: '1px solid #e5e7eb', padding: '10px 20px', fontSize: 12, color: '#374151' }}>
              Emails the Banquet Order Sheet to your caterer or venue contact — covers guest count, budget, style, and dietary requirements.
            </div>
            <div style={{ padding: '20px 24px' }}>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Recipient Emails</label>
              <textarea
                value={fnbEmails}
                onChange={(e) => setFnbEmails(e.target.value)}
                placeholder="e.g. catering@venue.com"
                rows={3}
                disabled={fnbSending}
                style={{ width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db', borderRadius: 8, padding: '10px 12px', fontSize: 13, fontFamily: 'inherit', resize: 'vertical', outline: 'none', color: '#111827' }}
              />
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
              {fnbResult && (
                <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, fontSize: 13, fontWeight: 600, background: fnbResult.ok ? '#f0fdf4' : '#fef2f2', color: fnbResult.ok ? '#166534' : '#dc2626', border: `1px solid ${fnbResult.ok ? '#bbf7d0' : '#fecaca'}` }}>
                  {fnbResult.message}
                </div>
              )}
            </div>
            <div style={{ padding: '12px 24px 20px', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button onClick={() => setFnbRes(null)} disabled={fnbSending} style={outlineBtnStyle}>Cancel</button>
              <button
                onClick={async () => {
                  const emails = parseEmails(fnbEmails)
                  if (!emails.length) { setFnbResult({ ok: false, message: 'Please enter at least one email address.' }); return }
                  setFnbSending(true); setFnbResult(null)
                  try {
                    const r = await fetch('http://localhost:8000/email/send-fnb-summary', {
                      method: 'POST', headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ recipients: emails, tournament_meta: fnbRes.tournament || {} })
                    })
                    const d = await r.json()
                    setFnbResult({ ok: d.success, message: d.message })
                    if (d.success) setTimeout(() => setFnbRes(null), 2000)
                  } catch { setFnbResult({ ok: false, message: 'Could not reach the server.' }) }
                  finally { setFnbSending(false) }
                }}
                disabled={fnbSending}
                style={{ background: fnbSending ? '#fcd34d' : '#b45309', color: '#fff', border: 'none', padding: '7px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: fnbSending ? 'default' : 'pointer' }}
              >
                {fnbSending ? 'Sending…' : 'Send Summary'}
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

const regThStyle = {
  padding: '8px 12px',
  textAlign: 'left',
  fontWeight: 600,
  fontSize: 12,
  color: '#374151',
}

const regTdStyle = {
  padding: '8px 12px',
  color: '#111827',
  verticalAlign: 'top',
  fontSize: 13,
}

