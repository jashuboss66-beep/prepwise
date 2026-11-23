import { lazy, Suspense, useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { api } from './api/client'
import AppShell from './components/AppShell'
import ProtectedRoute from './components/ProtectedRoute'
import AuthPage from './pages/AuthPage'
import AssessmentHome from './pages/AssessmentHome'
import AssessmentHistory from './pages/AssessmentHistory'
import AssessmentResult from './pages/AssessmentResult'
import AssessmentRunner from './pages/AssessmentRunner'
import AIChatPage from './pages/AIChatPage'
import AICoachPage from './pages/AICoachPage'
import AiPracticePage from './pages/AiPracticePage'
import Dashboard from './pages/Dashboard'
import PracticeArena from './pages/PracticeArena'
import GamificationPage from './pages/GamificationPage'
import LearningHub from './pages/LearningHub'
import PlacementHub from './pages/PlacementHub'
const CodingPracticePage = lazy(() => import('./pages/CodingPracticePage'))
const ReadinessPage = lazy(() => import('./pages/ReadinessPage'))

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => { api('/api/auth/me').then(result => setUser(result.user)).catch(() => setUser(null)).finally(() => setLoading(false)) }, [])

  async function authenticate(path, form) { return api(path, { method: 'POST', body: JSON.stringify(form) }) }
  const protectedPage = page => <ProtectedRoute user={user} loading={loading}><AppShell user={user} onLogout={() => setUser(null)}>{page}</AppShell></ProtectedRoute>

  return <Routes>
    <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <AuthPage mode="login" onAuth={authenticate} setUser={setUser} />} />
    <Route path="/register" element={user ? <Navigate to="/dashboard" replace /> : <AuthPage mode="register" onAuth={authenticate} setUser={setUser} />} />
    <Route path="/dashboard" element={protectedPage(<Dashboard user={user} message="Your assessment history and preparation tools are ready." />)} />
    <Route path="/assessment" element={protectedPage(<AssessmentHome />)} />
    <Route path="/assessment/:attemptId/results" element={protectedPage(<AssessmentResult />)} />
    <Route path="/assessment/:attemptId" element={protectedPage(<AssessmentRunner />)} />
    <Route path="/assessments/history" element={protectedPage(<AssessmentHistory />)} />
    <Route path="/ai-coach" element={protectedPage(<AICoachPage />)} />
    <Route path="/chat" element={protectedPage(<AIChatPage />)} />
    <Route path="/ai-practice" element={protectedPage(<AiPracticePage />)} />
    <Route path="/practice" element={protectedPage(<PracticeArena />)} />
    <Route path="/coding" element={<Suspense fallback={<div className="mx-auto max-w-7xl px-5 py-12 text-slate-500">Loading coding practice...</div>}>{protectedPage(<CodingPracticePage />)}</Suspense>} />
    <Route path="/rewards" element={protectedPage(<GamificationPage />)} />
    <Route path="/learning" element={protectedPage(<LearningHub />)} />
    <Route path="/placement-hub" element={protectedPage(<PlacementHub />)} />
    <Route path="/readiness" element={<Suspense fallback={<div className="mx-auto max-w-7xl px-5 py-12 text-slate-500">Loading readiness analytics...</div>}>{protectedPage(<ReadinessPage />)}</Suspense>} />
    <Route path="*" element={<Navigate to={user ? '/dashboard' : '/login'} replace />} />
  </Routes>
}
