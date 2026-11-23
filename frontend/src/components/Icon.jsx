const paths = {
  dashboard: <><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="5" rx="2"/><rect x="13" y="10" width="8" height="11" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/></>,
  book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></>,
  clipboard: <><rect x="8" y="3" width="8" height="4" rx="1"/><path d="M16 5h2a2 2 0 0 1 2 2v14H4V7a2 2 0 0 1 2-2h2M8 12h8M8 16h8"/></>,
  chart: <><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-5 5"/></>,
  brain: <><path d="M12 18V5a3 3 0 1 0-5.7 1.3 3.5 3.5 0 0 0-1.1 6.6A3.5 3.5 0 0 0 8 19h4Z"/><path d="M12 18V5a3 3 0 1 1 5.7 1.3 3.5 3.5 0 0 1 1.1 6.6A3.5 3.5 0 0 1 16 19h-4Z"/><path d="M8 10h.01M16 10h.01M8 15h.01M16 15h.01"/></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/></>,
  bookmark: <path d="M6 4.5A1.5 1.5 0 0 1 7.5 3h9A1.5 1.5 0 0 1 18 4.5V21l-6-4-6 4V4.5Z"/>,
  trophy: <><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4ZM7 7H4v2a4 4 0 0 0 4 4M17 7h3v2a4 4 0 0 1-4 4"/></>,
  award: <><circle cx="12" cy="8" r="6"/><path d="m8.2 13.3-1.1 8.2L12 19l4.9 2.5-1.1-8.2"/><path d="m9.5 8 1.5 1.5L14.5 6"/></>,
  coins: <><circle cx="8" cy="8" r="6"/><path d="M12.5 4.5A6 6 0 1 1 4.5 12.5M14 14a6 6 0 1 1-8 8"/></>,
  flame: <><path d="M8.5 14.5A3.5 3.5 0 0 0 12 18a3.5 3.5 0 0 0 3.5-3.5c0-1.9-1.3-3.1-2.5-4.5-.3 1.5-1.2 2.2-2 2.5.4-3-1.5-5.5-4-7 0 2.8-2.5 5.1-2.5 8.5A7.5 7.5 0 0 0 12 21a7.5 7.5 0 0 0 7.5-7.5c0-2.5-1.1-4.5-3-6.5"/></>,
  target: <><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></>,
  user: <><path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="8" r="4"/></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
  message: <><path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8A8.5 8.5 0 0 1 8.7 3.9a8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z"/></>,
  menu: <><path d="M4 6h16M4 12h16M4 18h16"/></>,
  chevron: <path d="m9 18 6-6-6-6"/>,
  logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/></>,
  close: <><path d="m18 6-12 12M6 6l12 12"/></>,
}

export default function Icon({ name, size = 18, className = '' }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className={className}>{paths[name] || paths.chart}</svg>
}
