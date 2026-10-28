// ── Screen 2 · Gallery (cumulative pinned filters) ───────────
function Gallery({ setTab, onChain }) {
  const { GALLERY, CONSONANTS, VOWELS, decompose } = window.DATA;
  const [cho, setCho] = useState(null);
  const [jung, setJung] = useState(null);
  const [syl, setSyl] = useState(null);

  // cumulative removal
  const clearCho = () => { setCho(null); setJung(null); setSyl(null); };
  const clearJung = () => { setJung(null); setSyl(null); };
  const clearSyl = () => setSyl(null);
  const pickCho = (c) => { setCho(c); setJung(null); setSyl(null); };
  const pickJung = (v) => { setJung(v); setSyl(null); };

  const matchCho = (g) => !cho || decompose(g.sound).cho === cho;
  const matchJung = (g) => !jung || decompose(g.sound).jung === jung;
  const matchSyl = (g) => !syl || g.sound === syl;

  const results = GALLERY.filter(g => matchCho(g) && matchJung(g) && matchSyl(g));

  // syllables present for current cho+jung
  const syllables = jung
    ? [...new Set(GALLERY.filter(g => matchCho(g) && matchJung(g)).map(g => g.sound))]
    : [];

  return (
    <div className="screen">
      <AppHeader kr="서랍" en={`GALLERY · ${GALLERY.length} saved`} />

      {/* pinned filter trail */}
      <div className="trail">
        <span className="trail-label">필터</span>
        <button className={'ftab' + (!cho ? ' ftab-on' : '')} onClick={clearCho}>전체</button>
        {cho && (
          <div className="ftab ftab-active">
            <span className="ftab-jamo">{cho}</span>
            <span className="ftab-x" onClick={(e)=>{e.stopPropagation();clearCho();}}><Icon.x s={12}/></span>
          </div>
        )}
        {cho && jung && (
          <div className="ftab ftab-active">
            <span className="ftab-jamo">{cho}{jung}</span>
            <span className="ftab-x" onClick={(e)=>{e.stopPropagation();clearJung();}}><Icon.x s={12}/></span>
          </div>
        )}
        {syl && (
          <div className="ftab ftab-active ftab-syl">
            <span className="ftab-jamo">{syl}</span>
            <span className="ftab-x" onClick={(e)=>{e.stopPropagation();clearSyl();}}><Icon.x s={12}/></span>
          </div>
        )}
      </div>

      {/* level 1 — consonants */}
      <div className="jamorow">
        {CONSONANTS.map(c => (
          <button key={c} className={'jamo' + (cho === c ? ' jamo-on' : '')} onClick={() => cho===c ? clearCho() : pickCho(c)}>{c}</button>
        ))}
      </div>

      {/* level 2 — vowels (after consonant) */}
      {cho && (
        <div className="jamorow sub">
          {VOWELS.map(v => (
            <button key={v} className={'jamo jamo-vowel' + (jung === v ? ' jamo-on' : '')} onClick={() => jung===v ? clearJung() : pickJung(v)}>{cho}{v}</button>
          ))}
        </div>
      )}

      {/* level 3 — full syllables (after vowel) */}
      {cho && jung && syllables.length > 0 && (
        <div className="jamorow sub">
          {syllables.map(s => (
            <button key={s} className={'jamo jamo-syl' + (syl === s ? ' jamo-on' : '')} onClick={() => syl===s ? clearSyl() : setSyl(s)}>{s}</button>
          ))}
        </div>
      )}

      <div className="reslabel">{results.length}자{cho && <span className="reslabel-sub"> · {syl || (cho + (jung||''))} 으(로) 시작</span>}</div>

      <div className="cardlist">
        {results.map((g, i) => <CharCard key={i} d={g} onChain={() => onChain(g)} />)}
        {results.length === 0 && <div className="empty">이 자음으로 저장된 한자가 없어요</div>}
      </div>
    </div>
  );
}
window.Gallery = Gallery;
