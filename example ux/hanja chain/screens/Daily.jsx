// ── Screen 1 · Daily (bento grid) ────────────────────────────
function Daily({ setTab }) {
  const { TODAY } = window.DATA;
  // mock 3-week activity (0 none · 1 light · 2 mid · 3 strong)
  const activity = [0,1,2,1,3,2,0, 1,2,3,2,1,2,3, 2,3,1,2,3,3,2];

  return (
    <div className="screen">
      <AppHeader kr="오늘의 한자" en="MON · 6월 2일" />

      <div className="bento">
        {/* Hero — today's character */}
        <div className="pane hero" role="button" tabIndex={0} onClick={() => setTab('search')}>
          <div className="hero-top">
            <span className="kicker">오늘의 한자</span>
            <Icon.chevron s={16} />
          </div>
          <div className="hero-glyph">{TODAY.hanja}</div>
          <div className="hero-reading">{TODAY.reading}</div>
          <div className="hero-eng">{TODAY.eng}</div>
          <div className="hero-pills">
            {TODAY.examples.map((e, i) => <Pill key={i} word={e.w} hanja={e.h} />)}
          </div>
        </div>

        {/* Gallery shortcut */}
        <div className="pane" role="button" tabIndex={0} onClick={() => setTab('gallery')}>
          <div className="pane-head"><Icon.gallery s={18} /><span>Gallery</span></div>
          <div className="big-num">42<span className="unit">자</span></div>
          <div className="pane-note">상위 100자 중 <b>15%</b> 학습 완료</div>
        </div>

        {/* Streak */}
        <div className="pane" role="button" tabIndex={0}>
          <div className="pane-head streak-head"><Icon.flame s={17} /><span>연속 학습</span></div>
          <div className="big-num">14<span className="unit">일</span></div>
          <div className="streakgrid">
            {activity.map((v, i) => <span key={i} className={'cell c' + v} />)}
          </div>
        </div>

        {/* Flashcards */}
        <div className="pane" role="button" tabIndex={0}>
          <div className="pane-head"><Icon.cards s={18} /><span>Flashcards</span>
            <span className="badge">12</span>
          </div>
          <div className="pane-note big">오늘 복습할<br/>카드 <b>12</b>장</div>
          <div className="cta">복습 시작 <Icon.arrow s={15} /></div>
        </div>

        {/* Search */}
        <div className="pane" role="button" tabIndex={0} onClick={() => setTab('search')}>
          <div className="pane-head"><Icon.search s={18} /><span>Search</span></div>
          <div className="searchbox-mini">한자, 한국어, English…</div>
        </div>

        {/* History fact */}
        <div className="pane history" role="button" tabIndex={0}>
          <div className="pane-head"><Icon.scroll s={18} /><span>어원 · 옛이야기</span></div>
          <p className="fact-kr">{TODAY.history}</p>
          <p className="fact-en">{TODAY.historyEn}</p>
        </div>
      </div>
    </div>
  );
}
window.Daily = Daily;
