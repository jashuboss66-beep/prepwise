import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

const initialProfile = { college: '', degree: '', department: '', graduation_year: '', cgpa: '', technical_skills: [], programming_languages: [], preferred_language: '', target_companies: [], target_roles: [], daily_study_target: 60, weekly_study_target: 420 }
const listFields = ['technical_skills', 'programming_languages', 'target_companies', 'target_roles']
const labels = { technical_skills: 'Technical skills', programming_languages: 'Programming languages', target_companies: 'Target companies', target_roles: 'Target job roles' }

function parseList(value) { return value.split(',').map(item => item.trim()).filter(Boolean) }
function listText(value) { return Array.isArray(value) ? value.join(', ') : typeof value === 'string' ? value : '' }
function Field({ label, ...props }) { return <label className="block"><span className="mb-1.5 block text-sm font-medium text-slate-700">{label}</span><input className="field" {...props}/></label> }

export default function LearningHub() {
  const [profile, setProfile] = useState(initialProfile)
  const [plan, setPlan] = useState(null)
  const [missions, setMissions] = useState(null)
  const [goals, setGoals] = useState(null)
  const [notifications, setNotifications] = useState([])
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const profileForm = useMemo(() => ({ ...profile,
    graduation_year: profile.graduation_year ?? '', cgpa: profile.cgpa ?? '',
    technical_skills: listText(profile.technical_skills), programming_languages: listText(profile.programming_languages),
    target_companies: listText(profile.target_companies), target_roles: listText(profile.target_roles) }), [profile])

  async function load() {
    setLoading(true); setError('')
    try {
      const [p, l, m, g, n] = await Promise.all([
        api('/api/learning/profile'), api('/api/learning/plan'), api('/api/learning/missions'),
        api('/api/learning/goals'), api('/api/learning/notifications'),
      ])
      setProfile({ ...initialProfile, ...p.profile }); setPlan(l.plan); setMissions(m.missions); setGoals(g.goals)
      setNotifications(n.notifications); setUnread(n.unread_count)
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function saveProfile(event) {
    event.preventDefault(); setSaving('profile'); setError(''); setNotice('')
    const body = { ...profileForm, graduation_year: profileForm.graduation_year ? Number(profileForm.graduation_year) : null,
      cgpa: profileForm.cgpa === '' ? null : Number(profileForm.cgpa), daily_study_target: Number(profileForm.daily_study_target),
      weekly_study_target: Number(profileForm.weekly_study_target) }
    listFields.forEach(key => { body[key] = parseList(profileForm[key]) })
    try { const result = await api('/api/learning/profile', { method: 'PUT', body: JSON.stringify(body) }); setProfile(result.profile); setNotice('Profile and learning targets saved.') }
    catch (err) { setError(err.message) } finally { setSaving('') }
  }

  async function completeTask(id) {
    setSaving(`task-${id}`); setError('')
    try { const result = await api(`/api/learning/plan/tasks/${id}/complete`, { method: 'POST' }); setPlan(value => ({ ...value, tasks: value.tasks.map(item => item.id === id ? result.task : item) })) }
    catch (err) { setError(err.message) } finally { setSaving('') }
  }

  async function markRead(item) {
    try { await api(`/api/learning/notifications/${item.id}/read`, { method: 'POST' }); setNotifications(values => values.map(row => row.id === item.id ? { ...row, read: true } : row)); setUnread(value => Math.max(0, value - (item.read ? 0 : 1))) }
    catch (err) { setError(err.message) }
  }

  return <div className="mx-auto max-w-7xl px-5 py-9 lg:px-8 lg:py-12">
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-semibold text-indigo-600">PERSONALIZED LEARNING</p><h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Plan your next steps.</h1><p className="mt-2 max-w-2xl leading-7 text-slate-500">Your topics and missions respond to saved assessment answers, practice attempts, and study goals.</p></div><button onClick={load} disabled={loading} className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50">{loading ? 'Refreshing…' : 'Refresh progress'}</button></div>
    {error && <p role="alert" className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</p>}
    {notice && <p role="status" className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p>}
    {loading && <p className="mt-6 rounded-xl bg-white p-6 text-sm text-slate-500">Loading your learning plan and saved progress…</p>}
    {!loading && <>
      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">TODAY · {plan?.date}</p><h2 className="mt-1 text-2xl font-semibold">Your daily learning plan</h2><p className="mt-2 text-sm text-slate-500">{plan?.summary} Estimated {plan?.duration_minutes ?? 0} minutes total.</p></div><Link to="/practice" className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white">Open practice</Link></div>
        {plan?.tasks?.length ? <div className="mt-5 grid gap-3 md:grid-cols-2">{plan.tasks.map((task, index) => <article key={task.id} className={`rounded-xl border p-4 ${task.status === 'completed' ? 'border-emerald-200 bg-emerald-50/60' : 'border-slate-200 bg-slate-50'}`}><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">{task.priority} priority · {task.subject}</p><h3 className="mt-1 font-semibold">{index + 1}. {task.topic}</h3><p className="mt-1 text-sm text-slate-600">{task.activity}</p></div><span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600">{task.difficulty} · {task.duration_minutes} min</span></div><button onClick={() => completeTask(task.id)} disabled={task.status === 'completed' || saving === `task-${task.id}`} className="mt-3 text-sm font-semibold text-indigo-700 disabled:text-emerald-700">{task.status === 'completed' ? 'Completed âœ“' : saving === `task-${task.id}` ? 'Saving…' : 'Mark task complete'}</button></article>)}</div> : <p className="mt-5 text-sm text-slate-500">No tasks are available. Complete an assessment or practice set to build a performance-based plan.</p>}
      </section>

      <section className="mt-6 grid gap-5 lg:grid-cols-2"><div className="rounded-2xl border border-slate-200 bg-white p-6"><div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">DAILY MISSIONS</p><h2 className="mt-1 text-xl font-semibold">Small wins today</h2></div><span className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-semibold text-indigo-700">{missions?.daily?.filter(item => item.completed).length ?? 0}/{missions?.daily?.length ?? 0}</span></div><MissionList items={missions?.daily ?? []}/></div><div className="rounded-2xl border border-slate-200 bg-white p-6"><div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-wide text-violet-600">WEEKLY MISSIONS</p><h2 className="mt-1 text-xl font-semibold">Build a steady routine</h2></div><span className="rounded-full bg-violet-50 px-3 py-1 text-sm font-semibold text-violet-700">{missions?.weekly?.filter(item => item.completed).length ?? 0}/{missions?.weekly?.length ?? 0}</span></div><MissionList items={missions?.weekly ?? []}/></div></section>

      <section className="mt-6 grid gap-5 lg:grid-cols-[1.1fr_.9fr]"><div className="rounded-2xl border border-slate-200 bg-white p-6"><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">GOALS · ACTUAL SAVED ACTIVITY</p><h2 className="mt-1 text-xl font-semibold">Target versus progress</h2>{goals && <div className="mt-5 grid gap-5 sm:grid-cols-2"><GoalCard title="Today" amount={goals.today.minutes} target={goals.targets.daily_minutes} unit="min" percent={goals.daily_progress_percent} footer={`${goals.today.completed_activities} completed assessment/practice activities`} /><GoalCard title="This week" amount={goals.week.minutes} target={goals.targets.weekly_minutes} unit="min" percent={goals.weekly_progress_percent} footer={`${goals.week.active_days} active days · ${goals.week.completed_activities} completed activities`} /></div>}{goals?.daily_history && <div className="mt-5 border-t border-slate-100 pt-4"><div className="flex items-center justify-between"><p className="text-sm font-semibold">Last seven daily goals</p><p className="text-xs text-slate-500">{goals.completed_goals} met · {goals.missed_goals} missed</p></div><div className="mt-3 flex flex-wrap gap-2">{goals.daily_history.map(day => <span key={day.date} title={`${day.actual_minutes}/${day.target_minutes} minutes`} className={`rounded-lg px-2.5 py-1.5 text-xs font-medium ${day.status === 'completed' ? 'bg-emerald-50 text-emerald-700' : day.status === 'missed' ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-800'}`}>{new Date(`${day.date}T00:00:00`).toLocaleDateString(undefined, { weekday: 'short' })} · {day.status === 'completed' ? 'Met' : day.status === 'missed' ? 'Missed' : 'Today'}</span>)}</div></div>}<p className="mt-4 text-xs leading-5 text-slate-500">Study time is estimated from elapsed assessment time and answered practice questions (2 minutes per answer, capped per session). Plan checkmarks track planning tasks separately.</p></div>
        <div id="notifications" className="scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-6"><div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-wide text-amber-600">IN-APP NOTIFICATIONS</p><h2 className="mt-1 text-xl font-semibold">Updates for you</h2></div>{unread > 0 && <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">{unread} new</span>}</div><div className="mt-4 max-h-80 space-y-2 overflow-y-auto">{notifications.length ? notifications.map(item => <article key={item.id} className={`rounded-xl p-3 ${item.read ? 'bg-slate-50' : 'bg-amber-50'}`}><div className="flex justify-between gap-3"><div><p className="text-sm font-semibold">{item.title}</p><p className="mt-1 text-sm text-slate-600">{item.message}</p><p className="mt-1 text-xs text-slate-400">{new Date(item.created_at).toLocaleString()}</p></div>{!item.read && <button onClick={() => markRead(item)} className="shrink-0 self-start text-xs font-semibold text-indigo-700">Mark read</button>}</div></article>) : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No notifications yet. New plans and milestones will appear here.</p>}</div></div></section>

      <form id="profile" onSubmit={saveProfile} className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><div><p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">STUDENT PROFILE</p><h2 className="mt-1 text-2xl font-semibold">Your goals and background</h2><p className="mt-1 text-sm text-slate-500">Your name and email stay in the existing account profile. These additional details help tailor your preparation.</p></div><div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><Field label="College / university" value={profileForm.college} onChange={e => setProfile(p => ({ ...p, college: e.target.value }))} placeholder="University name"/><Field label="Degree" value={profileForm.degree} onChange={e => setProfile(p => ({ ...p, degree: e.target.value }))} placeholder="B.Tech"/><Field label="Department" value={profileForm.department} onChange={e => setProfile(p => ({ ...p, department: e.target.value }))} placeholder="Computer Science"/><Field label="Graduation year" type="number" min="2000" max="2100" value={profileForm.graduation_year} onChange={e => setProfile(p => ({ ...p, graduation_year: e.target.value }))} placeholder="2027"/><Field label="CGPA (0–10)" type="number" step="0.01" min="0" max="10" value={profileForm.cgpa} onChange={e => setProfile(p => ({ ...p, cgpa: e.target.value }))} placeholder="8.2"/><Field label="Preferred programming language" value={profileForm.preferred_language} onChange={e => setProfile(p => ({ ...p, preferred_language: e.target.value }))} placeholder="Python"/>{listFields.map(key => <Field key={key} label={labels[key]} value={profileForm[key]} onChange={e => setProfile(p => ({ ...p, [key]: e.target.value }))} placeholder="Separate entries with commas"/>)}<Field label="Daily study target (minutes)" type="number" min="15" max="1440" value={profileForm.daily_study_target} onChange={e => setProfile(p => ({ ...p, daily_study_target: e.target.value === '' ? '' : Number(e.target.value) }))}/><Field label="Weekly study target (minutes)" type="number" min="15" max="10080" value={profileForm.weekly_study_target} onChange={e => setProfile(p => ({ ...p, weekly_study_target: e.target.value === '' ? '' : Number(e.target.value) }))}/></div><button disabled={saving === 'profile'} className="mt-5 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">{saving === 'profile' ? 'Saving profile…' : 'Save profile and goals'}</button></form>
    </>}
  </div>
}

function MissionList({ items }) { return <div className="mt-4 space-y-3">{items.length ? items.map(item => <article key={item.id} className="rounded-xl bg-slate-50 p-3"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold">{item.title}</p><p className="mt-1 text-xs text-slate-500">{item.description}</p></div><span className="shrink-0 text-xs font-semibold text-amber-700">+{item.reward_xp} XP · {item.reward_coins} coins</span></div><div className="mt-3 flex items-center gap-3"><div className="h-2 flex-1 overflow-hidden rounded-full bg-white"><div className={`h-full rounded-full ${item.completed ? 'bg-emerald-500' : 'bg-indigo-500'}`} style={{ width: `${item.progress_percent}%` }}/></div><span className="text-xs font-medium text-slate-500">{item.progress}/{item.target}</span></div><p className={`mt-1 text-xs font-medium ${item.completed ? 'text-emerald-700' : 'text-slate-400'}`}>{item.completed ? 'Completed and rewarded' : `Expires ${new Date(item.expires_at).toLocaleDateString()}`}</p></article>) : <p className="text-sm text-slate-500">Missions will appear here.</p>}</div> }
function GoalCard({ title, amount, target, unit, percent, footer }) { return <div className="rounded-xl bg-slate-50 p-4"><div className="flex items-end justify-between"><p className="font-semibold">{title}</p><p className="text-sm font-semibold text-indigo-700">{amount} / {target} {unit}</p></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-white"><div className="h-full rounded-full bg-indigo-500" style={{ width: `${percent}%` }}/></div><p className="mt-2 text-xs text-slate-500">{footer}</p></div> }
