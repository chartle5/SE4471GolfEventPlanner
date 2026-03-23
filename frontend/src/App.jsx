import React from 'react'
import { NavLink, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import Dashboard from './pages/Dashboard'
import PlanTournament from './pages/PlanTournament'
import KnowledgeBase from './pages/KnowledgeBase'

export default function App(){
  return (
    <div className="app">
      <Sidebar />
      <div className="content">
        <Topbar />
        <Routes>
          <Route path="/" element={<Dashboard/>} />
          <Route path="/plan" element={<PlanTournament/>} />
          <Route path="/knowledge" element={<KnowledgeBase/>} />
        </Routes>
      </div>
    </div>
  )
}
