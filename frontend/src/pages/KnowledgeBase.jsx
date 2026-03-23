import React, {useState} from 'react'
import { documents } from '../data/documents'

export default function KnowledgeBase(){
  const [q,setQ] = useState('')
  const filtered = documents.filter(d=> (
    d.title.toLowerCase().includes(q.toLowerCase()) || d.summary.toLowerCase().includes(q.toLowerCase())
  ))

  return (
    <div>
      <h1>Knowledge Base</h1>
      <div className="muted small">Simple document list (mock)</div>
      <div style={{height:12}} />

      <div style={{display:'flex',gap:8,marginBottom:12}}>
        <input placeholder="Search documents" value={q} onChange={e=>setQ(e.target.value)} />
      </div>

      <div className="doc-list">
        {filtered.map(d=> (
          <div key={d.id} className="card">
            <div style={{fontWeight:700}}>{d.title}</div>
            <div className="muted small">{d.summary}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
