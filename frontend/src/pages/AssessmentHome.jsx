import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'

const subjects = [
  ['Aptitude', 'Numbers, percentages, averages, and work problems'],
  ['Logical reasoning', 'Patterns, deductions, directions, and analogies'],
  ['Verbal ability', 'Vocabulary, grammar, and clear communication'],
  ['Technical', 'Core programming, data, and computer science concepts'],
]

export default function AssessmentHome() {
  const [attempts, setAttempts] = useState([])
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api('/api/assessments/history').then(result => setAttempts(result.attempts)).catch(err => setError(err.message)).finally(() => setLoading(false))
  }, [])

  async function start() {
    setStarting(true)
    setError('')
    try {
      const result = await api('/api/assessments', { method: 'POST' })
      navigate(`/assessment/${result.attempt_id}`)
    } catch (err) { setError(err.message); setStarting(false) }
  }

  return <div className="mx-auto max-w-5xl px-5 py-10 lg:px-8 lg:py-14">
    <p className="text-sm font-semibold text-indigo-600">INITIAL SKILL ASSESSMENT</p>
    <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Know where you stand.</h1>
    <p className="mt-3 max-w-2xl leading-7 text-slate-500">Answer a balanced set of multiple-choice questions. Your results show how you did in each subject and what to focus on next.</p>
    <div className="mt-8 grid gap-4 sm:grid-cols-2">{subjects.map(([title, detail], index) => <div key={title} className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-5"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-indigo-50 text-sm font-bold text-indigo-700">0{index + 1}</span><div><h2 className="font-semibold">{title}</h2><p className="mt-1 text-sm leading-6 text-slate-500">{detail}</p><p className="mt-2 text-xs font-medium text-slate-400">5 questions</p></div></div>)}</div>
    <div className="mt-6 flex flex-col justify-between gap-5 rounded-2xl bg-[var(--forest-deep)] p-6 text-white sm:flex-row sm:items-center sm:p-8"><div><p className="text-xl font-semibold">20 questions · 20 minutes</p><p className="mt-2 text-sm text-slate-300">Your answers save automatically. Move between questions and submit when you’re ready.</p></div><button onClick={start} disabled={starting} className="shrink-0 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-indigo-900 hover:bg-indigo-50 disabled:opacity-60">{starting ? 'Preparing…' : 'Start assessment →'}</button></div>
    {error && <p role="alert" className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}
    <section className="mt-10"><div className="flex items-end justify-between"><div><h2 className="text-xl font-semibold">Your attempts</h2><p className="mt-1 text-sm text-slate-500">Only you can view your assessment history.</p></div><Link to="/assessments/history" className="text-sm font-semibold text-indigo-600">Full history →</Link></div>
      {loading ? <p className="mt-5 text-sm text-slate-500">Loading your history…</p> : attempts.length ? <div className="mt-4 space-y-3">{attempts.map(attempt => <div key={attempt.id} className="flex flex-col justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center"><div><p className="font-medium">{new Date(attempt.started_at).toLocaleString()}</p><p className="mt-1 text-xs text-slate-500">{attempt.status === 'completed' ? `${attempt.correct_answers} of ${attempt.total_questions} correct` : 'In progress'}</p></div><Link to={attempt.status === 'completed' ? `/assessment/${attempt.id}/results` : `/assessment/${attempt.id}`} className="text-sm font-semibold text-indigo-600">{attempt.status === 'completed' ? `${attempt.score_percent}% · View results` : 'Resume →'}</Link></div>)}</div> : <p className="mt-4 rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">No attempts yet. Your completed assessments will appear here.</p>}
    </section>
  </div>
}
