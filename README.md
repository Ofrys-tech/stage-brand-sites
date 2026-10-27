# stage-brand-sites

Custom websites for performers, artists, and stage productions.

## Люди Бренды — static site

Static replacement for the Tilda site `lyudi-brendy.ru`. Fully self-hosted: no request goes to
`tildacdn.com` at runtime.

**Live demo:** https://ofrys-tech.github.io/stage-brand-sites/
(GitHub Pages, built from `main` — every push updates it.)

[![Hub page, desktop](docs/preview.png)](https://ofrys-tech.github.io/stage-brand-sites/)

<p align="center">
  <img src="docs/preview-mobile.png" alt="Hub page, mobile" width="320">
</p>

| route | content | source |
|---|---|---|
| `/` | new hub page (hand-built) | this repo |
| `/ufa-nov-2026/` | Счастливый путь — Уфа, 25 ноября 2026 | new page (this repo), content from the designer's КП |
| `/ufa-2026/` | Спектакль в Уфе 2026 | Tilda page `118761336` (was `/`) |
| `/kazan/` | Спектакль в Казани 2025 | Tilda page `57448733` |
| `/ufa/` | Спектакль в Уфе 2024 | Tilda page `63388755` |
| `/partner/` | Стать партнёром | Tilda page `60132875` |

Run it:

```bash
python3 -m http.server 8777        # then open http://127.0.0.1:8777/
```

**Rollback.** Before the charity content update the tree is tagged `pre-charity-2026-10`;
`git reset --hard pre-charity-2026-10` restores the site as it was.

No build step, no dependencies. Deploy = serve this directory (the repo root) as the web root.
All internal links are relative (`kazan/`, `../assets/…`), so the same files work under the GitHub
Pages sub-path and at the root of `lyudi-brendy.ru`. Pages must be served as directory indexes
(`kazan/index.html`).

### How the spectacle pages were ported

`tools/port_tilda.py` turns the verbatim snapshots in `docs/captures/…/published-html/` into
`<route>/index.html`. The captured HTML already carries the complete generated Zero Block CSS
inline, so the port is byte-faithful and only rewrites references:

- CDN libraries → `assets/tilda/` (Tilda runtime, self-hosted)
- CDN images → `assets/img/tilda/<hash>/<name>` (originals, 160 files)
- `fonts-tildasans.css` → `assets/tilda/fonts.css` (TildaSans variable, local)
- links `https://lyudi-brendy.ru/…` → relative routes
- telemetry (`tilda-stat`, `neo` fallback) and the dead `/script.js` reference are dropped
- native `loading="lazy"` below the first screen; popup images stay eager
- the two 3600×420 stadium outlines in the hero (the arcs sticking out of the viewport) lose their
  1px border — the faint panel fill stays
- **navigation** (`assets/tilda/site-<route>.css`, generated per page): spectacle-to-spectacle links
  are gone ("Спектакль в Казани 2025", "Уфа 2024", "Уфа 2026" — 2 header items and 2 hero buttons per
  page); a ghost outline "← На главную" pill sits left of "О спектакле" (the nav buttons are
  shifted right by 170px to make room), matching the show-page back button; phones keep the
  «← На главную» row at the top of the Tilda menu; the in-page anchors are repaired
  ("О спектакле" / "Партнеры" / "Актеры" and the roundel scroll smoothly to the right section —
  Tilda had copied the Kazan record ids into the other pages, so they did nothing, and on the old root
  page the roundel opened a photo popup instead of scrolling); the bottom plaque is removed entirely
  from the three spectacle pages — the date pill, the time pill, the "Смотреть фото" button and the
  empty card that framed them
- **mobile navigation**: the Tilda burger menu is a full-screen sheet with a "← На главную"
  row; it locks the page behind it and closes on a link, Escape or a desktop resize
  (`assets/js/tilda-mobile-menu.js`). The Tilda mobile header and the
  hero nav row overlap between 960–980px; the duplicate Tilda bar is hidden in that window.
- **accessibility**: the port adds `<html lang="ru">` and a visually hidden `<h1>` (Tilda renders
  all visible titles as positioned divs); the mobile menu links close the menu before scrolling.
- **contacts**: the phone opens `tel:`, the e-mail opens `mailto:`, the venue street opens Yandex Maps in
  a new tab (on `/kazan/` the address in the hero is linked too), and the ИП line is tidied — no dot
  before a comma, no dot after the postcode, while «г.» keeps its dot:
  *ИП Злобина Инна Сергеевна, 450091, г. Уфа, Карла Маркса, 58*

```bash
python3 tools/port_tilda.py plan     # asset manifests (tools/_images.txt, tools/_libs.txt)
python3 tools/port_tilda.py build    # rewrite the three generated pages (partner is skipped)
```

**Fidelity check** (how the port was verified): every `.tn-elem` on each page was measured in
Chromium on both the live Tilda page and the local copy after a full-page scroll:

| page | elements | missing | max delta | font mismatches |
|---|---|---|---|---|
| `/ufa-2026/` | 209 | 0 | **0 px** | 0 |
| `/kazan/` | 145 | 0 | **0 px** | 0 |
| `/ufa/` | 186 | 0 | **0 px** | 0 |
| `/partner/` | 46 | 0 | **0 px** | 0 |

Also verified: 0 console errors, 0 failed requests, 0 unloaded images, no horizontal overflow at
320–1440 px, mobile Tilda burger menu works.

### Weight

| route | HTML | images | libraries | first screen | whole page |
|---|---|---|---|---|---|
| `/ufa-2026/` | 704 KB | 27.4 MB (75) | 519 KB | ~1.5 MB | 28.6 MB |
| `/kazan/` | 489 KB | 4.7 MB (58) | 738 KB | ~2.6 MB | 5.9 MB |
| `/ufa/` | 537 KB | 4.2 MB (65) | 489 KB | ~1.3 MB | 5.2 MB |
| `/partner/` | 167 KB | 1.6 MB (21) | 706 KB | ~1.3 MB | 2.4 MB |

The originals are kept because they are the source of truth; Tilda used to serve WebP/resized
variants, so an image pipeline is the obvious next optimisation (the `/ufa-2026/` page carries most
of the weight: 7 files are ≥ 1 MB, `Mask_group.png` alone is 2.8 MB).

### Structure

```
index.html                     hub page
ufa-nov-2026/                  Счастливый путь — new hand-built show page
ufa-2026/ kazan/ ufa/ partner/ ported spectacle pages (Tilda markup, local assets)
assets/css/main.css            hub + show styles, programme sections, design tokens
assets/css/show.css            /ufa-nov-2026/ hero, title partner, partner board
assets/css/motion.css          premium motion layer (hub, show, partner)
assets/css/partner.css         /partner/ programme blocks added on top of Tilda
assets/js/main.js              menu, current year, page fade, back-to-top
assets/js/motion.js            header state, card spotlight, scroll drift, counters
assets/js/reveal.js            scroll reveals, hero entrance support, image parallax
assets/js/tilda-mobile-menu.js full-screen Tilda menu: home row, close on link/Escape/resize
assets/fonts/TildaSans-VF.woff2
assets/img/                    hub brand assets + og.png
assets/img/logo-lockup.svg     full lockup: wordmark + «Театр добрых дел»
assets/img/story/              photos, designer PDF slides + mobile crops, show title and hero art for /ufa-nov-2026/
assets/img/partners/           partner logos for /ufa-nov-2026/ (trimmed WebP cards + white title mark)
assets/img/tilda/<hash>/       images of the ported pages (160)
assets/tilda/                  Tilda runtime used by the ported pages + fonts.css
tools/port_tilda.py            the port script; tools/_images.txt / _libs.txt are its manifests
docs/tilda.md                  Tilda account/API/migration reconnaissance
docs/captures/                 verbatim snapshots of the Tilda project (11092055), sanitized
docs/preview*.png              README screenshots
.nojekyll                      keep GitHub Pages from running Jekyll
```

### Partner board (`/ufa-nov-2026/`)

The show page uses the client's status order:

- **title partner** in the hero — ГК ТОЧНО, caption «Федеральный застройщик ГК ТОЧНО»;
- **official partner** — Indjushkin;
- **partners** — Брауни and Красный Ключ;
- smaller **partner** row — Hampton, Kumpan, Арго, Глобус, Собака, Арета, Россия 24.

All logos are trimmed WebP cards on white. The general partner goes under the title logo, smaller,
when its logo arrives. Original vectors/PDFs/JPEGs stay in the gitignored `materials/partners-src/`.

### Navigation and back-to-top

The hub and `/ufa-nov-2026/` mobile menus are solid `#171717` sheets without the old grid: the
sheet fades/slides in, the links are centred and stagger up, and the phone number is a live `tel:`
link styled in the accent colour. The hub keeps its items and the «Стать партнёром» pill, with
«Партнёрам» renamed to «Сотрудничество»; the show menu is exactly «О спектакле», «Партнёрам» and
the phone (the show CTA stays desktop-only). The hub also gets a round back-to-top button that
fades in when the requisites reach the viewport and smoothly returns to the top.

### Page fade

Clicking a spectacle card — the «Перейти на сайт спектакля» CTA — fades the hub to `#0a0a0a` for
220 ms and then navigates; the hub and `/ufa-nov-2026/` fade in for 280 ms. `prefers-reduced-motion`
navigates instantly, and modified clicks / new tabs are left to the browser. The older Tilda pages
are only faded out (they do not load `main.css`).

### Motion pass

`assets/css/motion.css` (hub, `/ufa-nov-2026/`, `/partner/`) and `assets/js/motion.js`
(hub + show) add a second, restrained motion layer:

- masked, word-by-word hero title on the hub; masked show-title image and staggered hero copy on
  `/ufa-nov-2026/`; the Toratau art settling in and floating slowly;
- a darker scrolled header, growing nav underlines, button lift/glow and a pointer spotlight on the
  spectacle cards;
- scale settles for the programme slides, partner-page editorial photos and partner logo cards;
- the 740/7 show counters and decorative scroll drift (ring, portrait, footer bust).

Entrances are gated by `html.motion`; hover lifts by `prefers-reduced-motion`; without JS or with
reduced motion everything is static and visible. The motion layer is a separate commit; revert it
to remove both the layer and its markup hooks.

First-screen images are preloaded WebP (`portrait`, `ring`, the show title and the Toratau art —
480 px on phones, 1000 px on desktop). The 740/7 counters start only when their block enters the
viewport, and the below-fold footer portrait is lazy.

### Colour transitions

Section colour blocks are joined by gradients instead of hard edges: `story` (black → grey),
`help` (grey → paper), `why` (paper → grey), the show CTA (grey → black) and the footer
(black → grey) use the section's top padding as the blend length. On the hub the first/last
programme slides fade into the page, the partner band fades at the top and bottom, and the
partner/footer/CTA grids are masked at their edges.

### Hub design tokens (measured from the live Tilda site)

| token | value |
|---|---|
| background | `#202020`, deep `#0a0a0a`, header `#1a1a1a`, card `#171717` |
| hairlines | `#373737`, `#323232` |
| text | `#ffffff`; muted `#acacac`, `#a6a6a6`, `#949494` |
| accent | `#da3036` (soft `#ec777b`) |
| radius | pills 30–50px, cards 20px |
| type | TildaSans; display 42px/300 uppercase in accent, body 20px/300, labels 20px/400 muted, values 20px/700 accent, buttons 18px/600 |
| container | 1200px (1160px content) |
| motion | 0.2s ease-in-out, matching Tilda's `--t396-speedhover` |

Contacts (from `lyudi-brendy.ru`): `+7 993 342-12-73`, `Dir-ufa@mail.ru`,
ИП Злобина Инна Сергеевна, индекс 450091, г. Уфа, Карла Маркса, 58.

### Known leftovers

- **Form backend.** The T702 popup form on `/kazan/` and `/partner/` still posts to Tilda's own
  handler (`data-tilda-formskey`, `action=""`). It needs a real backend before the Tilda account is
  retired. The phone, e-mail and WhatsApp links work independently.
- **`/partner/` is hand-maintained.** Its capture predates the programme blocks and the corrected
  copy, so `port_tilda.py build` deliberately skips it. Edit `partner/index.html` and
  `assets/css/partner.css` directly and keep the generated `assets/tilda/site-partner.css` in sync.
- **Empty T456 header.** On desktop the Tilda header block is a 0×0 placeholder — every visible nav
  item lives in the hero Zero Block, which is why the back pill is there. On phones the Tilda bar is
  the menu trigger; the home link is the first row of its full-screen sheet.
- **Images.** 27 MB of originals on `/ufa-2026/`; no WebP/responsive pipeline yet.
- **TildaSans** is vendored from Tilda's CDN. Confirm the licence before publishing.
