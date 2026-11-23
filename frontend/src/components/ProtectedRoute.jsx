import { Navigate } from 'react-router-dom'

export default function ProtectedRoute({ user, loading, children }) {
  if (loading) return <div className="grid min-h-screen place-items-center text-slate-500">Loading your workspace…</div>
  return user ? children : <Navigate to="/login" replace />
}
