import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import Icon from '../components/Icon'
import Modal from '../components/Modal'

export default function ScheduleDraft() {
  const [schedule, setSchedule] = useState(null)
  const [brochure, setBrochure] = useState(null)
  const [tournament, setTournament] = useState(null)
  const [ruleSheet, setRuleSheet] = useState(null)
  const [fnbSummary, setFnbSummary] = useState(null)
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  // rule sheet email modal
  const [ruleSheetModal, setRuleSheetModal] = useState(false)
  const [ruleSheetEmails, setRuleSheetEmails] = useState('')
  const [ruleSheetSending, setRuleSheetSending] = useState(false)
  const [ruleSheetResult, setRuleSheetResult] = useState(null)
  // F&B email modal
  const [fnbModal, setFnbModal] = useState(false)
  const [fnbEmails, setFnbEmails] = useState('')
  const [fnbSending, setFnbSending] = useState(false)
  const [fnbResult, setFnbResult] = useState(null)
  const { authHeaders } = useAuth()

  const loadFromStorage = useCallback(() => {
    try {
      const s = localStorage.getItem('golfDraftSchedule')
      const b = localStorage.getItem('golfDraftBrochure')
      const t = localStorage.getItem('golfDraftTournament')
      if (s) setSchedule(JSON.parse(s))
      if (b) setBrochure(JSON.parse(b))
      if (t) setTournament(JSON.parse(t))
      const rs = localStorage.getItem('golfDraftRuleSheet')
      const fb = localStorage.getItem('golfDraftFnBSummary')
      if (rs) setRuleSheet(JSON.parse(rs))
      if (fb) setFnbSummary(JSON.parse(fb))
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
      <div className="empty-state" style={{ marginTop: 24 }}>
        <div className="empty-icon"><Icon name="calendar" size={26} /></div>
        <h3>No schedule found</h3>
        <p style={{ margin: 0 }}>Return to the planner and click <strong>Generate Documents</strong> to create a schedule.</p>
      </div>
    )
  }

  const meta = brochure?.meta || {}

  return (
    <div style={{ maxWidth: 820, margin: '0 auto' }}>

      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, var(--forest) 0%, var(--pine) 100%)',
        color: '#fff',
        borderRadius: 'var(--r-md)',
        padding: '24px 30px',
        marginBottom: 22,
      }}>
        <div className="eyebrow" style={{ color: 'var(--champagne)', marginBottom: 6 }}>Schedule Draft</div>
        <h1 style={{ margin: 0, fontSize: 26, color: '#fff' }}>{meta.name || 'Tournament Schedule'}</h1>
        <div style={{ marginTop: 8, opacity: 0.9, fontSize: 14 }}>
          {meta.date && <span>{meta.date}</span>}
          {meta.numberOfDays > 1 && <span> ({meta.numberOfDays} days)</span>}
          {meta.venue && <span> &nbsp;·&nbsp; {meta.venue}</span>}
          {meta.format && <span> &nbsp;·&nbsp; {meta.format}</span>}
          {meta.eventType && <span> &nbsp;·&nbsp; {meta.eventType === 'team' ? `Teams of ${meta.teamSize}` : 'Individual'}</span>}
        </div>
        <div style={{ marginTop: 4, opacity: 0.78, fontSize: 13 }}>
          {meta.playerCount} players &nbsp;·&nbsp; First tee: {meta.teeTimeStart} &nbsp;·&nbsp; {meta.teeTimeInterval}-min intervals
          {meta.registrationDeadline && <span> &nbsp;·&nbsp; Reg. closes: {meta.registrationDeadline}</span>}
          {meta.entryFee > 0 && <span> &nbsp;·&nbsp; Entry: ${meta.entryFee}</span>}
        </div>
      </div>

      {/* Draft banner */}
      <div className="notice notice-warn" style={{ marginBottom: 20 }}>
        <Icon name="clock" size={16} style={{ flexShrink: 0, marginTop: 1 }} />
        <span><strong>Draft</strong> — Return to the planner chat to make changes. This page auto-refreshes when you come back.</span>
      </div>

      {/* Tee Time Table */}
      <div className="card card-flush">
        <div className="card-head">
          <span className="card-title"><Icon name="calendar" size={18} style={{ color: 'var(--fairway)' }} /> Tee Time Schedule</span>
        </div>
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
              {schedule.map((row) => (
                <tr key={row.group}>
                  <td>Group {row.group}</td>
                  <td className="accent">{row.teeTime}</td>
                  <td>{row.players.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Save button */}
      <div style={{ marginTop: 22, display: 'flex', alignItems: 'center', gap: 16 }}>
        {saved ? (
          <div className="notice notice-success" style={{ fontWeight: 600 }}>
            <Icon name="check" size={16} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>Schedule saved! Return to the planner to continue editing, or visit the Reservations page.</span>
          </div>
        ) : (
          <button onClick={handleSave} disabled={saving} className="btn btn-gold">
            {saving ? <><span className="spinner" /> Saving…</> : <><Icon name="check" size={16} /> Save Schedule</>}
          </button>
        )}
      </div>

      {/* Rule Sheet card */}
      {ruleSheet && (
        <div className="card card-flush" style={{ marginTop: 22 }}>
          <div className="card-head">
            <span className="card-title"><Icon name="doc" size={18} style={{ color: 'var(--fairway)' }} /> Player Information Guide</span>
            <button onClick={() => { setRuleSheetModal(true); setRuleSheetEmails(''); setRuleSheetResult(null) }} className="btn btn-sm" style={{ background: 'var(--info)' }}>
              <Icon name="send" size={15} /> Send to Players
            </button>
          </div>
          <div style={{ padding: '14px 22px', fontSize: 13, color: 'var(--slate)' }}>
            <strong>Subject:</strong> {ruleSheet.subject}
          </div>
          <div style={{ margin: '0 22px 18px', background: '#EAF7F4', border: '1px solid #BFE6DE', borderRadius: 'var(--r-sm)', padding: '14px 16px' }}>
            <pre style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0, color: '#14534A', lineHeight: 1.65 }}>
              {ruleSheet.body?.slice(0, 600)}{ruleSheet.body?.length > 600 ? '\n…' : ''}
            </pre>
          </div>
        </div>
      )}

      {/* F&B Summary card */}
      {fnbSummary && (
        <div className="card card-flush" style={{ marginTop: 22 }}>
          <div className="card-head">
            <span className="card-title"><Icon name="food" size={18} style={{ color: 'var(--fairway)' }} /> Food &amp; Beverage Summary</span>
            <button onClick={() => { setFnbModal(true); setFnbEmails(''); setFnbResult(null) }} className="btn btn-sm" style={{ background: 'var(--warn)' }}>
              <Icon name="send" size={15} /> Send to Caterer
            </button>
          </div>
          <div style={{ padding: '14px 22px', fontSize: 13, color: 'var(--slate)' }}>
            <strong>Subject:</strong> {fnbSummary.subject}
          </div>
          <div style={{ margin: '0 22px 18px', background: 'var(--warn-bg)', border: '1px solid var(--warn-bd)', borderRadius: 'var(--r-sm)', padding: '14px 16px' }}>
            <pre style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0, color: '#78350F', lineHeight: 1.65 }}>
              {fnbSummary.body?.slice(0, 600)}{fnbSummary.body?.length > 600 ? '\n…' : ''}
            </pre>
          </div>
        </div>
      )}

      {/* Rule Sheet Email Modal */}
      {ruleSheetModal && (
        <Modal
          title="Send Player Information Guide"
          subtitle={meta.name || 'Tournament'}
          tone="info"
          note="Emails the full Player Information Guide to participants — event details, format, conduct rules, and catering info."
          onClose={() => { if (!ruleSheetSending) setRuleSheetModal(false) }}
          closeDisabled={ruleSheetSending}
          footer={
            <>
              <button onClick={() => setRuleSheetModal(false)} disabled={ruleSheetSending} className="btn btn-ghost btn-sm">Cancel</button>
              <button
                disabled={ruleSheetSending}
                className="btn btn-primary btn-sm"
                onClick={async () => {
                  const emails = ruleSheetEmails.split(/[\s,;]+/).map(e => e.trim()).filter(Boolean)
                  if (!emails.length) { setRuleSheetResult({ ok: false, message: 'Please enter at least one email address.' }); return }
                  setRuleSheetSending(true); setRuleSheetResult(null)
                  try {
                    const r = await fetch('http://localhost:8000/email/send-rule-sheet', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recipients: emails, tournament_meta: tournament || {} }) })
                    const d = await r.json()
                    setRuleSheetResult({ ok: d.success, message: d.message })
                    if (d.success) setTimeout(() => setRuleSheetModal(false), 2000)
                  } catch { setRuleSheetResult({ ok: false, message: 'Could not reach the server.' }) }
                  finally { setRuleSheetSending(false) }
                }}
              >
                {ruleSheetSending ? <><span className="spinner" /> Sending…</> : <><Icon name="send" size={15} /> Send Guide</>}
              </button>
            </>
          }
        >
          <div className="field">
            <label className="field-label">Recipient Emails</label>
            <textarea
              value={ruleSheetEmails}
              onChange={(e) => setRuleSheetEmails(e.target.value)}
              placeholder="e.g. player1@example.com player2@example.com"
              rows={3}
              disabled={ruleSheetSending}
              style={{ resize: 'vertical' }}
            />
            <div style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
          </div>
          {ruleSheetResult && (
            <div className={`notice ${ruleSheetResult.ok ? 'notice-success' : 'notice-danger'}`} style={{ marginTop: 14, fontWeight: 600 }}>
              {ruleSheetResult.message}
            </div>
          )}
        </Modal>
      )}

      {/* F&B Email Modal */}
      {fnbModal && (
        <Modal
          title="Send F&B Summary"
          subtitle={meta.name || 'Tournament'}
          tone="gold"
          note="Emails the Food & Beverage Summary / Banquet Order Sheet to your caterer or venue contact."
          onClose={() => { if (!fnbSending) setFnbModal(false) }}
          closeDisabled={fnbSending}
          footer={
            <>
              <button onClick={() => setFnbModal(false)} disabled={fnbSending} className="btn btn-ghost btn-sm">Cancel</button>
              <button
                disabled={fnbSending}
                className="btn btn-primary btn-sm"
                onClick={async () => {
                  const emails = fnbEmails.split(/[\s,;]+/).map(e => e.trim()).filter(Boolean)
                  if (!emails.length) { setFnbResult({ ok: false, message: 'Please enter at least one email address.' }); return }
                  setFnbSending(true); setFnbResult(null)
                  try {
                    const r = await fetch('http://localhost:8000/email/send-fnb-summary', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recipients: emails, tournament_meta: tournament || {} }) })
                    const d = await r.json()
                    setFnbResult({ ok: d.success, message: d.message })
                    if (d.success) setTimeout(() => setFnbModal(false), 2000)
                  } catch { setFnbResult({ ok: false, message: 'Could not reach the server.' }) }
                  finally { setFnbSending(false) }
                }}
              >
                {fnbSending ? <><span className="spinner" /> Sending…</> : <><Icon name="send" size={15} /> Send Summary</>}
              </button>
            </>
          }
        >
          <div className="field">
            <label className="field-label">Recipient Emails</label>
            <textarea
              value={fnbEmails}
              onChange={(e) => setFnbEmails(e.target.value)}
              placeholder="e.g. catering@venue.com"
              rows={3}
              disabled={fnbSending}
              style={{ resize: 'vertical' }}
            />
            <div style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
          </div>
          {fnbResult && (
            <div className={`notice ${fnbResult.ok ? 'notice-success' : 'notice-danger'}`} style={{ marginTop: 14, fontWeight: 600 }}>
              {fnbResult.message}
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}
