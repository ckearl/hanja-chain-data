// ── Screen 3 · Search ────────────────────────────────────────
function Search({ onChain }) {
  const { SEARCH_INDEX, RECENT, SUGGESTED } = window.DATA;
  const [q, setQ] = useState('사');
  const [mode, setMode] = useState('auto'); // auto · hanja · ko · en

  const query = q.trim().toLowerCase();
  const fieldMatch = (d) => {
    const hanja = d.hanja.includes(q);
    const ko = d.sound.includes(q) || d.reading.includes(q) || d.ex.some(e => e.includes(q));
    const en = d.eng.toLowerCase().includes(query);
    if (mode === 'hanja') return hanja;
    if (mode === 'ko') return ko;
    if (mode === 'en') return en;
    return hanja || ko || en;
  };
  const results = query ? SEARCH_INDEX.filter(fieldMatch) : [];

  const chips = [
    { id: 'auto', label: '자동' },
    { id: 'hanja', label: '漢字' },
    { id: 'ko', label: '한국어' },
    { id: 'en', label: 'English' },
  ];

  return (
    <div className="screen">
      <AppHeader kr="검색" en="SEARCH" />

      <div className="searchbar">
        <Icon.search s={19} />
        <input className="searchinput" value={q} onChange={e => setQ(e.target.value)} placeholder="한자, 한국어, or English…" />
        {q && <button className="searchclear" onClick={() => setQ('')}><Icon.x s={14} /></button>}
      </div>

      <div className="modechips">
        {chips.map(c => (
          <button key={c.id} className={'mchip' + (mode === c.id ? ' mchip-on' : '')} onClick={() => setMode(c.id)}>{c.label}</button>
        ))}
      </div>

      {query ? (
        <div className="results">
          <div className="reslabel">{results.length} results · <span className="mono">{q}</span></div>
          <div className="cardlist">
            {results.map((d, i) => <CharCard key={i} d={d} compact onChain={() => onChain(d)} />)}
            {results.length === 0 && <div className="empty">검색 결과가 없어요</div>}
          </div>
        </div>
      ) : (
        <div className="presearch">
          <div className="ps-label">최근 본 한자</div>
          <div className="recent-row">
            {RECENT.map((h, i) => <button key={i} className="recent-glyph" onClick={() => setQ(h)}>{h}</button>)}
          </div>
          <div className="ps-label">추천 검색어</div>
          <div className="sugg-row">
            {SUGGESTED.map((s, i) => (
              <button key={i} className="sugg-chip" onClick={() => setQ(s)}><Icon.spark s={13} /> {s}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
window.Search = Search;
