import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import Icon from './Icon'

const sections = [
  { label: 'Workspace', items: [
    { label: 'Dashboard', to: '/dashboard', icon: 'dashboard', exact: true },
    { label: 'Learning Hub', to: '/placement-hub', icon: 'book' },
    { label: 'Normal Mode', to: '/placement-hub?mode=normal', icon: 'clipboard', sub: true },
    { label: 'AI Mode', to: '/placement-hub?mode=ai', icon: 'brain', sub: true },
    { label: 'Daily Challenges', to: '/placement-hub?mode=daily', icon: 'calendar', sub: true },
  ] },
  { label: 'Preparation', items: [
    { label: 'Initial Assessment', to: '/assessment', icon: 'clipboard' },
    { label: 'Mock Tests', to: '/placement-hub?mode=ai', icon: 'target' },
    { label: 'Adaptive Practice', to: '/practice', icon: 'chart' },
    { label: 'Coding Practice', to: '/coding', icon: 'clipboard' },
  ] },
  { label: 'AI support', items: [
    { label: 'AI Tutor', to: '/chat', icon: 'message' },
    { label: 'AI Coach', to: '/ai-coach', icon: 'brain' },
    { label: 'AI Practice', to: '/ai-practice', icon: 'brain' },
  ] },
  { label: 'Your progress', items: [
    { label: 'Learning Planner', to: '/learning', icon: 'calendar' },
    { label: 'My Profile', to: '/learning#profile', icon: 'user' },
    { label: 'Gamification', to: '/rewards', icon: 'trophy' },
    { label: 'Company Preparation', to: '/readiness#companies', icon: 'target' },
    { label: 'Placement Readiness', to: '/readiness', icon: 'chart' },
    { label: 'Notifications', to: '/learning#notifications', icon: 'bell', notification: true },
  ] },
]

const titles = {
  '/dashboard': 'Dashboard', '/assessment': 'Initial assessment', '/assessments/history': 'Assessment history',
  '/practice': 'Adaptive practice', '/coding': 'Coding practice', '/placement-hub': 'Learning Hub', '/learning': 'Learning planner',
  '/rewards': 'Gamification', '/readiness': 'Placement readiness', '/chat': 'AI Assistant',
  '/ai-coach': 'AI Coach', '/ai-practice': 'AI practice',
}

export default function AppShell({ user, onLogout, children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('prepwise-sidebar-collapsed') === 'true')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [unread, setUnread] = useState(0)
  const [profileOpen, setProfileOpen] = useState(false)
  const title = useMemo(() => location.pathname.startsWith('/assessment/') && location.pathname.includes('/results')
    ? 'Assessment results' : location.pathname.startsWith('/assessment/') ? 'Timed assessment' : titles[location.pathname] || 'Prepwise', [location.pathname])

  useEffect(() => {
    api('/api/learning/notifications').then(data => setUnread(data.unread_count || 0)).catch(() => setUnread(0))
  }, [location.pathname])
  useEffect(() => { setMobileOpen(false) }, [location.pathname])
  useEffect(() => {
    if (location.hash) window.setTimeout(() => document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 120)
  }, [location.pathname, location.hash])

  function toggleSidebar() {
    setCollapsed(value => { localStorage.setItem('prepwise-sidebar-collapsed', String(!value)); return !value })
  }
  async function logout() {
    await api('/api/auth/logout', { method: 'POST' }).catch(() => {})
    onLogout()
    navigate('/login', { replace: true })
  }
  const navContent = <>
    <div className={`flex h-[68px] items-center border-b border-[var(--line)] ${collapsed ? 'justify-center px-3' : 'justify-between px-5'}`}>
      <Link to="/dashboard" className="flex items-center gap-3 overflow-hidden font-bold tracking-tight" title="Prepwise dashboard"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[var(--forest)] text-sm text-white">P</span>{!collapsed && <span className="whitespace-nowrap">prepwise<span className="text-[var(--forest)]">.</span></span>}</Link>
      <button className="hidden rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--surface-soft)] hover:text-[var(--ink)] lg:block" onClick={toggleSidebar} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}><Icon name="chevron" className={collapsed ? '' : 'rotate-180'}/></button>
      <button className="rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--surface-soft)] lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><Icon name="close"/></button>
    </div>
    <nav className="app-scrollbar flex-1 space-y-6 overflow-y-auto px-3 py-5">
      {sections.map(section => <section key={section.label}><p className={`mb-2 px-3 text-[10px] font-semibold uppercase tracking-[.15em] text-[var(--muted)] ${collapsed ? 'sr-only' : ''}`}>{section.label}</p><div className="space-y-1">{section.items.map(item => <NavLink key={item.label} to={item.to} end={item.exact} title={collapsed ? item.label : undefined} className={({ isActive }) => `group flex h-10 items-center gap-3 rounded-lg px-3 text-[13px] transition-colors ${item.sub ? 'ml-3 h-9 text-xs' : ''} ${isActive && (!item.sub || location.search.includes(item.to.split('?')[1] || '')) ? 'bg-[var(--forest-soft)] font-semibold text-[var(--forest)]' : 'text-[var(--muted)] hover:bg-[var(--surface-soft)] hover:text-[var(--ink)]'} ${collapsed ? 'justify-center px-0' : ''}`}><Icon name={item.icon} size={17}/>{!collapsed && <><span className="flex-1 truncate">{item.label}</span>{item.notification && unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-[var(--amber-soft)] px-1 text-[10px] font-bold text-[var(--amber-ink)]">{unread > 9 ? '9+' : unread}</span>}</>}</NavLink>)}</div></section>)}
    </nav>
    {!collapsed && <div className="border-t border-[var(--line)] p-4"><div className="flex items-center gap-3 rounded-xl bg-[var(--surface-soft)] p-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[var(--sage-soft)] text-sm font-semibold text-[var(--forest)]">{user.name.charAt(0).toUpperCase()}</span><div className="min-w-0"><p className="truncate text-sm font-semibold">{user.name}</p><p className="truncate text-xs text-[var(--muted)]">Student account</p></div></div></div>}
  </>

  return <div className="min-h-screen bg-[var(--canvas)] text-[var(--ink)]">
    <aside className={`fixed inset-y-0 left-0 z-40 hidden flex-col border-r border-[var(--line)] bg-[var(--surface)] transition-[width] duration-200 lg:flex ${location.pathname.match(/^\/assessment\/\d+$/) ? '!hidden' : ''} ${collapsed ? 'w-[76px]' : 'w-[258px]'}`}>{navContent}</aside>
    {mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><button aria-label="Close navigation" className="absolute inset-0 bg-black/30" onClick={() => setMobileOpen(false)}/><aside className="relative flex h-full w-[min(84vw,300px)] flex-col border-r border-[var(--line)] bg-[var(--surface)] shadow-xl">{navContent}</aside></div>}
    <div className={`min-h-screen transition-[margin] duration-200 ${location.pathname.match(/^\/assessment\/\d+$/) ? 'lg:ml-0' : collapsed ? 'lg:ml-[76px]' : 'lg:ml-[258px]'}`}>
      <header className="sticky top-0 z-30 border-b border-[var(--line)] bg-[var(--surface)]/95 backdrop-blur"><div className="flex h-[68px] items-center justify-between gap-3 px-4 sm:px-7 lg:px-9">
        <div className="flex min-w-0 items-center gap-3"><button onClick={() => setMobileOpen(true)} className="rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--surface-soft)] lg:hidden" aria-label="Open navigation"><Icon name="menu"/></button><div className="min-w-0"><p className="hidden text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--muted)] sm:block">PREPWISE / STUDENT WORKSPACE</p><h1 className="truncate text-[15px] font-semibold sm:mt-0.5 sm:text-base">{title}</h1></div></div>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3"><button onClick={() => navigate('/learning#notifications')} className="relative rounded-lg p-2 text-[var(--muted)] transition hover:bg-[var(--surface-soft)] hover:text-[var(--ink)]" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}><Icon name="bell"/>{unread > 0 && <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-[var(--amber)] ring-2 ring-[var(--surface)]"/>}</button><div className="relative"><button onClick={() => setProfileOpen(value => !value)} className="flex items-center gap-2 rounded-xl p-1.5 pr-2 transition hover:bg-[var(--surface-soft)]" aria-expanded={profileOpen}><span className="grid h-8 w-8 place-items-center rounded-full bg-[var(--sage-soft)] text-xs font-bold text-[var(--forest)]">{user.name.charAt(0).toUpperCase()}</span><span className="hidden max-w-32 truncate text-sm font-medium sm:inline">{user.name}</span><Icon name="chevron" size={14} className="rotate-90 text-[var(--muted)]"/></button>{profileOpen && <><button className="fixed inset-0 z-40 cursor-default" aria-label="Close profile menu" onClick={() => setProfileOpen(false)}/><div className="absolute right-0 z-50 mt-2 w-52 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-1.5 shadow-lg"><Link onClick={() => setProfileOpen(false)} to="/learning#profile" className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-[var(--ink)] hover:bg-[var(--surface-soft)]"><Icon name="user" size={16}/> My profile</Link><button onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-[var(--danger)] hover:bg-[var(--danger-soft)]"><Icon name="logout" size={16}/> Sign out</button></div></>}</div></div>
      </div></header>
      <main className="min-h-[calc(100vh-68px)]">{children}</main>
    </div>
  </div>
}
