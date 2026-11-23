import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

const suggestions = [
  'How should I approach percentage problems?',
  'Explain how a stack differs from a queue.',
  'Give me a simple structure for behavioral interview answers.',
]

export default function AIChatPage() {
  const [sessions, setSessions] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const messagesEnd = useRef(null)

  async function refreshSessions() {
    const data = await api('/api/ai/chat/sessions')
    setSessions(data.sessions)
  }
  useEffect(() => { refreshSessions().catch(err => setError(err.message)).finally(() => setLoading(false)) }, [])
  useEffect(() => { messagesEnd.current?.scrollIntoView({ block: 'end' }) }, [messages, sending])

  async function openSession(id) {
    setError('')
    try {
      const data = await api(`/api/ai/chat/sessions/${id}`)
      setSessionId(id)
      setMessages(data.messages)
    } catch (err) { setError(err.message) }
  }

  function newConversation() {
    setSessionId(null)
    setMessages([])
    setDraft('')
    setError('')
  }

  async function send(event) {
    event?.preventDefault()
    const message = draft.trim()
    if (!message || sending) return
    setSending(true)
    setError('')
    setDraft('')
    try {
      const response = await api('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, message }),
      })
      setSessionId(response.session_id)
      setMessages(current => [...current, response.user_message, response.assistant_message])
      await refreshSessions()
    } catch (err) {
      setDraft(message)
      setError(err.message)
    } finally { setSending(false) }
  }

  return <div className="mx-auto max-w-7xl px-5 py-8 lg:px-8 lg:py-10">
    <div className="mb-5"><p className="text-sm font-semibold text-indigo-600">PREPWISE TUTOR</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">Ask about placement prep.</h1><p className="mt-2 text-sm text-slate-500">Aptitude, reasoning, verbal ability, programming, DSA, and interviews.</p></div>
    <div className="mb-5 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm leading-6 text-indigo-950"><span className="font-semibold">Privacy:</span> your prompt and de-identified recent performance bands are sent to OpenRouter’s free Nemotron endpoint. Exact scores and account identifiers stay in this app. Avoid personal or confidential details. Email addresses, phone numbers, and obvious API keys are removed from prompts when recognized.</div>
    <div className="grid min-h-[620px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm lg:grid-cols-[270px_1fr]">
      <aside className="border-b border-slate-200 bg-slate-50 p-4 lg:border-b-0 lg:border-r"><button onClick={newConversation} className="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700">+ New conversation</button><p className="mb-2 mt-6 text-xs font-semibold uppercase tracking-wide text-slate-400">Recent conversations</p>{loading ? <p className="px-2 py-3 text-sm text-slate-500">Loading…</p> : sessions.length ? <div className="space-y-1">{sessions.map(item => <button key={item.id} onClick={() => openSession(item.id)} className={`w-full rounded-lg px-3 py-2.5 text-left text-sm ${sessionId === item.id ? 'bg-indigo-100 font-medium text-indigo-800' : 'text-slate-600 hover:bg-white'}`}><span className="block truncate">{item.title}</span><span className="mt-1 block text-[11px] text-slate-400">{new Date(item.updated_at).toLocaleDateString()}</span></button>)}</div> : <p className="px-2 py-3 text-sm text-slate-500">Your saved chats will appear here.</p>}</aside>
      <section className="flex min-h-[620px] flex-col">
        <div className="app-scrollbar flex-1 space-y-4 overflow-y-auto p-5 sm:p-7" aria-live="polite">{messages.length ? messages.map(item => <div key={item.id} className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[90%] rounded-2xl px-4 py-3 sm:max-w-[75%] ${item.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-800'}`}><p className="whitespace-pre-wrap text-sm leading-6">{item.content}</p>{item.role === 'assistant' && <p className={`mt-2 text-[10px] font-semibold uppercase tracking-wide ${item.source === 'fallback' ? 'text-amber-700' : 'text-indigo-600'}`}>{item.source === 'fallback' ? 'Local fallback' : 'Nemotron 3 Ultra'}</p>}</div></div>) : <div className="mx-auto mt-12 max-w-lg text-center"><span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-indigo-50 text-xl text-indigo-600">âœ¦</span><h2 className="mt-4 text-xl font-semibold">What are you preparing for?</h2><p className="mt-2 text-sm leading-6 text-slate-500">Your recent subject results provide study context. Your name, email, and account ID are kept in this app.</p><div className="mt-6 grid gap-2">{suggestions.map(item => <button key={item} onClick={() => { setDraft(item) }} className="rounded-xl border border-slate-200 px-4 py-3 text-left text-sm text-slate-600 hover:border-indigo-200 hover:bg-indigo-50">{item}</button>)}</div></div>}{sending && <p className="text-xs text-slate-400">Tutor is thinking…</p>}<div ref={messagesEnd}/></div>
        {error && <p role="alert" className="mx-5 mb-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700 sm:mx-7">{error}</p>}
        <form onSubmit={send} className="border-t border-slate-200 p-4 sm:p-5"><div className="flex items-end gap-3"><textarea value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send() } }} maxLength={2000} rows={2} placeholder="Ask a placement-preparation question…" className="field min-h-12 flex-1 resize-none" /><button disabled={sending || !draft.trim()} className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{sending ? 'Sending…' : 'Send'}</button></div><p className="mt-2 text-right text-[11px] text-slate-400">{draft.length}/2,000 · Shift+Enter for a new line</p></form>
      </section>
    </div>
  </div>
}
