// ── 한자 체인 · app shell ─────────────────────────────────────
const ACCENTS = {
  ink:     { hex: '#4f86c6', rgb: '79,134,198',  label: 'ink-blue' },
  celadon: { hex: '#5f9e8f', rgb: '95,158,143',  label: 'celadon' },
  indigo:  { hex: '#6b78d6', rgb: '107,120,214', label: 'indigo' },
  seal:    { hex: '#c2604f', rgb: '194,96,79',   label: 'seal-red' },
};

function tokens(theme, accId) {
  const a = ACCENTS[accId] || ACCENTS.ink;
  const dark = theme === 'dark';
  return {
    '--bg':        dark ? '#0e1014' : '#f3f1ea',
    '--surface':   dark ? '#171a20' : '#ffffff',
    '--surface-2': dark ? '#1d222a' : '#f6f3ec',
    '--surface-3': dark ? '#262c35' : '#ece6da',
    '--border':    dark ? '#2a313a' : '#e6dfd0',
    '--border-2':  dark ? '#3a424d' : '#d8d0bf',
    '--text':      dark ? '#edeff2' : '#1b1d22',
    '--text-2':    dark ? '#9aa1ac' : '#5e636c',
    '--text-3':    dark ? '#646b76' : '#9a9080',
    '--ink':       dark ? '#f4f6f9' : '#23262c',
    '--accent':    a.hex,
    '--accent-rgb': a.rgb,
    '--shadow':    dark ? '0 10px 30px rgba(0,0,0,0.4)' : '0 8px 24px rgba(40,36,28,0.10)',
    '--noise':     dark ? '0.04' : '0.05',
  };
}

function Phone({ initialTab = 'daily', theme = 'dark', accent = 'ink' }) {
  const [tab, setTab] = useState(initialTab);
  const dark = theme === 'dark';
  const onChain = () => setTab('chains');

  return (
    <IOSDevice dark={dark} width={402} height={872}>
      <div className="approot" style={tokens(theme, accent)}>
        <div className="noise" />
        <div className="appscroll" key={tab}>
          {tab === 'daily'   && <Daily setTab={setTab} />}
          {tab === 'gallery' && <Gallery setTab={setTab} onChain={onChain} />}
          {tab === 'search'  && <Search onChain={onChain} />}
          {tab === 'chains'  && <Chains />}
        </div>
        <TabBar tab={tab} setTab={setTab} />
      </div>
    </IOSDevice>
  );
}

window.ACCENTS = ACCENTS;
window.Phone = Phone;
