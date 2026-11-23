import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import Icon from '../components/Icon'

function formatTime(seconds) {
  return `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`
}

export default function AssessmentRunner() {
  const { attemptId } = useParams()
  const navigate = useNavigate()
  const [attempt, setAttempt] = useState(null)
  const [questions, setQuestions] = useState([])
  const [current, setCurrent] = useState(0)
  const [remaining, setRemaining] = useState(null)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [markedForReview, setMarkedForReview] = useState([])
  const savePromise = useRef(null)
  const submitPromise = useRef(null)
  const questionsRef = useRef([])
  const viewedQuestionId = useRef(null)

  useEffect(() => {
    api(`/api/assessments/${attemptId}`).then(data => {
      if (data.status === 'completed') {
        navigate(data.result_url, { replace: true })
        return
      }
      setAttempt(data.attempt)
      setQuestions(data.questions)
      questionsRef.current = data.questions
      const elapsed = Math.floor((Date.now() - Date.parse(data.attempt.started_at)) / 1000)
      setRemaining(Math.max(0, data.attempt.duration_seconds - elapsed))
    }).catch(err => setError(err.message))
  }, [attemptId, navigate])

  useEffect(() => {
    const question = questions[current]
    if (!attempt || !question || viewedQuestionId.current === question.id) return
    viewedQuestionId.current = question.id
    api(`/api/assessments/${attemptId}/questions/${question.id}/view`, { method: 'POST' }).catch(err => setError(err.message))
  }, [attempt, attemptId, current, questions])

  const submitAssessment = useCallback(() => {
    if (submitPromise.current) return submitPromise.current
    setSubmitting(true)
    submitPromise.current = (async () => {
      try {
        if (savePromise.current) await savePromise.current
        await api(`/api/assessments/${attemptId}/submit`, { method: 'POST' })
        navigate(`/assessment/${attemptId}/results`, { replace: true })
      } catch (err) {
        setError(err.message)
        setSubmitting(false)
        submitPromise.current = null
      }
    })()
    return submitPromise.current
  }, [attemptId, navigate])

  const submitRef = useRef(submitAssessment)
  submitRef.current = submitAssessment

  useEffect(() => {
    if (!attempt) return undefined
    const tick = () => {
      const elapsed = Math.floor((Date.now() - Date.parse(attempt.started_at)) / 1000)
      const seconds = Math.max(0, attempt.duration_seconds - elapsed)
      setRemaining(seconds)
      if (seconds === 0) submitRef.current()
    }
    tick()
    const timer = window.setInterval(tick, 1000)
    return () => window.clearInterval(timer)
  }, [attempt])

  async function chooseOption(question, optionIndex) {
    setError('')
    const updated = questionsRef.current.map(item => item.id === question.id ? { ...item, selected_option: optionIndex } : item)
    questionsRef.current = updated
    setQuestions(updated)
    setSaving(true)
    const previousSave = savePromise.current
    const request = (async () => {
      if (previousSave) await previousSave.catch(() => {})
      return api(`/api/assessments/${attemptId}/answers`, {
        method: 'PUT',
        body: JSON.stringify({ question_id: question.id, selected_option: optionIndex }),
      })
    })()
    savePromise.current = request
    try { await request }
    catch (err) { setError(err.message) }
    finally {
      if (savePromise.current === request) {
        savePromise.current = null
        setSaving(false)
      }
    }
  }

  if (error && !attempt) return <div className="mx-auto max-w-3xl px-5 py-16"><p role="alert" className="rounded-xl bg-rose-50 p-4 text-rose-700">{error}</p><Link to="/assessment" className="mt-5 inline-block text-sm font-semibold text-indigo-600">Back to assessment</Link></div>
  if (!attempt || !questions.length || remaining === null) return <div className="grid min-h-[60vh] place-items-center text-slate-500">Loading assessment…</div>

  const question = questions[current]
  const answered = questions.filter(item => item.selected_option !== null).length
  const isMarked = markedForReview.includes(question?.id)
  function toggleReview(id) { setMarkedForReview(items => items.includes(id) ? items.filter(item => item !== id) : [...items, id]) }
  const finish = () => {
    if (window.confirm(`Submit your assessment? ${answered} of ${questions.length} questions answered.`)) submitAssessment()
  }

  return <div className="mx-auto max-w-6xl px-5 py-8 lg:px-8 lg:py-10">
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm font-medium text-indigo-600">{attempt.assessment_mode === 'ai' ? `AI ASSESSMENT · ${attempt.assessment_category}` : 'INITIAL SKILL ASSESSMENT'}</p><h1 className="mt-1 text-2xl font-semibold">Question {current + 1} <span className="font-normal text-slate-400">of {questions.length}</span></h1></div><div className={`rounded-xl border px-4 py-2.5 text-sm font-semibold tabular-nums ${remaining < 120 ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-slate-200 bg-white text-slate-700'}`} aria-live="polite">Time remaining&nbsp; {formatTime(remaining)}</div></div>
    <div className="mb-5 h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-indigo-600 transition-all" style={{ width: `${(answered / questions.length) * 100}%` }} /></div>
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><div className="mb-5 flex flex-wrap items-center justify-between gap-3"><span className="inline-flex rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700">{question.subject}</span><button onClick={() => toggleReview(question.id)} className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-semibold transition ${isMarked ? 'border-amber-300 bg-amber-50 text-amber-800' : 'border-slate-200 text-slate-600 hover:bg-slate-50'}`}><Icon name="bookmark" size={14}/>{isMarked ? 'Marked for review' : 'Mark for review'}</button></div><h2 className="text-xl font-semibold leading-8">{question.prompt}</h2><div className="mt-7 space-y-3">{question.options.map((option, index) => <button key={option} onClick={() => chooseOption(question, index)} className={`flex w-full items-center gap-4 rounded-xl border p-4 text-left transition ${question.selected_option === index ? 'border-indigo-500 bg-indigo-50 ring-2 ring-indigo-100' : 'border-slate-200 hover:border-indigo-200 hover:bg-slate-50'}`}><span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg text-sm font-semibold ${question.selected_option === index ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'}`}>{String.fromCharCode(65 + index)}</span><span className="text-sm leading-6">{option}</span></button>)}</div>
        {error && <p role="alert" className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}
        <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5"><button onClick={() => setCurrent(value => Math.max(0, value - 1))} disabled={current === 0} className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40">? Previous</button><span className="text-xs text-slate-500">{saving ? 'Saving answer…' : 'Answers save automatically'}</span>{current < questions.length - 1 ? <button onClick={() => setCurrent(value => Math.min(questions.length - 1, value + 1))} className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700">Next question →</button> : <button onClick={finish} disabled={submitting || saving} className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{submitting ? 'Submitting…' : 'Submit assessment'}</button>}</div>
      </section>
      <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-5"><div className="flex items-center justify-between"><h2 className="font-semibold">Questions</h2><span className="text-xs text-slate-500">{answered}/{questions.length} answered</span></div><div className="mt-4 grid grid-cols-5 gap-2">{questions.map((item, index) => { const marked = markedForReview.includes(item.id); return <button key={item.id} onClick={() => setCurrent(index)} aria-label={`Go to question ${index + 1}${marked ? ', marked for review' : ''}`} aria-current={current === index ? 'step' : undefined} className={`relative grid aspect-square place-items-center rounded-lg border text-sm font-semibold ${current === index ? 'border-indigo-600 bg-indigo-600 text-white' : marked ? 'border-amber-300 bg-amber-50 text-amber-800' : item.selected_option !== null ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'}`}>{index + 1}{marked && <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-[var(--amber)]"/>}</button> })}</div><div className="mt-5 border-t border-slate-100 pt-4"><button onClick={finish} disabled={submitting || saving} className="w-full rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50">{submitting ? 'Submitting…' : 'Finish assessment'}</button><p className="mt-2 text-center text-xs text-slate-500">Unanswered questions count as incorrect.</p></div></aside>
    </div>
  </div>
}
