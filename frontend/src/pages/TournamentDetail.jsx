import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function TournamentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { authHeaders } = useAuth()

  const [res, setRes] = useState(null)
  const [liveData, setLiveData] = useState(null)
  const [notFound, setNotFound] = useState(false)

  
  // Shared modal state
  const [modal, setModal] = useState(null) // 'invite'|'schedule'|'ruleSheet'|'fnb'|'clubSheet'|'registrants'
  const [emails, setEmails] = useState('')
  const [clubOrgName, setClubOrgName] = useState('')
  const [clubOrgEmail, setClubOrgEmail] = useState('')
  const [clubOrgPhone, setClubOrgPhone] = useState('')
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState(null)

  // Cart placards
  const [placardLoading, setPlacardLoading] = useState(false)

  // Registrants
  const [registrantsData, setRegistrantsData] = useState(null)
  const [registrantsLoading, setRegistrantsLoading] = useState(false)

  // Load from localStorage
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      const found = stored.find(r => String(r.id) === String(id))
      if (found) setRes(found)
      else setNotFound(true)
    } catch {
      setNotFound(true)
    }
  }, [id])

  // Poll live schedule from DB
  useEffect(() => {
    if (!res?.tournament_id) return
    async function fetchLive() {
      try {
        const r = await fetch(`http://localhost:8000/tournaments/${res.tournament_id}/schedule`)
        if (r.ok) setLiveData(await r.json())
      } catch {}
    }
    fetchLive()
    const timer = setInterval(fetchLive, 15000)
    return () => clearInterval(timer)
  }, [res?.tournament_id])

  function openModal(type) {
    setModal(type)
    setEmails('')
    setSendResult(null)
    setClubOrgName('')
    setClubOrgEmail('')
    setClubOrgPhone('')
  }

  function closeModal() {
    if (sending) return
    setModal(null)
    setSendResult(null)
  }

  function parseEmails(input) {
    return input.split(/[\s,;]+/).map(e => e.trim()).filter(Boolean)
  }

  async function doSend(url, body, useAuth = false) {
    setSending(true)
    setSendResult(null)
    try {
      const headers = { 'Content-Type': 'application/json', ...(useAuth ? authHeaders() : {}) }
      const r = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) })
      const d = await r.json()
      setSendResult({ ok: d.success, message: d.message })
      if (d.success) setTimeout(() => closeModal(), 2000)
    } catch {
      setSendResult({ ok: false, message: 'Could not reach the server. Is the backend running?' })
    } finally {
      setSending(false)
    }
  }

  async function handleSendInvite() {
    const recipientList = parseEmails(emails)
    if (!recipientList.length) { setSendResult({ ok: false, message: 'Please enter at least one email address.' }); return }

    let token = res.registration_token || liveData?.registration_token || ''
    // Lazy-save to DB if no token yet
    if (!token && res.tournament && res.schedule && res.brochure) {
      try {
        const saveRes = await fetch('http://localhost:8000/tournaments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          body: JSON.stringify({ tournament: res.tournament, schedule: res.schedule, brochure: res.brochure }),
        })
        if (saveRes.ok) {
          const saveData = await saveRes.json()
          token = saveData.registration_token
          const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
          const updated = stored.map(r => String(r.id) === String(id)
            ? { ...r, tournament_id: saveData.tournament_id, registration_token: token }
            : r)
          localStorage.setItem('savedReservations', JSON.stringify(updated))
          setRes(prev => ({ ...prev, tournament_id: saveData.tournament_id, registration_token: token }))
        }
      } catch {}
    }

    const registrationLink = token ? `${window.location.origin}/player-register/${token}` : ''
    await doSend('http://localhost:8000/email/send-invite', {
      recipients: recipientList,
      tournament_meta: res.brochure?.meta || res.tournament || {},
      registration_link: registrationLink,
    })
  }

  async function handleSendSchedule() {
    const recipientList = parseEmails(emails)
    if (!recipientList.length) { setSendResult({ ok: false, message: 'Please enter at least one email address.' }); return }
    const displaySchedule = liveData?.schedule || res.schedule || []
    const t = res.tournament || {}
    const meta = res.brochure?.meta || {}
    await doSend('http://localhost:8000/email/send', {
      recipients: recipientList,
      subject: res.brochure?.subject || 'Tournament Schedule',
      body: res.brochure?.body || '',
      schedule: displaySchedule,
      tournament_name: t.name || meta.name || '',
      tournament_date: t.date || meta.date || '',
      tournament_venue: t.venue || meta.venue || '',
      tournament_format: t.format || meta.format || '',
    })
  }

  async function handleSendRuleSheet() {
    const recipientList = parseEmails(emails)
    if (!recipientList.length) { setSendResult({ ok: false, message: 'Please enter at least one email address.' }); return }
    await doSend('http://localhost:8000/email/send-rule-sheet', {
      recipients: recipientList,
      tournament_meta: res.tournament || {},
    })
  }

  async function handleSendFnb() {
    const recipientList = parseEmails(emails)
    if (!recipientList.length) { setSendResult({ ok: false, message: 'Please enter at least one email address.' }); return }
    await doSend('http://localhost:8000/email/send-fnb-summary', {
      recipients: recipientList,
      tournament_meta: res.tournament || {},
    })
  }

  async function handleSendClubSheet() {
    const recipientList = parseEmails(emails)
    if (!recipientList.length) { setSendResult({ ok: false, message: 'Please enter at least one email address.' }); return }
    setSending(true)
    setSendResult(null)
    try {
      const r = await fetch(`http://localhost:8000/tournaments/${res.tournament_id}/send-club-sheet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          emails: recipientList,
          organizer_name: clubOrgName,
          organizer_email: clubOrgEmail,
          organizer_phone: clubOrgPhone,
        }),
      })
      const d = await r.json()
      setSendResult({ ok: d.success, message: d.message })
      if (d.success) setTimeout(() => closeModal(), 2000)
    } catch {
      setSendResult({ ok: false, message: 'Could not reach the server. Is the backend running?' })
    } finally {
      setSending(false)
    }
  }

  async function handleDownloadPlacards() {
    if (placardLoading || !res.tournament_id) return
    setPlacardLoading(true)
    try {
      const response = await fetch(
        `http://localhost:8000/tournaments/${res.tournament_id}/cart-placards`,
        { headers: authHeaders() }
      )
      if (!response.ok) { alert('Failed to generate cart placards.'); return }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const safeName = (res.tournament?.name || 'tournament').replace(/\s+/g, '-').toLowerCase()
      a.href = url
      a.download = `cart-placards-${safeName}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      alert('Could not reach the server.')
    } finally {
      setPlacardLoading(false)
    }
  }

  async function openRegistrantsModal() {
    setModal('registrants')
    setRegistrantsData(null)
    setRegistrantsLoading(true)
    try {
      const r = await fetch(
        `http://localhost:8000/tournaments/${res.tournament_id}/registrations`,
        { headers: authHeaders() }
      )
      if (r.ok) setRegistrantsData(await r.json())
      else setRegistrantsData({ error: 'Failed to load registrations.' })
    } catch {
      setRegistrantsData({ error: 'Could not reach the server.' })
    } finally {
      setRegistrantsLoading(false)
    }
  }

  function handleDelete() {
    if (!window.confirm('Remove this reservation? This cannot be undone.')) return
    const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
    const updated = stored.filter(r => String(r.id) !== String(id))
    localStorage.setItem('savedReservations', JSON.stringify(updated))
    navigate('/reservations')
  }

  if (notFound) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>
        <h2>Tournament not found</h2>
        <p>This reservation may have been deleted.</p>
        <button onClick={() => navigate('/reservations')} style={solidBtn('#2563eb')}>
          Back to Reservations
        </button>
      </div>
    )
  }

  if (!res) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>Loading…</div>
  }

  const t = res.tournament || {}
  const displaySchedule = liveData?.schedule || res.schedule || []

  return (
    <div>
      {/* Breadcrumb */}
      <button
        onClick={() => navigate('/reservations')}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#2563eb', fontSize: 14, fontWeight: 600, padding: 0, marginBottom: 8 }}
      >
        ← Reservations
      </button>

      <h1 style={{ margin: '4px 0 0' }}>{t.name || 'Tournament'}</h1>
      <div className="muted small" style={{ marginBottom: 20 }}>
        {[t.date, t.venue, t.format].filter(Boolean).join(' · ')}
        {t.playerCount > 0 && <span> · {t.playerCount} players</span>}
        {res.tournament_id && (
          <span style={{ marginLeft: 10, background: '#d1fae5', color: '#166534', borderRadius: 4, padding: '1px 7px', fontSize: 11, fontWeight: 600 }}>
            Saved to DB
          </span>
        )}
      </div>

      {/* Registration progress */}
      {liveData?.players_registered != null && (
        <div style={{ marginBottom: 16, padding: '10px 16px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 8, fontSize: 13 }}>
          <strong style={{ color: '#166534' }}>
            Registration: {liveData.players_registered} / {liveData.total_players} players signed up
          </strong>
          {(res.registration_token || liveData.registration_token) && (
            <div style={{ marginTop: 4, color: '#374151', fontSize: 12 }}>
              Registration link: {window.location.origin}/player-register/{res.registration_token || liveData.registration_token}
            </div>
          )}
        </div>
      )}

      {/* ── Tee Schedule ── */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 20 }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <span style={{ fontWeight: 700, fontSize: 15 }}>
            Tee Schedule
            {liveData && (
              <span style={{ fontSize: 11, background: '#d1fae5', color: '#166534', borderRadius: 4, padding: '1px 7px', fontWeight: 500, marginLeft: 8 }}>Live</span>
            )}
          </span>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={() => openModal('invite')} style={actionBtn('#2563eb')}>Send Invite</button>
            <button onClick={() => openModal('schedule')} style={actionBtn('#166534')}>Send Schedule</button>
            {res.tournament_id && (
              <>
                <button onClick={openRegistrantsModal} style={actionBtn('#7c3aed')}>View Registrants</button>
                <button onClick={handleDownloadPlacards} disabled={placardLoading} style={actionBtn('#0369a1')}>
                  {placardLoading ? 'Generating…' : 'Cart Placards'}
                </button>
              </>
            )}
          </div>
        </div>
        {displaySchedule.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ background: '#f9fafb' }}>
                <th style={thStyle}>Group</th>
                <th style={thStyle}>Tee Time</th>
                <th style={thStyle}>Players</th>
              </tr>
            </thead>
            <tbody>
              {displaySchedule.map(row => (
                <tr key={row.group} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={tdStyle}>Group {row.group}</td>
                  <td style={{ ...tdStyle, fontWeight: 600, color: '#166534' }}>{row.teeTime}</td>
                  <td style={tdStyle}>{row.players.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: 20, color: '#9ca3af', fontSize: 13 }}>No schedule data available.</div>
        )}
      </div>

      {/* ── Tournament Brochure ── */}
      {res.brochure && (
        <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 20 }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e7eb', fontWeight: 700, fontSize: 15 }}>
            Tournament Brochure
          </div>
          <div style={{ padding: '12px 20px', fontSize: 13, color: '#374151' }}>
            <strong>Subject:</strong> {res.brochure.subject}
            {res.brochure.to && <div style={{ marginTop: 4 }}><strong>To:</strong> {res.brochure.to}</div>}
          </div>
          <div style={{ margin: '0 20px 16px', background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6, padding: '12px 16px' }}>
            <pre style={{ fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0, color: '#374151', lineHeight: 1.6 }}>
              {res.brochure.body}
            </pre>
          </div>
        </div>
      )}

      {/* ── Player Information Guide ── */}
      {res.rule_sheet && (
        <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 20 }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e7eb', fontWeight: 700, fontSize: 15, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Player Information Guide</span>
            <button onClick={() => openModal('ruleSheet')} style={actionBtn('#0891b2')}>Send to Players</button>
          </div>
          <div style={{ padding: '12px 20px', fontSize: 13, color: '#374151' }}>
            <strong>Subject:</strong> {res.rule_sheet.subject}
          </div>
          <div style={{ margin: '0 20px 16px', background: '#f0fdfa', border: '1px solid #99f6e4', borderRadius: 6, padding: '12px 16px' }}>
            <pre style={{ fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0, color: '#134e4a', lineHeight: 1.6 }}>
              {res.rule_sheet.body?.slice(0, 800)}{res.rule_sheet.body?.length > 800 ? '\n…' : ''}
            </pre>
          </div>
        </div>
      )}

      {/* ── F&B Summary ── */}
      {res.fnb_summary && (
        <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 20 }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e7eb', fontWeight: 700, fontSize: 15, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Food &amp; Beverage Summary</span>
            <button onClick={() => openModal('fnb')} style={actionBtn('#b45309')}>Send to Caterer</button>
          </div>
          <div style={{ padding: '12px 20px', fontSize: 13, color: '#374151' }}>
            <strong>Subject:</strong> {res.fnb_summary.subject}
          </div>
          <div style={{ margin: '0 20px 16px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, padding: '12px 16px' }}>
            <pre style={{ fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0, color: '#78350f', lineHeight: 1.6 }}>
              {res.fnb_summary.body?.slice(0, 800)}{res.fnb_summary.body?.length > 800 ? '\n…' : ''}
            </pre>
          </div>
        </div>
      )}

      {/* ── Club Operations Sheet ── */}
      {res.tournament_id && (
        <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 20 }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e7eb', fontWeight: 700, fontSize: 15, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Club Operations Sheet</span>
            <button onClick={() => openModal('clubSheet')} style={actionBtn('#d97706')}>Send Club Sheet</button>
          </div>
          <div style={{ padding: '12px 20px', fontSize: 13, color: '#6b7280' }}>
            Full operations document for golf club staff — headcount, carts, rental clubs, confirmed tee pairings, and organizer contact.
          </div>
        </div>
      )}

      {/* Delete */}
      <div style={{ marginTop: 8, paddingTop: 20, borderTop: '1px solid #e5e7eb', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={handleDelete}
          style={{ background: 'transparent', border: '1px solid #dc2626', color: '#dc2626', padding: '7px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
        >
          Delete Tournament
        </button>
      </div>

      {/* ── Modals ── */}

      {modal === 'invite' && (
        <EmailModal
          title="Send Invite"
          subtitle={t.name}
          color="#1d4ed8"
          description={`Sends tournament details + a "Register Now" button so players can claim a tee-time slot.${
            !res.registration_token && !liveData?.registration_token
              ? ' ⚠️ No registration link found — make sure you are logged in and the tournament was saved to the database.'
              : ''
          }`}
          emails={emails}
          onEmailsChange={setEmails}
          sending={sending}
          sendResult={sendResult}
          onClose={closeModal}
          onSend={handleSendInvite}
          sendLabel="Send Invite"
        />
      )}

      {modal === 'schedule' && (
        <EmailModal
          title="Send Schedule"
          subtitle={t.name}
          color="#166534"
          description="Sends the full tee-time brochure with all player assignments."
          emails={emails}
          onEmailsChange={setEmails}
          sending={sending}
          sendResult={sendResult}
          onClose={closeModal}
          onSend={handleSendSchedule}
          sendLabel="Send Schedule"
        />
      )}

      {modal === 'ruleSheet' && (
        <EmailModal
          title="Send Player Information Guide"
          subtitle={t.name}
          color="#0891b2"
          description="Emails the full Player Information Guide — event details, format, conduct rules, and catering info."
          emails={emails}
          onEmailsChange={setEmails}
          sending={sending}
          sendResult={sendResult}
          onClose={closeModal}
          onSend={handleSendRuleSheet}
          sendLabel="Send Guide"
        />
      )}

      {modal === 'fnb' && (
        <EmailModal
          title="Send Food & Beverage Summary"
          subtitle={t.name}
          color="#b45309"
          description="Emails the Banquet Order Sheet to your caterer or venue contact — covers guest count, budget, style, and dietary requirements."
          emails={emails}
          onEmailsChange={setEmails}
          sending={sending}
          sendResult={sendResult}
          onClose={closeModal}
          onSend={handleSendFnb}
          sendLabel="Send Summary"
        />
      )}

      {modal === 'clubSheet' && (
        <div
          onClick={closeModal}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
        >
          <div onClick={e => e.stopPropagation()} style={{ background: '#fff', borderRadius: 12, width: '100%', maxWidth: 520, boxShadow: '0 20px 60px rgba(0,0,0,0.25)', overflow: 'hidden' }}>
            <ModalHeader title="Send Club Operations Sheet" subtitle={t.name} color="#d97706" onClose={closeModal} disabled={sending} />
            <div style={{ background: '#fffbeb', borderBottom: '1px solid #e5e7eb', padding: '10px 20px', fontSize: 12, color: '#374151' }}>
              Sends the full operations sheet to golf club staff — headcount, carts, rental clubs, confirmed tee pairings, and organizer contact.
            </div>
            <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={labelStyle}>Club Email(s)</label>
                <textarea
                  value={emails}
                  onChange={e => setEmails(e.target.value)}
                  placeholder="e.g. proshop@venue.com"
                  rows={3}
                  disabled={sending}
                  style={textareaStyle}
                />
                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 3 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
              </div>
              <div style={{ borderTop: '1px solid #f3f4f6', paddingTop: 12 }}>
                <div style={{ fontWeight: 600, fontSize: 13, color: '#6b7280', marginBottom: 10 }}>Your Contact Info (shown at bottom of sheet)</div>
                {[
                  ['Your Name', clubOrgName, setClubOrgName, 'e.g. Jane Smith'],
                  ['Your Email', clubOrgEmail, setClubOrgEmail, 'e.g. jane@example.com'],
                  ['Your Phone', clubOrgPhone, setClubOrgPhone, 'e.g. 555-867-5309'],
                ].map(([label, val, setter, ph]) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <label style={{ width: 90, fontSize: 13, fontWeight: 500, flexShrink: 0 }}>{label}</label>
                    <input
                      type="text"
                      value={val}
                      onChange={e => setter(e.target.value)}
                      placeholder={ph}
                      disabled={sending}
                      style={{ flex: 1, border: '1px solid #d1d5db', borderRadius: 6, padding: '7px 10px', fontSize: 13, outline: 'none', color: '#111827' }}
                    />
                  </div>
                ))}
              </div>
              {sendResult && <FeedbackBanner result={sendResult} />}
            </div>
            <ModalFooter sending={sending} onClose={closeModal} onSend={handleSendClubSheet} sendLabel="Send Club Sheet" color="#d97706" />
          </div>
        </div>
      )}

      {modal === 'registrants' && (
        <div
          onClick={() => { if (!registrantsLoading) setModal(null) }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{ background: '#fff', borderRadius: 12, width: '100%', maxWidth: 820, maxHeight: '80vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 60px rgba(0,0,0,0.25)', overflow: 'hidden' }}
          >
            <ModalHeader title="Registered Players" subtitle={t.name} color="#7c3aed" onClose={() => setModal(null)} />
            <div style={{ overflowY: 'auto', flex: 1, padding: '20px 24px' }}>
              {registrantsLoading && <p style={{ color: '#6b7280', textAlign: 'center' }}>Loading…</p>}
              {registrantsData?.error && <p style={{ color: '#dc2626', textAlign: 'center' }}>{registrantsData.error}</p>}
              {registrantsData && !registrantsData.error && (
                registrantsData.registrations?.length === 0 ? (
                  <p style={{ color: '#6b7280', textAlign: 'center', padding: '24px 0' }}>No players have registered yet.</p>
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
                          <td style={regTdStyle}>{reg.rental_clubs ? `Yes — ${reg.club_hand === 'left' ? 'Left' : 'Right'} Handed` : 'No'}</td>
                          {registrantsData.event_type === 'team' && <td style={regTdStyle}>{reg.team_name || '—'}</td>}
                          <td style={regTdStyle}>{reg.slot_description || '—'}</td>
                          <td style={regTdStyle}>{reg.registered_at ? new Date(reg.registered_at).toLocaleString() : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )
              )}
            </div>
            <div style={{ padding: '12px 24px 20px', display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={() => setModal(null)} style={outlineBtnStyle}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Shared sub-components ──

function EmailModal({ title, subtitle, color, description, emails, onEmailsChange, sending, sendResult, onClose, onSend, sendLabel }) {
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div onClick={e => e.stopPropagation()} style={{ background: '#fff', borderRadius: 12, width: '100%', maxWidth: 520, boxShadow: '0 20px 60px rgba(0,0,0,0.25)', overflow: 'hidden' }}>
        <ModalHeader title={title} subtitle={subtitle} color={color} onClose={onClose} disabled={sending} />
        {description && (
          <div style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb', padding: '10px 20px', fontSize: 12, color: '#374151' }}>
            {description}
          </div>
        )}
        <div style={{ padding: '20px 24px' }}>
          <label style={labelStyle}>Recipient Emails</label>
          <textarea
            value={emails}
            onChange={e => onEmailsChange(e.target.value)}
            placeholder="e.g. alice@example.com bob@example.com"
            rows={3}
            disabled={sending}
            style={textareaStyle}
          />
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
          {sendResult && <div style={{ marginTop: 12 }}><FeedbackBanner result={sendResult} /></div>}
        </div>
        <ModalFooter sending={sending} onClose={onClose} onSend={onSend} sendLabel={sendLabel} color={color} />
      </div>
    </div>
  )
}

function ModalHeader({ title, subtitle, color, onClose, disabled }) {
  return (
    <div style={{ background: color, color: '#fff', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div>
        <div style={{ fontWeight: 700, fontSize: 16 }}>{title}</div>
        {subtitle && <div style={{ fontSize: 12, opacity: 0.8, marginTop: 2 }}>{subtitle}</div>}
      </div>
      <button onClick={onClose} disabled={disabled} style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>✕</button>
    </div>
  )
}

function ModalFooter({ sending, onClose, onSend, sendLabel, color }) {
  return (
    <div style={{ padding: '12px 24px 20px', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
      <button onClick={onClose} disabled={sending} style={outlineBtnStyle}>Cancel</button>
      <button
        onClick={onSend}
        disabled={sending}
        style={{ background: sending ? '#9ca3af' : color, color: '#fff', border: 'none', padding: '7px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: sending ? 'default' : 'pointer' }}
      >
        {sending ? 'Sending…' : sendLabel}
      </button>
    </div>
  )
}

function FeedbackBanner({ result }) {
  return (
    <div style={{ padding: '10px 14px', borderRadius: 8, fontSize: 13, fontWeight: 600, background: result.ok ? '#f0fdf4' : '#fef2f2', color: result.ok ? '#166534' : '#dc2626', border: `1px solid ${result.ok ? '#bbf7d0' : '#fecaca'}` }}>
      {result.message}
    </div>
  )
}

// ── Styles ──
const thStyle = { padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb', fontSize: 12 }
const tdStyle = { padding: '8px 12px', color: '#111827', fontSize: 13 }
const regThStyle = { padding: '8px 12px', textAlign: 'left', fontWeight: 600, fontSize: 12, color: '#374151' }
const regTdStyle = { padding: '8px 12px', color: '#111827', verticalAlign: 'top' }
const outlineBtnStyle = { background: 'transparent', border: '1px solid #6b7280', color: '#374151', padding: '5px 14px', borderRadius: 6, fontSize: 13, cursor: 'pointer', fontWeight: 500 }
const labelStyle = { display: 'block', fontWeight: 600, fontSize: 14, marginBottom: 6 }
const textareaStyle = { width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db', borderRadius: 8, padding: '10px 12px', fontSize: 13, fontFamily: 'inherit', resize: 'vertical', outline: 'none', color: '#111827' }

function actionBtn(color) {
  return { background: color, color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }
}

function solidBtn(color) {
  return { background: color, color: '#fff', border: 'none', padding: '10px 20px', borderRadius: 8, fontWeight: 700, fontSize: 14, cursor: 'pointer' }
}
