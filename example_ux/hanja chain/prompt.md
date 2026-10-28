# Claude Design Prompt

You are designing a mobile-first Korean Hanja learning app called (working title)

**한자 체인** (hanja chain) or similar. The target user is a non-native Korean speaker who is
proficient in Korean and wants to deepen their understanding of Chinese character
roots in the language. Think scholarly but approachable — not a kids' flashcard
app, not a dry reference tool.

## Design direction

- Mobile-first. Design for ~390px wide viewport (iPhone 16 size).
- Aesthetic: clean, modern, East Asian editorial. Think ink, brushwork as subtle
  texture, not kitsch. Characters themselves are the visual centerpiece — let them
  breathe and be large.
- Typography: the Hanja characters (e.g. 學, 江, 强) should always render large,
  legible, and prominent. Korean text secondary. English tertiary.
- Color palette: neutral base (off-white or very dark for dark mode), one strong
  accent color for interactive elements. Suggest muted indigo or ink-blue as the
  accent — but you can propose alternatives.
- Subtle dark mode preferred as the primary design direction.
- Bottom tab navigation with 4 tabs: Daily, Gallery, Search, Chains.
- No gradients, no bubbly gamification UI. Clean, typographic, confident.

---

## Screen 1: Daily

The home screen. Six panes bento-style grid where each box is a shortcut to a key feature or content area.

Pane 1 (hero/full-width or 2-col span): Today's Hanja character.

- The Hanja character rendered very large (think 120px+)
- Below it: the Korean reading and meaning (e.g. 배울 학)
- Below that: 3-5 example words using that character, shown as pills or a
    compact list (e.g. 학생, 학교, 학문)
- Tapping the pane opens the full character detail view

Pane 2: "Gallery" — shortcut to the gallery tab, shows a small preview/count
  of how many characters the user has saved. Some small fact about the gallery that rotates daily (e.g. "You have 42 characters saved! Did you know...", or "you have studied 15% of the top 100 most common Hanja characters!", or "the most common Hanja character is 人 (사람 인) — you have 50 words saved that use this character!")

Pane 3: Daily history fact — a short ancient history or etymology fact related
  to the daily character. Just a text snippet with a subtle icon.

Pane 4: "Search" — shortcut to search tab with a small search icon

Pane 5: "Flashcards" — opens the flashcard study session. Shows cards due today
  (SRS-style). Badge with due count.

Pane 6: Study streak — streak count (e.g. 🔥 14일), a small weekly activity
  grid like GitHub's contribution graph but minimal.

---

## Screen 2: Gallery

Shows all characters the user has saved/studied.

Top: nested segmented control / tab filter

- Level 1: Korean consonant (ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ ㅇ ㅈ ㅊ ㅋ ㅌ ㅍ ㅎ + all)
- Level 2 (appears after selecting a consonant): vowel combinations
    (ㅏ ㅐ ㅑ ㅓ ㅔ ㅕ ㅗ ㅛ ㅜ ㅡ ㅣ + all), which filters to syllables like
    가, 각, 간, 갈, 감, 강...
- Level 3 (optional deepest filter): specific full syllable (가, 각, 간, etc.)
  The nested tabs should feel natural, not cramped — consider horizontal scroll
  for the consonant row.

Think of the tabs in the style of pinned tabs on a web browser, where you can have multiple active filters at once. One filter would be the root consonant, two filters would be the consonant + vowel, and three filters would be the full syllable. Adding a filter would narrow down the results, and add a visual tab for that filter. Removing a filter would widen the results and remove the corresponding tab. So filters will be cumulative and combinatorial, from consonant → consonant+vowel → full syllable, but the UI should make it clear which filters are active and how they relate to each other.

Below the filter: a list/card view of matching saved characters.
  Each card shows:

- The Hanja character (large, left side)
- Korean reading + meaning (e.g. 배울 학)
- English gloss (e.g. "to learn / study")
- Up to 4 example words shown as horizontal pills (학교, 학생, 학문...)
    with a "+N more" indicator if there are more
- A small "open in Chains" icon button on the card

---

## Screen 3: Search

Top: a prominent search bar.

- Placeholder: "한자, 한국어, or English..."
- Below the bar: 3 small toggle chips — 漢字 / 한국어 / English — to filter
    search mode (or auto-detect)

Results: scrollable list, same card style as Gallery but more compact.
  Each result shows:

- Hanja character (large)
- Reading + meaning in Korean
- English gloss
- 1-2 example words as pills

Empty/pre-search state: show recently viewed characters or suggested searches.

---

## Screen 4: Chains

The most unique screen — a traversal graph view.

The concept: each node is a Korean word. Tapping a syllable in that word
expands to show other words that use that same Hanja character. You can
traverse indefinitely in any direction, forward and back.

Example traversal:
  낙관적 → (tap 낙) → 낙원, 낙하산, 쾌락 → (tap 원 in 낙원) → 공원, 원칙, 원소

Visual design:

- Start with a single "seed" node in the center or top
- Each word node is a pill/card showing the Korean word + its Hanja notation
    below (e.g. 낙관적 / 樂觀的)
- When expanded, child nodes branch out from the tapped syllable
- Active/selected path is highlighted in the accent color
- Previously visited nodes remain visible but dimmed
- Breadcrumb trail at the top showing the current chain path
- A "start new chain" button to reset
- Entry points: you can also start a chain from Search or Gallery

For the initial mockup, you can represent this as a vertical feed-style
expansion (like a tree that grows downward) rather than a full 2D force graph —
that's fine for v1, with a note that it could become a true graph view later.

---

## What to build

Create high-fidelity mockups for all 4 screens as a single scrollable HTML
prototype. Use real-looking data (use actual Hanja characters, real Korean words,
real readings — don't use lorem ipsum). Dark mode as the primary render.

After the initial mockup, I'll give feedback and we'll iterate on:

- The Daily pane grid layout
- The Gallery nested filter UX
- The Chains traversal visual design (this is the most novel, iterate most here)

For the Chains screen especially, show at least 2 visual approaches — one
tree/vertical-expansion style and one that hints at a more graph-like layout —
so we can decide on direction.

Use real Korean + Hanja data in all mockups:

- Daily character: 學 (배울 학) — examples: 학교, 학생, 학문, 학자, 대학
- Gallery sample entries: 學, 江, 强, 愛, 國, 語, 心, 力
- Search results for 사: 四(넉 사), 死(죽을 사), 思(생각할 사), 師(스승 사), 事(일 사)
- Chains seed word: 낙관적(樂觀的), first branch on 낙(樂): 낙원(樂園), 쾌락(快樂),
  음악(音樂), then branch on 원(園) from 낙원: 공원(公園), 정원(庭園), 원예(園藝)
