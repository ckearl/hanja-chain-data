// ── Screen 4 · Chains (tree + graph-hint) ────────────────────
const { WORDS, HANJA_META, relatedWords, hanjaString, CHAIN_SEED } = window.DATA;

// A single word rendered as tappable syllable columns (한글 over 漢字)
function WordChip({ word, expandedSyl, onTapSyl, active, mini }) {
  const pairs = WORDS[word] || [];
  return (
    <div className={'wordchip' + (active ? ' wc-active' : '') + (mini ? ' wc-mini' : '')}>
      {pairs.map((p, i) => {
        const on = expandedSyl === p[0];
        return (
          <button key={i} className={'wc-col' + (on ? ' wc-col-on' : '')}
            onClick={(e) => { e.stopPropagation(); onTapSyl && onTapSyl(p[0], p[1]); }}>
            <span className="wc-ko">{p[0]}</span>
            <span className="wc-h">{p[1]}</span>
          </button>
        );
      })}
    </div>
  );
}

// ── Tree view (vertical downward expansion) ──────────────────
function TreeNode({ node, path, activePath, onExpand, depth }) {
  const isPrefix = path.every((v, i) => activePath[i] === v);
  const onActive = isPrefix && path.length <= activePath.length;
  return (
    <div className="tnode">
      <div className={'tnode-row' + (onActive ? '' : ' tnode-dim')}>
        {depth > 0 && <span className="connector" />}
        <WordChip word={node.word} expandedSyl={node.expanded}
          active={node.expanded != null}
          onTapSyl={(syl, hanja) => onExpand(path, syl, hanja)} />
      </div>
      {node.expanded && node.children.length > 0 && (
        <div className="tchildren">
          {node.children.map((c, i) => (
            <TreeNode key={c.word + i} node={c} path={[...path, i]}
              activePath={activePath} onExpand={onExpand} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Graph-hint view (curated 2D arrangement) ─────────────────
function GraphView() {
  // fixed demo layout — seed → 낙 branch → 원 branch
  const nodes = {
    seed:  { word: '낙관적', x: 24,  y: 215, active: true },
    n1:    { word: '낙원',   x: 250, y: 96,  active: true },
    n2:    { word: '쾌락',   x: 250, y: 215 },
    n3:    { word: '음악',   x: 250, y: 334 },
    n4:    { word: '공원',   x: 486, y: 36,  active: true },
    n5:    { word: '정원',   x: 486, y: 132 },
    n6:    { word: '원예',   x: 486, y: 222 },
  };
  const edges = [
    ['seed','n1',true], ['seed','n2',false], ['seed','n3',false],
    ['n1','n4',true], ['n1','n5',false], ['n1','n6',false],
  ];
  const CW = 200, CH = 64;
  const cx = (k) => nodes[k].x + CW / 2, cy = (k) => nodes[k].y + 30;
  return (
    <div className="graphwrap">
      <div className="graphcanvas" style={{ width: 720, height: 430 }}>
        <svg className="graph-svg" width="720" height="430">
          {edges.map(([a, b, on], i) => {
            const x1 = nodes[a].x + CW, y1 = cy(a), x2 = nodes[b].x, y2 = cy(b);
            const mx = (x1 + x2) / 2;
            return <path key={i} d={`M${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`}
              className={'edge' + (on ? ' edge-on' : '')} fill="none" />;
          })}
        </svg>
        {Object.entries(nodes).map(([k, n]) => (
          <div key={k} className={'gnode' + (n.active ? ' gnode-on' : '')}
            style={{ left: n.x, top: n.y, width: CW }}>
            <WordChip word={n.word} mini active={n.active} onTapSyl={() => {}} />
          </div>
        ))}
      </div>
      <div className="graph-hint-note">↔ 좌우로 스크롤 · 그래프 뷰는 방향 스케치입니다</div>
    </div>
  );
}

function Chains() {
  const [view, setView] = useState('tree');
  const [tree, setTree] = useState({ word: CHAIN_SEED, expanded: null, children: [] });
  const [activePath, setActivePath] = useState([]);

  const expand = (path, syl, hanja) => {
    setActivePath(path);
    setTree(prev => {
      const clone = JSON.parse(JSON.stringify(prev));
      let node = clone;
      for (const idx of path) node = node.children[idx];
      if (node.expanded === syl) { node.expanded = null; node.children = []; }
      else {
        node.expanded = syl;
        node.children = relatedWords(node.word, hanja).map(w => ({ word: w, expanded: null, children: [] }));
      }
      return clone;
    });
  };

  const reset = () => { setTree({ word: CHAIN_SEED, expanded: null, children: [] }); setActivePath([]); };

  // breadcrumb words along active path
  const trail = [];
  { let n = tree; trail.push(n.word); for (const idx of activePath) { n = n.children[idx]; if (n) trail.push(n.word); } }

  return (
    <div className="screen">
      <AppHeader kr="체인" en="CHAINS" right={
        <button className="newchain" onClick={reset}><Icon.plus s={15} /> 새 체인</button>
      } />

      {/* view toggle */}
      <div className="viewtoggle">
        <button className={'vt' + (view === 'tree' ? ' vt-on' : '')} onClick={() => setView('tree')}>트리</button>
        <button className={'vt' + (view === 'graph' ? ' vt-on' : '')} onClick={() => setView('graph')}>그래프</button>
      </div>

      {/* breadcrumb */}
      <div className="breadcrumb">
        {trail.flatMap((w, i) => {
          const span = <span key={'w' + i} className={'bc' + (i === trail.length - 1 ? ' bc-on' : '')}>{w}</span>;
          return i > 0 ? [<Icon.chevron key={'c' + i} s={12} />, span] : [span];
        })}
      </div>

      {view === 'tree' ? (
        <div className="treewrap">
          <TreeNode node={tree} path={[]} activePath={activePath} onExpand={expand} depth={0} />
          {!tree.expanded && (
            <div className="tree-hint">음절을 눌러 같은 한자를 쓰는 단어로 가지를 뻗어보세요</div>
          )}
        </div>
      ) : <GraphView />}
    </div>
  );
}
window.Chains = Chains;
