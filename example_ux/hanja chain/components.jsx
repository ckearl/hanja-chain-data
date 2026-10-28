// ── 한자 체인 · shared components ─────────────────────────────
const { useState, useEffect, useRef, Fragment } = React;

// ── Icons (simple geometric SVGs) ────────────────────────────
const Icon = {
  daily: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||22} height={p.s||22} fill="none" stroke="currentColor" strokeWidth={p.w||1.7} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3.5" y="4.5" width="17" height="16" rx="2.5"/><path d="M3.5 9h17M8 2.5v4M16 2.5v4"/>
    </svg>
  ),
  gallery: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||22} height={p.s||22} fill="none" stroke="currentColor" strokeWidth={p.w||1.7} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.6"/>
    </svg>
  ),
  search: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||22} height={p.s||22} fill="none" stroke="currentColor" strokeWidth={p.w||1.7} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>
    </svg>
  ),
  chains: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||22} height={p.s||22} fill="none" stroke="currentColor" strokeWidth={p.w||1.7} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="9" width="8.5" height="6" rx="3"/><rect x="12.5" y="9" width="8.5" height="6" rx="3"/><path d="M9 12h6"/>
    </svg>
  ),
  cards: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||20} height={p.s||20} fill="none" stroke="currentColor" strokeWidth={p.w||1.7} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3.5" y="6.5" width="13" height="14" rx="2.2"/><path d="M7.5 4.2l11 2.6a2 2 0 011.5 2.4l-2.4 10.4"/>
    </svg>
  ),
  flame: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||20} height={p.s||20} fill="currentColor">
      <path d="M12.5 2.2c.4 2.6-1 4-2.4 5.4C8.4 9.2 7 10.8 7 13.4A5.5 5.5 0 0018 13.4c0-2-.9-3.5-1.8-4.6-.3 1-.9 1.6-1.7 1.9.5-2.6-.4-5.5-2-8.5z"/>
    </svg>
  ),
  scroll: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||20} height={p.s||20} fill="none" stroke="currentColor" strokeWidth={p.w||1.6} strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 4h11a2 2 0 012 2v13M6 4a2 2 0 00-2 2v1.5h4M6 4a2 2 0 012 2v11a2 2 0 002 2h7a2 2 0 002-2"/><path d="M10 9h6M10 12.5h6"/>
    </svg>
  ),
  arrow: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||18} height={p.s||18} fill="none" stroke="currentColor" strokeWidth={p.w||1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h13M12.5 6l6 6-6 6"/>
    </svg>
  ),
  chevron: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||16} height={p.s||16} fill="none" stroke="currentColor" strokeWidth={p.w||2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 5l7 7-7 7"/>
    </svg>
  ),
  link: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||16} height={p.s||16} fill="none" stroke="currentColor" strokeWidth={p.w||1.8} strokeLinecap="round" strokeLinejoin="round">
      <rect x="2.5" y="8.5" width="7.5" height="7" rx="3.5"/><rect x="14" y="8.5" width="7.5" height="7" rx="3.5"/><path d="M8 12h8"/>
    </svg>
  ),
  x: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||14} height={p.s||14} fill="none" stroke="currentColor" strokeWidth={p.w||2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 6l12 12M18 6L6 18"/>
    </svg>
  ),
  plus: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||16} height={p.s||16} fill="none" stroke="currentColor" strokeWidth={p.w||2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14"/>
    </svg>
  ),
  spark: (p) => (
    <svg viewBox="0 0 24 24" width={p.s||16} height={p.s||16} fill="currentColor">
      <path d="M12 2l1.6 6.4L20 10l-6.4 1.6L12 18l-1.6-6.4L4 10l6.4-1.6z"/>
    </svg>
  ),
};

// ── Word pill (Korean word, optional hanja under) ────────────
function Pill({ word, hanja, small, onClick, active }) {
  return (
    <button className={'pill' + (active ? ' pill-on' : '') + (small ? ' pill-sm' : '')} onClick={onClick}>
      <span className="pill-w">{word}</span>
      {hanja && <span className="pill-h">{hanja}</span>}
    </button>
  );
}

// ── A character card (used in Gallery / Search) ──────────────
function CharCard({ d, compact, onChain }) {
  return (
    <div className={'card' + (compact ? ' card-compact' : '')}>
      <div className="card-glyph">{d.hanja}</div>
      <div className="card-body">
        <div className="card-reading">{d.reading}</div>
        <div className="card-eng">{d.eng}</div>
        {d.ex && d.ex.length > 0 && (
          <div className="card-pills">
            {d.ex.slice(0, compact ? 2 : 4).map((w, i) => <Pill key={i} word={w} small />)}
            {d.more > 0 && !compact && <span className="more">+{d.more}</span>}
          </div>
        )}
      </div>
      {!compact && onChain && (
        <button className="chain-btn" onClick={onChain} title="Open in Chains">
          <Icon.link s={17} />
        </button>
      )}
    </div>
  );
}

// ── Bottom tab bar ───────────────────────────────────────────
const TABS = [
  { id: 'daily',   label: 'Daily',   icon: Icon.daily },
  { id: 'gallery', label: 'Gallery', icon: Icon.gallery },
  { id: 'search',  label: 'Search',  icon: Icon.search },
  { id: 'chains',  label: 'Chains',  icon: Icon.chains },
];
function TabBar({ tab, setTab }) {
  return (
    <nav className="tabbar">
      {TABS.map(t => {
        const on = t.id === tab;
        return (
          <button key={t.id} className={'tab' + (on ? ' tab-on' : '')} onClick={() => setTab(t.id)}>
            <t.icon s={23} w={on ? 1.9 : 1.7} />
            <span className="tab-label">{t.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

// ── App header (title + small caption) ───────────────────────
function AppHeader({ kr, en, right }) {
  return (
    <header className="app-header">
      <div>
        <div className="app-title">{kr}</div>
        <div className="app-sub">{en}</div>
      </div>
      {right}
    </header>
  );
}

Object.assign(window, { Icon, Pill, CharCard, TabBar, AppHeader, TABS });
