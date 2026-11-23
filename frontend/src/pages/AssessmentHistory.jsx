import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function AssessmentHistory() {
  const [attempts, setAttempts] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api('/api/assessments/history').then(result => setAttempts(result.attempts)).catch(err => setError(err.message)) }, [])

  return <div className="mx-auto max-w-4xl px-5 py-10 lg:px-8 lg:py-14">
    <p className="text-sm font-semibold text-indigo-600">YOUR PRIVATE RECORD</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Assessment history</h1><p className="mt-2 text-slate-500">Every attempt is saved to your account, so you can revisit your results anytime.</p>
    {error && <p role="alert" className="mt-5 rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{error}</p>}
    {!attempts && !error && <p className="mt-8 text-sm text-slate-500">Loading your history…</p>}
    {attempts?.length === 0 && <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center"><p className="font-semibold">No assessments yet</p><p className="mt-2 text-sm text-slate-500">Your first attempt will be saved here.</p><Link to="/assessment" className="mt-5 inline-block rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white">Start assessment</Link></div>}
    {!!attempts?.length && <div className="mt-7 space-y-3">{attempts.map((attempt, index) => <article key={attempt.id} className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center"><div className="flex items-center gap-4"><span className="grid h-11 w-11 place-items-center rounded-xl bg-indigo-50 text-sm font-bold text-indigo-700">{attempts.length - index}</span><div><p className="font-semibold">{new Date(attempt.started_at).toLocaleString()}</p><p className="mt-1 text-sm text-slate-500">{attempt.status === 'completed' ? `${attempt.correct_answers} of ${attempt.total_questions} correct` : 'In progress · answers saved'}</p></div></div><div className="flex items-center gap-4">{attempt.status === 'completed' && <span className="text-xl font-semibold tabular-nums">{attempt.score_percent}%</span>}<Link to={attempt.status === 'completed' ? `/assessment/${attempt.id}/results` : `/assessment/${attempt.id}`} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50">{attempt.status === 'completed' ? 'Review results' : 'Resume attempt'}</Link></div></article>)}</div>}
  </div>
}
