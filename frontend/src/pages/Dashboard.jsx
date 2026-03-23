import React from 'react'
import { tournamentState } from '../data/tournament'

export default function Dashboard(){
  const t = tournamentState
  return (
    <div>
      <h1 style={{margin:0}}>Dashboard</h1>
      <div className="muted small">Minimal view • mock data only</div>
      <div style={{height:12}} />

      <div className="cards">
        <div className="card">
          <div style={{fontWeight:700}}>{t.name}</div>
          <div className="small muted">{t.date} • {t.venue}</div>
        </div>

        <div className="card">
          <div style={{fontWeight:700}}>{t.playerCount} players</div>
          <div className="small muted">Format: {t.format}</div>
        </div>
      </div>
    </div>
  )
}
