import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function CodingPracticePage() {
  const [problems, setProblems] = useState([])
  const [history, setHistory] = useState([])
  const [languages, setLanguages] = useState([{ id: 'python', label: 'Python 3.8' }])
  const [language, setLanguage] = useState('python')
  const [drafts, setDrafts] = useState({})
  const [selectedId, setSelectedId] = useState('')
  const [source, setSource] = useState('')
  const [stdin, setStdin] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const problem = useMemo(() => problems.find(item => item.id === selectedId) || problems[0], [problems, selectedId])

  async function load(selectedLanguage = language) {
    const [catalog, submissions] = await Promise.all([api(`/api/coding/problems?language=${encodeURIComponent(selectedLanguage)}`), api('/api/coding/history')])
    setProblems(catalog.problems)
    setLanguages(catalog.languages || [])
    setHistory(submissions.submissions)
    if (catalog.problems.length) {
      const initial = catalog.problems.find(item => item.id === selectedId) || catalog.problems[0]
      setSelectedId(initial.id)
      setSource(current => current || drafts[`${initial.id}:${selectedLanguage}`] || initial.starter_code)
      setStdin(current => current || initial.sample_input)
    }
  }
  useEffect(() => { load().catch(err => setError(err.message)) }, [])
  function chooseProblem(id) {
    const next = problems.find(item => item.id === id)
    if (problem) setDrafts(value => ({ ...value, [`${problem.id}:${language}`]: source }))
    setSelectedId(id); setSource(drafts[`${id}:${language}`] || next?.starter_code || ''); setStdin(next?.sample_input || ''); setResult(null); setError('')
  }
  async function chooseLanguage(nextLanguage) {
    if (nextLanguage === language) return
    if (problem) setDrafts(value => ({ ...value, [`${problem.id}:${language}`]: source }))
    setLanguage(nextLanguage); setResult(null); setError('')
    setBusy('language')
    try {
      const catalog = await api(`/api/coding/problems?language=${encodeURIComponent(nextLanguage)}`)
      setProblems(catalog.problems)
      const nextProblem = catalog.problems.find(item => item.id === selectedId) || catalog.problems[0]
      setSelectedId(nextProblem.id)
      setSource(drafts[`${nextProblem.id}:${nextLanguage}`] || nextProblem.starter_code)
    } catch (err) { setError(err.message) } finally { setBusy('') }
  }
  async function run(mode) {
    if (!problem) return
    setBusy(mode); setError(''); setResult(null)
    try {
      const response = await api('/api/coding/submit', { method: 'POST', body: JSON.stringify({ problem_id: problem.id, source_code: source, language, mode, stdin }) })
      setResult(response.result)
      if (mode === 'submit') {
        const submissions = await api('/api/coding/history')
        setHistory(submissions.submissions)
      }
    } catch (err) { setError(err.message) } finally { setBusy('') }
  }

  return <div className="mx-auto max-w-[1440px] px-4 py-7 sm:px-7 sm:py-9 xl:px-10">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[.14em] text-[var(--forest)]">CODING PRACTICE · DEMO</p><h2 className="mt-2 text-3xl font-semibold tracking-tight">Solve DSA problems in your language.</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Three original exercises cover arrays, hashing, Kadane’s algorithm, and binary search. Their topic sequence is guided by <a className="font-semibold text-[var(--forest)] underline underline-offset-2" href="https://takeuforward.org/dsa/strivers-a2z-sheet-learn-dsa-a-to-z" target="_blank" rel="noreferrer">Striver’s A2Z DSA Sheet</a>; statements and tests here are original demo content.</p></div><Link to="/readiness" className="text-sm font-semibold text-[var(--forest)]">Readiness analytics →</Link></div>

    {error && <p role="alert" className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{error}</p>}
    {!problem && !error && <p className="mt-7 rounded-xl bg-white p-6 text-sm text-slate-500">Loading coding problems…</p>}
    {problem && <div className="mt-6 grid items-start gap-5 xl:grid-cols-[.8fr_1.2fr]">
      <section className="space-y-5">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6"><div className="flex items-center justify-between gap-3"><h3 className="text-lg font-semibold">Demo problem set</h3><span className="rounded-full bg-[var(--forest-soft)] px-3 py-1 text-xs font-semibold text-[var(--forest)]">{languages.find(item => item.id === language)?.label || language}</span></div><div className="mt-4 space-y-2">{problems.map((item, index) => <button key={item.id} onClick={() => chooseProblem(item.id)} aria-current={problem.id === item.id ? 'true' : undefined} className={`w-full rounded-xl border p-3.5 text-left transition ${problem.id === item.id ? 'border-[var(--forest)] bg-[var(--forest-soft)]' : 'border-slate-200 hover:bg-slate-50'}`}><span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Problem {index + 1} · {item.difficulty}</span><span className="mt-1 block text-sm font-semibold">{item.title}</span><span className="mt-1 block text-xs text-slate-500">{item.topic}</span></button>)}</div></div>
        <article className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-[var(--forest-soft)] px-3 py-1 text-xs font-semibold text-[var(--forest)]">{problem.topic}</span><span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">{problem.difficulty}</span></div><h3 className="mt-4 text-xl font-semibold">{problem.title}</h3><p className="mt-3 text-sm leading-6 text-slate-600">{problem.description}</p><dl className="mt-5 space-y-3 text-sm"><div><dt className="font-semibold">Input</dt><dd className="mt-1 text-slate-600">{problem.input_format}</dd></div><div><dt className="font-semibold">Output</dt><dd className="mt-1 text-slate-600">{problem.output_format}</dd></div><div><dt className="font-semibold">Constraints</dt><dd className="mt-1 text-slate-600">{problem.constraints}</dd></div></dl><div className="mt-5 rounded-xl bg-slate-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Example input</p><pre className="mt-2 overflow-x-auto text-xs leading-5">{problem.sample_input}</pre><p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Example output</p><pre className="mt-1 text-xs">{problem.sample_output}</pre></div><details className="mt-4"><summary className="cursor-pointer text-sm font-semibold text-[var(--forest)]">Need a hint?</summary><p className="mt-2 text-sm leading-6 text-slate-600">{problem.hint}</p></details></article>
      </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="flex flex-wrap items-end justify-between gap-3"><div><h3 className="text-lg font-semibold">Your solution</h3><p className="mt-1 text-xs text-slate-500">Read input from stdin and write the answer to stdout.</p></div><div className="flex flex-wrap items-end gap-2"><label className="text-xs font-semibold text-slate-600">Language<select className="field mt-1 min-w-40" value={language} onChange={e => chooseLanguage(e.target.value)} disabled={Boolean(busy)}>{languages.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><button onClick={() => { setSource(problem.starter_code); setDrafts(value => ({ ...value, [`${problem.id}:${language}`]: problem.starter_code })); setResult(null) }} className="rounded-lg border border-slate-200 px-3 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50">Reset starter</button></div></div><label htmlFor="code-editor" className="sr-only">{language} code editor</label><textarea id="code-editor" spellCheck="false" autoCapitalize="off" autoCorrect="off" value={source} onChange={e => { setSource(e.target.value); setDrafts(value => ({ ...value, [`${problem.id}:${language}`]: e.target.value })) }} className="mt-4 min-h-[360px] w-full resize-y rounded-xl border border-slate-700 bg-[#20251f] p-4 font-mono text-sm leading-6 text-[#f0f0e8] outline-none focus:border-[var(--sage)] focus:ring-2 focus:ring-[var(--sage)]/30" aria-label={`${language} solution editor`}/><div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4"><div className="flex items-center justify-between gap-3"><label htmlFor="stdin-editor" className="text-sm font-semibold text-slate-700">Program input (stdin)</label><button type="button" onClick={() => setStdin(problem.sample_input)} className="text-xs font-semibold text-[var(--forest)]">Use example input</button></div><textarea id="stdin-editor" value={stdin} onChange={event => setStdin(event.target.value)} spellCheck="false" className="mt-3 min-h-24 w-full rounded-lg border border-slate-200 bg-white p-3 font-mono text-xs leading-5 text-slate-800 outline-none focus:border-[var(--forest)] focus:ring-2 focus:ring-[var(--sage)]/30" placeholder="Type the input your program should read from stdin" aria-label="Program standard input" /></div><div className="mt-4 flex flex-wrap gap-3"><button onClick={() => run('custom')} disabled={Boolean(busy)} className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50">{busy === 'custom' ? 'Running…' : 'Run with input'}</button><button onClick={() => run('sample')} disabled={Boolean(busy)} className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50">{busy === 'sample' ? 'Running example…' : 'Run example'}</button><button onClick={() => run('submit')} disabled={Boolean(busy)} className="rounded-lg bg-[var(--forest)] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[var(--forest-deep)] disabled:opacity-50">{busy === 'submit' ? 'Checking tests…' : 'Submit solution'}</button></div><p className="mt-3 text-xs leading-5 text-slate-500">Code is sent to an online sandbox compiler. Hidden cases are checked by the backend and aren’t shown in the problem statement.</p>
        {result && <div className={`mt-5 rounded-xl border p-4 ${result.accepted ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`} role="status" aria-live="polite"><p className="font-semibold">{result.status} {result.accepted ? '· all checks passed' : ''}</p><p className="mt-1 text-sm">{result.mode === 'sample' ? 'Example check' : result.mode === 'custom' ? 'Custom input run' : `${result.passed_tests} of ${result.total_tests} tests passed`}{result.execution_time ? ` · ${result.execution_time}s` : ''}</p>{result.mode === 'custom' && <><p className="mt-3 text-xs font-semibold uppercase tracking-wide">Program output</p><pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-white/80 p-3 font-mono text-xs leading-5">{result.output || '(No output)'}</pre></>}{result.message && (result.mode === 'custom' || !result.accepted) && <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap text-xs leading-5">{result.message}</pre>}{result.reward && <p className="mt-2 text-sm font-semibold text-[var(--forest)]">+{result.reward.xp_earned} XP · +{result.reward.coins_earned} coins for your first accepted solution</p>}</div>}
      </section>
    </div>}

    {!!history.length && <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6"><h3 className="text-lg font-semibold">Your recent submissions</h3><p className="mt-1 text-sm text-slate-500">Only your own saved results are shown.</p><div className="mt-4 divide-y divide-slate-100">{history.slice(0, 8).map(item => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="text-sm font-semibold">{item.title}</p><p className="mt-1 text-xs text-slate-500">{new Date(item.created_at).toLocaleString()} · {item.language}</p></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${item.status === 'Accepted' ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>{item.status} · {item.passed_tests}/{item.total_tests}</span></div>)}</div></section>}
  </div>
}

