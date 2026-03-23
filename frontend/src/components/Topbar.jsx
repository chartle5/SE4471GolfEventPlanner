import React from 'react'
import { Link } from 'react-router-dom'

export default function Topbar(){
  return (
    <div className="topbar">
      <div>
        <h2 style={{margin:0}}>Golf Planner</h2>
      </div>
      <div>
        <Link to="/plan" className="small">Plan</Link>
      </div>
    </div>
  )
}
