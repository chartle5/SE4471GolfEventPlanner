import React, {useState} from 'react'
import { tournamentState as initial } from '../data/tournament'

export default function PlanTournament(){
  const [form,setForm] = useState({ name: initial.name, date: initial.date, venue: initial.venue })

  function handleChange(e){
    const {name,value} = e.target
    setForm(prev=> ({...prev,[name]: value}))
  }

  function save(e){
    e.preventDefault()
    alert('Saved (mock)')
  }

  return (
    <div>
      <h1>Plan Tournament</h1>
      <div className="muted small">Minimal planner (mock)</div>
      <div style={{height:12}} />

      <form onSubmit={save} style={{maxWidth:640}}>
        <div className="card">
          <label className="small">Tournament Name</label>
          <input name="name" value={form.name} onChange={handleChange} />

          <label className="small">Date</label>
          <input name="date" value={form.date} onChange={handleChange} />

          <label className="small">Venue</label>
          <input name="venue" value={form.venue} onChange={handleChange} />

          <div style={{display:'flex',justifyContent:'flex-end',marginTop:12}}>
            <button className="button">Save</button>
          </div>
        </div>
      </form>
    </div>
  )
}
