import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

function SourceBadge({ source }) {
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${source === 'nemotron' ? 'bg-indigo-50 text-indigo-700' : 'bg-amber-50 text-amber-800'}`}>{source === 'nemotron' ? 'Nemotron 3 Ultra' : 'Score-based local fallback'}</span>
}

export default function AICoachPage() {
  const [analyses, setAnalyses] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/api/ai/analysis').then(result => {
      setAnalyses(result.analyses)
      if (result.analyses.length) setAnalysis(result.analyses[0])
    }).catch(err => setError(err.message)).finally(() => setLoading(false))
  }, [])

  async function generate() {
    setGenerating(true)
    setError('')
    try {
      const result = await api('/api/ai/analysis', { method: 'POST', body: JSON.stringify({}) })
      setAnalysis(result.analysis)
      setAnalyses(current => [result.analysis, ...current])
    } catch (err) { setError(err.message) }
    finally { setGenerating(false) }
  }

  return <div className="mx-auto max-w-6xl px-5 py-10 lg:px-8 lg:py-14">
    <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><p className="text-sm font-semibold text-indigo-600">PERSONALIZED PLACEMENT COACH</p><h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Turn your results into a plan.</h1><p className="mt-3 max-w-2xl leading-7 text-slate-500">Get a skill-gap review and a practical four-week roadmap based on your saved assessment results.</p></div><div className="flex flex-wrap gap-2"><Link to="/ai-practice" className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700">Practice questions</Link><Link to="/chat" className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700">Ask the tutor</Link></div></div>
    <div className="mt-6 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm leading-6 text-indigo-950"><span className="font-semibold">Privacy:</span> de-identified subject performance bands (Strength, Developing, or Needs focus) are sent to OpenRouter’s free Nemotron endpoint. Exact scores, names, emails, and account IDs stay in this app.</div>
    <div className="mt-6 flex flex-col justify-between gap-4 rounded-2xl bg-[var(--forest-deep)] p-6 text-white sm:flex-row sm:items-center sm:p-7"><div><h2 className="text-lg font-semibold">Your latest completed assessment</h2><p className="mt-1 text-sm text-slate-300">The coach uses stored scores; it does not change or recalculate them.</p></div><button onClick={generate} disabled={generating || loading} className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-indigo-900 hover:bg-indigo-50 disabled:opacity-60">{generating ? 'Building your plan…' : analysis ? 'Generate a fresh analysis' : 'Analyze my results →'}</button></div>
    {error && <div role="alert" className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{error.includes('Complete an assessment') ? <>{error} <Link to="/assessment" className="ml-1 font-semibold underline">Take the assessment</Link></> : error}</div>}
    {loading && <p className="mt-8 text-sm text-slate-500">Loading your saved analyses…</p>}
    {analysis && <>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3"><SourceBadge source={analysis.source} /><span className="text-xs text-slate-500">Assessment #{analysis.attempt_id} · Saved {new Date(analysis.created_at).toLocaleString()}</span></div>
      <section className="mt-4 grid gap-5 lg:grid-cols-[.9fr_1.1fr]"><div className="rounded-2xl border border-slate-200 bg-white p-6"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">COACH SUMMARY</p><p className="mt-3 leading-7 text-slate-700">{analysis.content.summary}</p><h2 className="mt-6 font-semibold">Recorded subject results</h2><div className="mt-3 space-y-3">{analysis.content.actual_scores.map(item => <div key={item.subject}><div className="flex justify-between text-sm"><span>{item.subject}</span><span className="font-semibold">{item.correct_answers}/{item.total_questions} · {item.score_percent}%</span></div><div className="mt-1.5 h-2 rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-500" style={{ width: `${item.score_percent}%` }} /></div></div>)}</div></div>
        <div className="grid gap-4 sm:grid-cols-2"><div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-5"><h2 className="font-semibold text-emerald-900">Strengths</h2>{analysis.content.strengths.length ? analysis.content.strengths.map(item => <div key={item.subject} className="mt-3"><p className="text-sm font-semibold text-emerald-900">{item.subject}</p><p className="mt-1 text-sm leading-6 text-emerald-950">{item.guidance}</p></div>) : <p className="mt-3 text-sm leading-6 text-emerald-950">No subject crossed the current strength threshold. Use the priorities below as your starting point.</p>}</div><div className="rounded-2xl border border-amber-100 bg-amber-50 p-5"><h2 className="font-semibold text-amber-950">Needs more focus</h2>{analysis.content.weaknesses.length ? analysis.content.weaknesses.map(item => <div key={item.subject} className="mt-3"><p className="text-sm font-semibold text-amber-950">{item.subject}</p><p className="mt-1 text-sm leading-6 text-amber-950">{item.guidance}</p></div>) : <p className="mt-3 text-sm leading-6 text-amber-950">No subject fell below the current focus threshold.</p>}</div></div></section>
      <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-6"><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">IMPROVEMENT PRIORITIES</p><div className="mt-4 grid gap-4 md:grid-cols-3">{analysis.content.priorities.map(item => <article key={item.subject} className="rounded-xl bg-slate-50 p-4"><p className="text-xs font-semibold text-indigo-600">PRIORITY {item.rank} · {item.score_percent}%</p><h3 className="mt-2 font-semibold">{item.subject}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{item.guidance}</p><ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-600">{item.activities.map(task => <li key={task}>{task}</li>)}</ul></article>)}</div></section>
      <section className="mt-5"><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">FOUR-WEEK ROADMAP</p><div className="mt-3 grid gap-4 sm:grid-cols-2">{analysis.content.roadmap.map(week => <article key={week.week} className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-xs font-semibold text-indigo-600">WEEK {week.week}</p><h2 className="mt-2 font-semibold">{week.focus}</h2><ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-600">{week.activities.map(task => <li key={task}>{task}</li>)}</ul></article>)}</div></section>
    </>}
    {!loading && !analysis && !error && <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center"><p className="font-semibold">Complete an assessment to build your plan</p><Link to="/assessment" className="mt-4 inline-block rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white">Go to assessment</Link></div>}
    {analyses.length > 1 && <section className="mt-9"><h2 className="font-semibold">Saved analysis history</h2><div className="mt-3 flex flex-wrap gap-2">{analyses.slice(1).map(item => <button key={item.id} onClick={() => setAnalysis(item)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:border-indigo-300">{new Date(item.created_at).toLocaleDateString()} · Attempt #{item.attempt_id}</button>)}</div></section>}
  </div>
}
