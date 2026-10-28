// ── 한자 체인 · data layer ────────────────────────────────────
// All real Hanja / Korean data + Hangul jamo decomposition.

// Hangul initial (초성) and medial (중성) jamo tables
const CHO = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];
const JUNG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ'];
// fold tense / compound jamo down to their base for filtering
const CHO_BASE = { 'ㄲ':'ㄱ','ㄸ':'ㄷ','ㅃ':'ㅂ','ㅆ':'ㅅ','ㅉ':'ㅈ' };
const JUNG_BASE = { 'ㅐ':'ㅐ','ㅒ':'ㅑ','ㅔ':'ㅔ','ㅖ':'ㅕ','ㅘ':'ㅗ','ㅙ':'ㅗ','ㅚ':'ㅗ','ㅝ':'ㅜ','ㅞ':'ㅜ','ㅟ':'ㅜ','ㅢ':'ㅡ' };

function decompose(syllable) {
  const code = (syllable || '').charCodeAt(0) - 0xAC00;
  if (code < 0 || code > 11171) return { cho: null, jung: null };
  const cho = CHO[Math.floor(code / 588)];
  const jung = JUNG[Math.floor((code % 588) / 28)];
  return { cho: CHO_BASE[cho] || cho, jung: JUNG_BASE[jung] || jung };
}

// Filter rows for the Gallery
const CONSONANTS = ['ㄱ','ㄴ','ㄷ','ㄹ','ㅁ','ㅂ','ㅅ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];
const VOWELS = ['ㅏ','ㅐ','ㅑ','ㅓ','ㅔ','ㅕ','ㅗ','ㅛ','ㅜ','ㅡ','ㅣ'];

// ── Today's character ────────────────────────────────────────
const TODAY = {
  hanja: '學', sound: '학', reading: '배울 학', eng: 'to learn · to study',
  examples: [
    { w: '학교', h: '學校', g: 'school' },
    { w: '학생', h: '學生', g: 'student' },
    { w: '학문', h: '學問', g: 'scholarship' },
    { w: '학자', h: '學者', g: 'scholar' },
    { w: '대학', h: '大學', g: 'university' },
  ],
  history:
    '갑골문에서 學은 지붕 아래 아이가 두 손으로 셈대를 본받는 모습으로, ' +
    '“가르침을 본받아 익히다”라는 뜻에서 출발했다.',
  historyEn: 'In oracle-bone script, 學 showed a child beneath a roof copying counting rods held in two hands — learning as imitation under shelter.',
};

// ── Gallery: saved characters ────────────────────────────────
const GALLERY = [
  { hanja: '學', sound: '학', reading: '배울 학', eng: 'to learn', ex: ['학교','학생','학문','학자'], more: 6 },
  { hanja: '江', sound: '강', reading: '강 강', eng: 'river', ex: ['강변','강산','한강'], more: 0 },
  { hanja: '强', sound: '강', reading: '강할 강', eng: 'strong', ex: ['강력','강조','강제','강도'], more: 2 },
  { hanja: '愛', sound: '애', reading: '사랑 애', eng: 'love', ex: ['애정','애인','연애'], more: 4 },
  { hanja: '國', sound: '국', reading: '나라 국', eng: 'country', ex: ['국가','국민','한국','외국'], more: 9 },
  { hanja: '語', sound: '어', reading: '말씀 어', eng: 'language', ex: ['언어','국어','영어'], more: 3 },
  { hanja: '心', sound: '심', reading: '마음 심', eng: 'heart · mind', ex: ['심장','관심','중심','진심'], more: 7 },
  { hanja: '力', sound: '력', reading: '힘 력', eng: 'power', ex: ['능력','노력','체력'], more: 5 },
  { hanja: '水', sound: '수', reading: '물 수', eng: 'water', ex: ['수도','수영','홍수'], more: 4 },
  { hanja: '火', sound: '화', reading: '불 화', eng: 'fire', ex: ['화재','화산','소화'], more: 2 },
  { hanja: '木', sound: '목', reading: '나무 목', eng: 'tree · wood', ex: ['목재','식목','목수'], more: 1 },
  { hanja: '金', sound: '금', reading: '쇠 금', eng: 'gold · metal', ex: ['금속','현금','황금'], more: 3 },
  { hanja: '人', sound: '인', reading: '사람 인', eng: 'person', ex: ['인간','개인','인구','성인'], more: 12 },
  { hanja: '大', sound: '대', reading: '큰 대', eng: 'big · great', ex: ['대학','대화','위대'], more: 6 },
  { hanja: '山', sound: '산', reading: '메 산', eng: 'mountain', ex: ['산맥','등산','화산'], more: 2 },
  { hanja: '海', sound: '해', reading: '바다 해', eng: 'sea', ex: ['해변','해양','항해'], more: 3 },
  { hanja: '時', sound: '시', reading: '때 시', eng: 'time', ex: ['시간','시대','당시'], more: 5 },
  { hanja: '食', sound: '식', reading: '먹을 식', eng: 'eat · food', ex: ['식사','식당','음식'], more: 4 },
];

// ── Search index (gallery + the 사 family + more) ────────────
const SEARCH_INDEX = [
  { hanja: '四', sound: '사', reading: '넉 사', eng: 'four', ex: ['사방','사계'] },
  { hanja: '死', sound: '사', reading: '죽을 사', eng: 'to die', ex: ['사망','생사'] },
  { hanja: '思', sound: '사', reading: '생각할 사', eng: 'to think', ex: ['사고','의사'] },
  { hanja: '師', sound: '사', reading: '스승 사', eng: 'teacher · master', ex: ['교사','은사'] },
  { hanja: '事', sound: '사', reading: '일 사', eng: 'affair · matter', ex: ['사건','행사'] },
  ...GALLERY.map(g => ({ hanja: g.hanja, sound: g.sound, reading: g.reading, eng: g.eng, ex: g.ex.slice(0, 2) })),
];

const RECENT = ['學', '江', '心', '愛'];
const SUGGESTED = ['사', '水', '자주 쓰는 한자', '강', 'love'];

// ── Chains graph data ────────────────────────────────────────
const HANJA_META = {
  '樂': { sound: '락', reading: '즐길 락 · 노래 악', eng: 'joy · music' },
  '觀': { sound: '관', reading: '볼 관', eng: 'to view' },
  '的': { sound: '적', reading: '과녁 적', eng: 'target · -tic' },
  '園': { sound: '원', reading: '동산 원', eng: 'garden' },
  '快': { sound: '쾌', reading: '쾌할 쾌', eng: 'pleasant' },
  '音': { sound: '음', reading: '소리 음', eng: 'sound' },
  '公': { sound: '공', reading: '공평할 공', eng: 'public' },
  '庭': { sound: '정', reading: '뜰 정', eng: 'courtyard' },
  '藝': { sound: '예', reading: '재주 예', eng: 'art · skill' },
  '天': { sound: '천', reading: '하늘 천', eng: 'heaven' },
  '光': { sound: '광', reading: '빛 광', eng: 'light' },
  '念': { sound: '념', reading: '생각 념', eng: 'thought' },
  '目': { sound: '목', reading: '눈 목', eng: 'eye · goal' },
};

// word → ordered [syllable, hanja] pairs
const WORDS = {
  '낙관적': [['낙','樂'],['관','觀'],['적','的']],
  '낙원':   [['낙','樂'],['원','園']],
  '쾌락':   [['쾌','快'],['락','樂']],
  '음악':   [['음','音'],['악','樂']],
  '낙천적': [['낙','樂'],['천','天'],['적','的']],
  '공원':   [['공','公'],['원','園']],
  '정원':   [['정','庭'],['원','園']],
  '원예':   [['원','園'],['예','藝']],
  '관광':   [['관','觀'],['광','光']],
  '관념':   [['관','觀'],['념','念']],
  '목적':   [['목','目'],['적','的']],
};

// hanja → words that contain it
const HANJA_TO_WORDS = {
  '樂': ['낙관적','낙원','쾌락','음악','낙천적'],
  '觀': ['낙관적','관광','관념'],
  '的': ['낙관적','낙천적','목적'],
  '園': ['낙원','공원','정원','원예'],
  '公': ['공원'],
  '音': ['음악'],
  '快': ['쾌락'],
  '庭': ['정원'],
  '藝': ['원예'],
  '光': ['관광'],
  '念': ['관념'],
  '目': ['목적'],
};

function hanjaString(word) {
  return (WORDS[word] || []).map(p => p[1]).join('');
}
// words sharing the hanja behind `syllable` in `word`, excluding `word` itself
function relatedWords(word, hanja) {
  return (HANJA_TO_WORDS[hanja] || []).filter(w => w !== word);
}

const CHAIN_SEED = '낙관적';

window.DATA = {
  decompose, CONSONANTS, VOWELS,
  TODAY, GALLERY, SEARCH_INDEX, RECENT, SUGGESTED,
  HANJA_META, WORDS, HANJA_TO_WORDS, hanjaString, relatedWords, CHAIN_SEED,
};
