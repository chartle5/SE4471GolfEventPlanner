import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import Dashboard from './pages/Dashboard'
import PlanTournament from './pages/PlanTournament'
import KnowledgeBase from './pages/KnowledgeBase'
import ScheduleDraft from './pages/ScheduleDraft'
import Reservations from './pages/Reservations'
import Login from './pages/Login'
import RegisterAccount from './pages/RegisterAccount'
import PlayerRegister from './pages/PlayerRegister'
import { useAuth } from './context/AuthContext'

function ProtectedLayout() {
  const { isLoggedIn } = useAuth()
  if (!isLoggedIn) return <Navigate to="/login" replace />
  return (
    <div className="app">
      <Sidebar />
      <div className="content">
        <Topbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/plan" element={<PlanTournament />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
          <Route path="/schedule-draft" element={<ScheduleDraft />} />
          <Route path="/reservations" element={<Reservations />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}

export default function App() {
  const { isLoggedIn } = useAuth()
  return (
    <Routes>
      <Route
        path="/login"
        element={isLoggedIn ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/register"
        element={isLoggedIn ? <Navigate to="/" replace /> : <RegisterAccount />}
      />
      {/* Public player registration — no account needed */}
      <Route path="/player-register/:token" element={<PlayerRegister />} />
      {/* all other paths handled by the protected layout */}
      <Route path="/*" element={<ProtectedLayout />} />
    </Routes>
  )
}
