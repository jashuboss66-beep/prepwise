import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const features = [
  ['01', 'Build skills that matter', 'Get ready for the roles you want, one focused session at a time.'],
  ['02', 'See your progress clearly', 'A personal workspace for your placement preparation journey.'],
  ['03', 'Make learning a habit', 'Small steps today make interviews feel easier tomorrow.'],
]

export default function AuthPage({ mode, onAuth, setUser }) {
  const isRegister = mode === 'register'
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await onAuth(isRegister ? '/api/auth/register' : '/api/auth/login', form)
      setUser(result.user)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return <div className="min-h-screen bg-white lg:grid lg:grid-cols-[1.03fr_.97fr]">
    <section className="relative hidden overflow-hidden bg-[var(--forest-deep)] px-12 py-12 text-white lg:flex lg:flex-col lg:justify-between xl:px-20">
      <div className="relative flex items-center gap-3 font-bold"><span className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-500 text-lg">P</span> prepwise<span className="text-indigo-400">.</span></div>
      <div className="relative max-w-xl">
        <p className="mb-5 text-sm font-semibold uppercase tracking-[.2em] text-indigo-300">Your next chapter starts here</p>
        <h1 className="text-4xl font-semibold leading-[1.12] tracking-tight xl:text-5xl">Prepare with purpose.<br /><span className="text-indigo-300">Arrive with confidence.</span></h1>
        <div className="mt-12 space-y-6">{features.map(([number, title, body]) => <div key={number} className="flex gap-4"><span className="pt-0.5 text-xs font-bold tracking-widest text-indigo-300">{number}</span><div><p className="font-semibold">{title}</p><p className="mt-1 text-sm leading-6 text-slate-400">{body}</p></div></div>)}</div>
      </div>
      <p className="relative text-xs text-slate-500">A calmer way to prepare for what’s next.</p>
    </section>
    <section className="flex min-h-screen items-center justify-center px-6 py-12 sm:px-12">
      <div className="w-full max-w-md">
        <Link to="/login" className="mb-12 inline-flex items-center gap-2 font-bold lg:hidden"><span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-white">P</span> prepwise<span className="text-indigo-600">.</span></Link>
        <p className="text-sm font-semibold text-indigo-600">{isRegister ? 'CREATE YOUR ACCOUNT' : 'WELCOME BACK'}</p>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight">{isRegister ? 'Start your journey' : 'Sign in to Prepwise'}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">{isRegister ? 'Create your personal placement preparation workspace.' : 'Pick up where your preparation left off.'}</p>
        <form onSubmit={submit} className="mt-8 space-y-5">
          {isRegister && <label className="block"><span className="mb-2 block text-sm font-medium">Full name</span><input required minLength="2" maxLength="80" autoComplete="name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Alex Morgan" className="field" /></label>}
          <label className="block"><span className="mb-2 block text-sm font-medium">Email address</span><input required type="email" autoComplete="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" className="field" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium">Password</span><input required type="password" minLength={isRegister ? 8 : undefined} autoComplete={isRegister ? 'new-password' : 'current-password'} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder={isRegister ? 'At least 8 characters' : 'Enter your password'} className="field" /></label>
          {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
          <button disabled={busy} className="flex w-full items-center justify-center rounded-xl bg-indigo-600 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/15 transition hover:bg-indigo-700 disabled:opacity-60">{busy ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}<span className="ml-2">→</span></button>
        </form>
        <p className="mt-7 text-center text-sm text-slate-500">{isRegister ? 'Already have an account?' : 'New to Prepwise?'} <Link className="font-semibold text-indigo-600 hover:text-indigo-700" to={isRegister ? '/login' : '/register'}>{isRegister ? 'Sign in' : 'Create an account'}</Link></p>
        <p className="mt-12 text-center text-xs leading-5 text-slate-400">By continuing, you agree to use this local prototype for your personal preparation.</p>
      </div>
    </section>
  </div>
}
