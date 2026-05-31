import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Icon from '../components/Icon'
import Modal from '../components/Modal'
import ConfirmDialog from '../components/ConfirmDialog'
import Toast from '../components/Toast'
import ScheduleEditor from '../components/ScheduleEditor'

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
  const [confirmDelete, setConfirmDelete] = useState(false)

  // Schedule editing (drag & drop / shuffle / seed) + toasts
  const [toast, setToast] = useState(null)
  const [savingOrder, setSavingOrder] = useState(false)
  const [shuffling, setShuffling] = useState(false)
  const [teamRegistrations, setTeamRegistrations] = useState([])
  const [seedModal, setSeedModal] = useState(false)
  const [seedCount, setSeedCount] = useState('')
  const [seedClear, setSeedClear] = useState(false)
  const [seeding, setSeeding] = useState(false)

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
        const r = await fetch(`${import.meta.env.VITE_API_URL}/tournaments/${res.tournament_id}/schedule`)
        if (r.ok) setLiveData(await r.json())
      } catch {}
    }
    fetchLive()
    const timer = setInterval(fetchLive, 15000)
    return () => clearInterval(timer)
  }, [res?.tournament_id])

  // Load registrations so the schedule editor can bundle teammates together.
  async function loadTeamRegistrations() {
    if (!res?.tournament_id) return
    try {
      const r = await fetch(`${import.meta.env.VITE_API_URL}/tournaments/${res.tournament_id}/registrations`, { headers: authHeaders() })
      if (r.ok) {
        const data = await r.json()
        setTeamRegistrations(data.registrations || [])
      }
    } catch { /* non-fatal — editor falls back to all-singles */ }
  }

  useEffect(() => {
    loadTeamRegistrations()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [res?.tournament_id])

  // Map "First Last" → team name for registered team players.
  const teamMap = React.useMemo(() => {
    const map = {}
    for (const reg of teamRegistrations) {
      const team = (reg.team_name || '').trim()
      if (team) map[`${reg.first_name} ${reg.last_name}`] = team
    }
    return map
  }, [teamRegistrations])

  async function refreshSchedule() {
    if (!res?.tournament_id) return
    try {
      const r = await fetch(`${import.meta.env.VITE_API_URL}/tournaments/${res.tournament_id}/schedule`)
      if (r.ok) setLiveData(await r.json())
    } catch { /* ignore */ }
    loadTeamRegistrations()
  }

  async function handleSaveOrder(newSchedule) {
    setSavingOrder(true)
    try {
      const r = await fetch(`${import.meta.env.VITE_API_URL}/tournaments/${res.tournament_id}/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ schedule: newSchedule }),
      })
      const d = await r.json()
      if (r.ok) {
        setLiveData(prev => ({ ...(prev || {}), schedule: d.schedule }))
        setToast({ ok: true, message: 'Tee order saved.' })
        return true
      }
      setToast({ ok: false, message: d.detail || 'Could not save the new order.' })
      return false
    } catch {
      setToast({ ok: false, message: 'Could not reach the server.' })
      return false
    } finally {
      setSavingOrder(false)
    }
  }

  async function handleShuffle() {
    if (shuffling || !res?.tournament_id) return
    setShuffling(true)
    try {
      const r = await fetch(`${import.meta.env.VITE_API_URL}/tournaments/${res.tournament_id}/shuffle`, { method: 'POST' })
      const d = await r.json()
      if (r.ok) {
        setLiveData(prev => ({ ...(prev || {}), schedule: d.schedule }))
        setToast({ ok: true, message: 'Players shuffled.' })
      } else {
        setToast({ ok: false, message: d.detail || 'Shuffle failed.' })
      }
    } catch {
      setToast({ ok: false, message: 'Could not reach the server.' })
    } finally {
      setShuffling(false)
    }
  }

  async function handleSeedPlayers() {
    const count = parseInt(seedCount, 10)
    if (!Number.isInteger(count) || count < 1) {
      setToast({ ok: false, message: 'Enter how many test players to generate.' })
      return
    }
    setSeeding(true)
    try {
      const r = await fetch(`${import.meta.env.VITE_API_URL}/tournaments/${res.tournament_id}/seed-players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ count, clear: seedClear }),
      })
      const d = await r.json()
      if (r.ok) {
        setSeedModal(false)
        setToast({ ok: d.success, message: d.success ? `✅ ${d.created} test player${d.created !== 1 ? 's' : ''} registered successfully` : d.message })
        await refreshSchedule()
      } else {
        setToast({ ok: false, message: d.detail || 'Failed to generate test players.' })
      }
    } catch {
      setToast({ ok: false, message: 'Could not reach the server.' })
    } finally {
      setSeeding(false)
    }
  }

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
        const saveRes = await fetch(`${import.meta.env.VITE_API_URL}/tournaments`, {
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
    await doSend(`${import.meta.env.VITE_API_URL}/email/send-invite`, {
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
    await doSend(`${import.meta.env.VITE_API_URL}/email/send`, {
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
    await doSend(`${import.meta.env.VITE_API_URL}/email/send-rule-sheet`, {
      recipients: recipientList,
      tournament_meta: res.tournament || {},
    })
  }

  async function handleSendFnb() {
    const recipientList = parseEmails(emails)
    if (!recipientList.length) { setSendResult({ ok: false, message: 'Please enter at least one email address.' }); return }
    await doSend(`${import.meta.env.VITE_API_URL}/email/send-fnb-summary`, {
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
      const r = await fetch(`${import.meta.env.VITE_API_URL}/tournaments/${res.tournament_id}/send-club-sheet`, {
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
        `${import.meta.env.VITE_API_URL}/tournaments/${res.tournament_id}/cart-placards`,
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
        `${import.meta.env.VITE_API_URL}/tournaments/${res.tournament_id}/registrations`,
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
    const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
    const updated = stored.filter(r => String(r.id) !== String(id))
    localStorage.setItem('savedReservations', JSON.stringify(updated))
    navigate('/reservations')
  }

  if (notFound) {
    return (
      <div className="empty-state" style={{ marginTop: 24 }}>
        <div className="empty-icon"><Icon name="trophy" size={26} /></div>
        <h3>Tournament not found</h3>
        <p style={{ margin: '6px 0 18px' }}>This reservation may have been deleted.</p>
        <button onClick={() => navigate('/reservations')} className="btn btn-primary">
          <Icon name="arrowLeft" size={16} /> Back to Reservations
        </button>
      </div>
    )
  }

  if (!res) {
    return <div className="muted" style={{ padding: 40, textAlign: 'center' }}>Loading…</div>
  }

  const t = res.tournament || {}
  const displaySchedule = liveData?.schedule || res.schedule || []
  const isFinalized = liveData?.status === 'finalized'
  const totalSlots = liveData?.total_players ?? t.playerCount ?? 0
  const registeredCount = liveData?.players_registered ?? 0
  const remainingSlots = Math.max(0, totalSlots - registeredCount)
  const canEditSchedule = !!res.tournament_id && !isFinalized && displaySchedule.length > 0

  return (
    <div>
      {/* Breadcrumb */}
      <button onClick={() => navigate('/reservations')} className="btn btn-ghost btn-sm" style={{ marginBottom: 14 }}>
        <Icon name="arrowLeft" size={15} /> Reservations
      </button>

      <div className="page-head">
        <h1 className="page-title">{t.name || 'Tournament'}</h1>
        <div className="page-sub" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <span>
            {[t.date, t.venue, t.format].filter(Boolean).join(' · ')}
            {t.playerCount > 0 && <span> · {t.playerCount} players</span>}
          </span>
          {res.tournament_id && <span className="badge badge-dot">Saved to DB</span>}
        </div>
      </div>

      {/* Registration progress */}
      {liveData?.players_registered != null && (
        <div className="notice notice-success" style={{ marginBottom: 18 }}>
          <Icon name="users" size={17} style={{ flexShrink: 0, marginTop: 1 }} />
          <div>
            <strong>Registration: {liveData.players_registered} / {liveData.total_players} players signed up</strong>
            {(res.registration_token || liveData.registration_token) && (
              <div style={{ marginTop: 4, color: 'var(--slate)', fontSize: 12 }}>
                Registration link: {window.location.origin}/player-register/{res.registration_token || liveData.registration_token}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Tee Schedule ── */}
      <div className="card card-flush" style={{ marginBottom: 20 }}>
        <div className="card-head">
          <span className="card-title">
            <Icon name="calendar" size={18} style={{ color: 'var(--fairway)' }} /> Tee Schedule
            {liveData && <span className="badge badge-dot" style={{ marginLeft: 4 }}>Live</span>}
          </span>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={() => openModal('invite')} className="btn btn-sm" style={{ background: 'var(--info)' }}>
              <Icon name="mail" size={15} /> Send Invite
            </button>
            <button onClick={() => openModal('schedule')} className="btn btn-primary btn-sm">
              <Icon name="send" size={15} /> Send Schedule
            </button>
            {res.tournament_id && (
              <>
                <button onClick={openRegistrantsModal} className="btn btn-sm" style={{ background: '#6D4C8A' }}>
                  <Icon name="users" size={15} /> View Registrants
                </button>
                <button onClick={handleDownloadPlacards} disabled={placardLoading} className="btn btn-sm" style={{ background: 'var(--info)' }}>
                  {placardLoading ? <><span className="spinner" /> Generating…</> : <><Icon name="cart" size={15} /> Cart Placards</>}
                </button>
                {!isFinalized && (
                  <button onClick={handleShuffle} disabled={shuffling} className="btn btn-ghost btn-sm">
                    {shuffling ? <><span className="spinner" /> Shuffling…</> : <>Shuffle</>}
                  </button>
                )}
                {!isFinalized && (
                  <button
                    onClick={() => { setSeedModal(true); setSeedCount(String(Math.max(1, remainingSlots))); setSeedClear(false) }}
                    className="btn btn-ghost btn-sm"
                    title="Developer/testing tool — registers synthetic players"
                  >
                    <Icon name="users" size={15} /> Generate Test Players
                  </button>
                )}
              </>
            )}
          </div>
        </div>
        {canEditSchedule ? (
          <div style={{ paddingTop: 16 }}>
            <ScheduleEditor
              schedule={displaySchedule}
              teamMap={teamMap}
              onSave={handleSaveOrder}
              saving={savingOrder}
            />
          </div>
        ) : displaySchedule.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Group</th>
                  <th>Tee Time</th>
                  <th>Players</th>
                </tr>
              </thead>
              <tbody>
                {displaySchedule.map(row => (
                  <tr key={row.group}>
                    <td>Group {row.group}</td>
                    <td className="accent">{row.teeTime}</td>
                    <td>{row.players.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="muted" style={{ padding: 22, fontSize: 13 }}>No schedule data available.</div>
        )}
      </div>

      {/* ── Tournament Brochure ── */}
      {res.brochure && (
        <DocCard icon="mail" title="Tournament Brochure">
          <div style={{ padding: '14px 22px', fontSize: 13, color: 'var(--slate)' }}>
            <strong>Subject:</strong> {res.brochure.subject}
            {res.brochure.to && <div style={{ marginTop: 4 }}><strong>To:</strong> {res.brochure.to}</div>}
          </div>
          <DocPreview tone="neutral">{res.brochure.body}</DocPreview>
        </DocCard>
      )}

      {/* ── Player Information Guide ── */}
      {res.rule_sheet && (
        <DocCard
          icon="doc"
          title="Player Information Guide"
          action={<button onClick={() => openModal('ruleSheet')} className="btn btn-sm" style={{ background: 'var(--info)' }}><Icon name="send" size={15} /> Send to Players</button>}
        >
          <div style={{ padding: '14px 22px', fontSize: 13, color: 'var(--slate)' }}>
            <strong>Subject:</strong> {res.rule_sheet.subject}
          </div>
          <DocPreview tone="teal">
            {res.rule_sheet.body?.slice(0, 800)}{res.rule_sheet.body?.length > 800 ? '\n…' : ''}
          </DocPreview>
        </DocCard>
      )}

      {/* ── F&B Summary ── */}
      {res.fnb_summary && (
        <DocCard
          icon="food"
          title="Food & Beverage Summary"
          action={<button onClick={() => openModal('fnb')} className="btn btn-sm" style={{ background: 'var(--warn)' }}><Icon name="send" size={15} /> Send to Caterer</button>}
        >
          <div style={{ padding: '14px 22px', fontSize: 13, color: 'var(--slate)' }}>
            <strong>Subject:</strong> {res.fnb_summary.subject}
          </div>
          <DocPreview tone="amber">
            {res.fnb_summary.body?.slice(0, 800)}{res.fnb_summary.body?.length > 800 ? '\n…' : ''}
          </DocPreview>
        </DocCard>
      )}

      {/* ── Club Operations Sheet ── */}
      {res.tournament_id && (
        <DocCard
          icon="pin"
          title="Club Operations Sheet"
          action={<button onClick={() => openModal('clubSheet')} className="btn btn-sm" style={{ background: 'var(--warn)' }}><Icon name="send" size={15} /> Send Club Sheet</button>}
        >
          <div style={{ padding: '14px 22px', fontSize: 13, color: 'var(--muted)' }}>
            Full operations document for golf club staff — headcount, carts, rental clubs, confirmed tee pairings, and organizer contact.
          </div>
        </DocCard>
      )}

      {/* Delete */}
      <div style={{ marginTop: 8, paddingTop: 20, borderTop: '1px solid var(--line)', display: 'flex', justifyContent: 'flex-end' }}>
        <button onClick={() => setConfirmDelete(true)} className="btn btn-danger">
          <Icon name="trash" size={16} /> Delete Tournament
        </button>
      </div>

      {confirmDelete && (
        <ConfirmDialog
          title="Delete tournament?"
          message="This removes the saved reservation from this device. This cannot be undone."
          confirmLabel="Delete"
          onConfirm={() => { setConfirmDelete(false); handleDelete() }}
          onCancel={() => setConfirmDelete(false)}
        />
      )}

      {/* ── Modals ── */}

      {toast && <Toast toast={toast} onClose={() => setToast(null)} />}

      {seedModal && (
        <Modal
          title="Generate Test Players"
          subtitle={t.name}
          tone="plum"
          note="Developer/testing tool — registers synthetic players (realistic names, phone numbers, ~15% rental clubs, and team assignment for team events)."
          onClose={() => { if (!seeding) setSeedModal(false) }}
          closeDisabled={seeding}
          footer={
            <>
              <button onClick={() => setSeedModal(false)} disabled={seeding} className="btn btn-ghost btn-sm">Cancel</button>
              <button onClick={handleSeedPlayers} disabled={seeding} className="btn btn-primary btn-sm">
                {seeding ? <><span className="spinner" /> Generating…</> : <><Icon name="users" size={15} /> Generate</>}
              </button>
            </>
          }
        >
          <div className="field" style={{ marginBottom: 14 }}>
            <label className="field-label">How many players?</label>
            <input
              type="number"
              min={1}
              max={remainingSlots || undefined}
              value={seedCount}
              onChange={e => setSeedCount(e.target.value)}
              disabled={seeding}
            />
            <div style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>
              {remainingSlots} open slot{remainingSlots !== 1 ? 's' : ''} remaining.
            </div>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600, color: 'var(--slate)', cursor: 'pointer' }}>
            <input type="checkbox" checked={seedClear} onChange={e => setSeedClear(e.target.checked)} disabled={seeding} />
            Clear existing registrations first
          </label>
        </Modal>
      )}

      {modal === 'invite' && (
        <EmailModal
          title="Send Invite"
          subtitle={t.name}
          tone="info"
          note={`Sends tournament details + a "Register Now" button so players can claim a tee-time slot.${
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
          tone="green"
          note="Sends the full tee-time brochure with all player assignments."
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
          tone="info"
          note="Emails the full Player Information Guide — event details, format, conduct rules, and catering info."
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
          tone="gold"
          note="Emails the Banquet Order Sheet to your caterer or venue contact — covers guest count, budget, style, and dietary requirements."
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
        <Modal
          title="Send Club Operations Sheet"
          subtitle={t.name}
          tone="gold"
          note="Sends the full operations sheet to golf club staff — headcount, carts, rental clubs, confirmed tee pairings, and organizer contact."
          onClose={closeModal}
          closeDisabled={sending}
          footer={<ModalActions sending={sending} onClose={closeModal} onSend={handleSendClubSheet} sendLabel="Send Club Sheet" />}
        >
          <div className="field" style={{ marginBottom: 14 }}>
            <label className="field-label">Club Email(s)</label>
            <textarea
              value={emails}
              onChange={e => setEmails(e.target.value)}
              placeholder="e.g. proshop@venue.com"
              rows={3}
              disabled={sending}
              style={{ resize: 'vertical' }}
            />
            <div style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
          </div>
          <div style={{ borderTop: '1px solid var(--line-soft)', paddingTop: 14 }}>
            <div style={{ fontWeight: 600, fontSize: 12.5, color: 'var(--muted)', marginBottom: 10 }}>Your Contact Info (shown at bottom of sheet)</div>
            {[
              ['Your Name', clubOrgName, setClubOrgName, 'e.g. Jane Smith'],
              ['Your Email', clubOrgEmail, setClubOrgEmail, 'e.g. jane@example.com'],
              ['Your Phone', clubOrgPhone, setClubOrgPhone, 'e.g. 555-867-5309'],
            ].map(([label, val, setter, ph]) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <label style={{ width: 90, fontSize: 13, fontWeight: 500, flexShrink: 0, color: 'var(--slate)' }}>{label}</label>
                <input type="text" value={val} onChange={e => setter(e.target.value)} placeholder={ph} disabled={sending} />
              </div>
            ))}
          </div>
          {sendResult && <div style={{ marginTop: 14 }}><FeedbackBanner result={sendResult} /></div>}
        </Modal>
      )}

      {modal === 'registrants' && (
        <Modal
          title="Registered Players"
          subtitle={t.name}
          tone="plum"
          onClose={() => { if (!registrantsLoading) setModal(null) }}
          maxWidth={820}
          footer={<button onClick={() => setModal(null)} className="btn btn-ghost btn-sm">Close</button>}
        >
          {registrantsLoading && <p className="muted" style={{ textAlign: 'center', padding: '20px 0' }}>Loading…</p>}
          {registrantsData?.error && <p style={{ color: 'var(--danger)', textAlign: 'center' }}>{registrantsData.error}</p>}
          {registrantsData && !registrantsData.error && (
            registrantsData.registrations?.length === 0 ? (
              <div className="empty-state" style={{ border: 'none', padding: '24px 0' }}>
                <div className="empty-icon"><Icon name="users" size={24} /></div>
                <p style={{ margin: 0 }}>No players have registered yet.</p>
              </div>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Name</th>
                      <th>Phone</th>
                      <th>Rental Clubs</th>
                      {registrantsData.event_type === 'team' && <th>Team</th>}
                      <th>Tee Slot</th>
                      <th>Registered At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {registrantsData.registrations.map((reg, i) => (
                      <tr key={reg.registration_id || i}>
                        <td>{i + 1}</td>
                        <td style={{ fontWeight: 600 }}>{reg.first_name} {reg.last_name}</td>
                        <td>{reg.phone_number || '—'}</td>
                        <td>{reg.rental_clubs ? `Yes — ${reg.club_hand === 'left' ? 'Left' : 'Right'} Handed` : 'No'}</td>
                        {registrantsData.event_type === 'team' && <td>{reg.team_name || '—'}</td>}
                        <td>{reg.slot_description || '—'}</td>
                        <td>{reg.registered_at ? new Date(reg.registered_at).toLocaleString() : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </Modal>
      )}
    </div>
  )
}

// ── Shared sub-components ──

function DocCard({ icon, title, action, children }) {
  return (
    <div className="card card-flush" style={{ marginBottom: 20 }}>
      <div className="card-head">
        <span className="card-title">
          <Icon name={icon} size={18} style={{ color: 'var(--fairway)' }} /> {title}
        </span>
        {action}
      </div>
      {children}
    </div>
  )
}

const previewTones = {
  neutral: { background: 'var(--paper)', border: 'var(--line)', color: 'var(--slate)' },
  teal:    { background: '#EAF7F4', border: '#BFE6DE', color: '#14534A' },
  amber:   { background: 'var(--warn-bg)', border: 'var(--warn-bd)', color: '#78350F' },
}

function DocPreview({ tone = 'neutral', children }) {
  const c = previewTones[tone]
  return (
    <div style={{ margin: '0 22px 18px', background: c.background, border: `1px solid ${c.border}`, borderRadius: 'var(--r-sm)', padding: '14px 16px' }}>
      <pre style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0, color: c.color, lineHeight: 1.65 }}>
        {children}
      </pre>
    </div>
  )
}

function EmailModal({ title, subtitle, tone, note, emails, onEmailsChange, sending, sendResult, onClose, onSend, sendLabel }) {
  return (
    <Modal
      title={title}
      subtitle={subtitle}
      tone={tone}
      note={note}
      onClose={onClose}
      closeDisabled={sending}
      footer={<ModalActions sending={sending} onClose={onClose} onSend={onSend} sendLabel={sendLabel} />}
    >
      <div className="field">
        <label className="field-label">Recipient Emails</label>
        <textarea
          value={emails}
          onChange={e => onEmailsChange(e.target.value)}
          placeholder="e.g. alice@example.com bob@example.com"
          rows={3}
          disabled={sending}
          style={{ resize: 'vertical' }}
        />
        <div style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
      </div>
      {sendResult && <div style={{ marginTop: 14 }}><FeedbackBanner result={sendResult} /></div>}
    </Modal>
  )
}

function ModalActions({ sending, onClose, onSend, sendLabel }) {
  return (
    <>
      <button onClick={onClose} disabled={sending} className="btn btn-ghost btn-sm">Cancel</button>
      <button onClick={onSend} disabled={sending} className="btn btn-primary btn-sm">
        {sending ? <><span className="spinner" /> Sending…</> : <><Icon name="send" size={15} /> {sendLabel}</>}
      </button>
    </>
  )
}

function FeedbackBanner({ result }) {
  return (
    <div className={`notice ${result.ok ? 'notice-success' : 'notice-danger'}`} style={{ fontWeight: 600 }}>
      <Icon name={result.ok ? 'check' : 'close'} size={16} style={{ flexShrink: 0, marginTop: 1 }} />
      <span>{result.message}</span>
    </div>
  )
}
