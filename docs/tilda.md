# Tilda: account access, API map, and migration recon

Scope: project **«Люди Бренды»** (`projectid=11092055`) at https://lyudi-brendy.ru, owner account `userid=10295205`.
Everything below is verified against the live account/platform, not inferred, unless marked `[INFERENCE]`.

Raw captures: `docs/captures/tilda-11092055/`.

---

## 1. Account & project inventory

| Field | Value |
|---|---|
| userid | `10295205` |
| username | `LB` |
| plan | `1` — **Tilda Personal** (`maxprojects: 1`, `maxpages: 1000`) |
| projects | 1 (`projects_intrash: 0`) |
| project id | `11092055` |
| project alias | `lyudi-brendy` |
| custom domain | `lyudi-brendy.ru` (https on) |
| fonts | `headlinefont: TildaSans`, `textfont: TildaSans` |
| header/footer page | `headerpageid: 0`, `footerpageid: 0` → **no shared header/footer**; each page embeds its own |
| index page | `118761336` |
| 404 page | `page404id: 0` → Tilda default |
| expired domains notice | `expiredomains: [{"id":278916}]` (unresolved) |

### Pages (6)

| pageid | alias | URL | blocks (`tplid`) | published (epoch) |
|---|---|---|---|---|
| `118761336` | *(index)* | `/` | 131, 456, 131, 396×5, 270, 390 | 1775473487 |
| `57448733` | `kazan` | `/kazan` | 456, 131, 396, 396, 396, 585, 396, 215, 396, 396, 702, 396, 396, 1093, 396, 396 | 1771441867 |
| `63388755` | `ufa` | `/ufa` | 456, 131, 396×5 | 1771441867 |
| `60132875` | `partner` | `/partner` | 456, 131, 396, 396, 702, 396, 396, 396 | 1771441868 |
| `122502036` | `13mart` | `/13mart` | 305 | 1772177048 |
| `122504626` | `30mart` | `/30mart` | 305 | 1772177051 |

`13mart` / `30mart` are **redirect stubs**: a single T305 HTML block running
`window.location.replace("https://lyudi-brendy.ru" + location.search + location.hash)`.
They exist to catch ad deep-links. Migration: plain redirects, no layout.

Ground truth for IDs/aliases: `POST /projects/get/getprojects/` with `comm=getprojectslist&projectid=11092055`
(capture: `pages_raw.json`).

---

## 2. Auth: how to get in

Tilda auth = cookie triple **`hash` + `userid` + `PHPSESSID`**, all `domain=tilda.ru`, plus a site-level
`mainsite=tilda.cc`-domain cookie from the domain-detection flow.

Verified failure/rotation behaviour:

- `hash` is **rotated on every login**. An old `hash` is rejected and the server answers
  `302 → /login/` with `set-cookie: hash=deleted; userid=deleted; tildacommonsessid=deleted`.
  This is exactly what happened with the first exported cookie set (hash rotated mid-capture).
- `PHPSESSID` must be the one bound to that `hash` server-side. Without a matching pair nothing works.
- Cookies exported while `domain_changed=1` / `need_save_domain=1` are the state right after a
  domain-link flow; the `tilda.cc/detectdomain/get/` → `/projects/?mainsite=checked` chain runs first
  and **wipes auth cookies if the session is stale**.
- A single HAR of the dashboard gave a working `hash` + `PHPSESSID` pair for this recon. The live values
  are deliberately **not** recorded here (credentials are never committed); take them from your own HAR.
- `userid=10295205` (the account id, not a credential) was constant across all captures; only the
  `hash`/`PHPSESSID` pair rotates.

### How to (re)authenticate when the session dies

1. **Best: HAR capture.** DevTools → Network → "Preserve log", reload `https://tilda.ru/projects/`,
   save HAR. The HAR contains the live `Cookie:` header for `tilda.ru/projects/get/getprojects/` and the
   `hash`/`PHPSESSID` are used verbatim in §3. This worked.
2. **Alternative: browser relay** (`omp browser-relay install`) to drive the user's real Chrome, then no
   cookie handling at all. Extension was not connected at recon time
   (`http://127.0.0.1:9224` up, `extension never connected`).
3. **Not viable:** exporting cookie JSON by hand. Fields get stale/partially filtered; every hand-made
   export failed while a HAR from the same minute worked.

### Requests must look like a browser

Headers used successfully: `User-Agent` matching the user's Chrome
(`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36`),
`Referer: https://tilda.ru/projects/` (or `https://tilda.ru/page/?pageid=<id>` for editor calls),
plus the cookie jar. Some endpoints return `{"error":"Page not found","error_code":"page_not_found"}`
instead of HTTP 404 when a param is wrong — check the body, not just the status.

---

## 3. API map (read-only; verified live)

Both `tilda.ru` and `tilda.cc` serve the same panels; the account panel lives on **`tilda.ru`**,
`tilda.cc` is the marketing site (redirect loops in a browser without cookies).

### 3.1 Project / page listings

```bash
# projects of the account (also returns csrf token)
POST https://tilda.ru/projects/get/getprojects/
  Cookie: hash=…; userid=…; PHPSESSID=…
→ {"username":"LB","plan":{"plan":1,"title":"Tilda Personal","maxprojects":1,…},
   "projects":[{"id":"11092055","title":"Люди Бренды","url":"https://lyudi-brendy.ru"}],
   "userid":10295205,"csrf":"<token>"}

# pages of one project + project meta
POST https://tilda.ru/projects/get/getprojects/
  comm=getprojectslist&projectid=11092055
→ {project:{id,indexpageid,headerpageid,footerpageid,customdomain,https,…},
   pages:[{id,title,alias,url,published,changed,thumb,folderid,trash,viewpassword},…]}

# page settings
POST https://tilda.ru/projects/get/getpagesettings/   comm=getpagesettings&pageid=<pageid>
# site settings (404 as called; real route not located)
# expired domains notice
POST https://tilda.ru/projects/get/getexpiredomains/    → {"expiredomains":[{"id":278916}]}
```

### 3.2 Page content — **the migration source of truth**

```bash
POST https://tilda.ru/page/get/getpage/
  Referer: https://tilda.ru/page/?pageid=<pageid>
  body: pageid=<pageid>&viewtrash=&minify=
→ 200 JSON, 3 KB … 800 KB per page
```

Response shape (`records` = blocks in render order):

```jsonc
{
  "lang": "RU",
  "page":   {"id","title","published","alias","noheader","nofooter","animationoff",
             "bgcolor","bgimg","linkcolor","writing_direction","isindex"},
  "project":{... same as §3.1 project ...},
  "records":[ {"tplid": 396, "html": "<…>", "css": "…", "js": "…",
               "csslibs": [...], "jslibs": [...]}, … ],
  "csslibs":["tilda-menusub-1.0.min.css", …],   // page-level additional libs
  "jslibs":["tilda-menu-1.0.min.js","tilda-zero-1.2.min.js", …],
  "ver":84493, "ver_editor":"…", "roles":[…], "Tildaupload_PUBLICKEY":"…"
}
```

Each record's `html` is the **un-minified block markup** including the Zero Block `data-field-*`
attributes; `css`/`js` are the block's generated assets. Captures:
`docs/captures/tilda-11092055/pages-json/<pageid>.json`.

### 3.3 Other endpoints found (not exercised / mutating — do not call blindly)

From `/tfront/dashboard/*.min.js` and `/tfront/page-editor/t-page-all.min.js`:

| Endpoint | Purpose |
|---|---|
| `POST /projects/submit/` | dashboard mutations; `comm` ∈ `delpage, dublicatepage, movepage*, pagepublish, delfolder, renamefolder, savepagessort, saveprojectssort, transferproject*, …`; needs `csrf` |
| `POST /page/submit/` | editor mutations; `comm` ∈ `saverecord, saverecordssort, deleterecord, addnewrecord, editrecordcontent, editrecordsettings, savepagealias, savepagetitle, pagepublish, getrecordhtml, updateundobutton, …` |
| `POST /zero/get/`, `/zero/submit/` | Zero Block data (`comm:"getzeroreceivers"` = form receivers) |
| `POST /page/publish/`, `/page/unpublish/` | publish toggles |
| `POST /page/edit/` | editor record tab content |
| `GET  /projects/trash/`, `/projects/staticstyle/` | trash, global styles |
| `GET  /projects/exporttozip/?projectid=`, `/projects/pageexport/?projectid=&pageid=&getcode=yes` | code export (see §6) |

`comm` on `/projects/submit/` is validated server-side: an unrecognized value returns
`Error: Unknown command` with HTTP 200.

---

## 4. Platform model (what the published site actually is)

Tilda emits a **static HTML page per page**; there is no client-side renderer of the site. Dependencies
come from 4 CDN hosts: `static.tildacdn.com`, `thb.tildacdn.com` (image transforms),
`app.tildacdn.com` (dashboard bundles), `neo.tildacdn.com`/`neo.tildaapi.com` (telemetry).

### Block types present in this project

| `tplid` | Block | Notes |
|---|---|---|
| `396` | **Zero Block** (`T396`) | free-form absolute canvas — **95 % of the site** |
| `456` | header menu (`T456`/`ME201`) | uses `tilda-menu` + `tilda-menusub` |
| `131` | HTML-code block (`T123` inside) | contains the **TicketsCloud** widget script |
| `702` | popup form (`T702`/`BF502N`) | hook `#popup:myform1`, `tilda-popup` + `tilda-forms` |
| `585` | accordion (`T585`/`TX16N`) | 15 KB HTML + 4.4 KB JS on `/kazan`, `t585_init` |
| `390` | button block (`T390`) | «Фотоотчёт 1» etc. — links / popup openers |
| `270` | anchor-scroll helper (`t270_scroll`) | in-page navigation |
| `215` | anchor target (`T215`/`T173`) | `<a name="partners">` — **not** a visual block |
| `1093` | popup wrapper (`T1093`) | `data-tooltip-hook="#zeropopup12"`, `data-popup-rec-ids="909691582"` — a **Zero Block shown in a popup**; 25 KB JS |
| `305` | HTML-code w/ meta | the redirect stubs (`/13mart`, `/30mart`) |
| `396` with `off="y"` | disabled placeholder | empty 223-byte records on `/kazan`, `/partner` — **skip in a port** |

### Section map (artboard heights = real page geometry)

`/` (118761336), Σ 9676 px: menu → tcwidget → hero 920 → 800 → gallery 1760 (29 img + 23 shape) →
5819 long text/cases (77 text + 26 shape) → CTA 377 → anchor → button.

`/kazan` (57448733), Σ 8256 px: menu → tcwidget → hero 920 → 800 → banner 230 → **accordion T585** →
disabled 396 → anchor T215 → disabled 396 → 680 (13 images) → **popup form T702** → 3829 text (55 text) →
680 → **T1093 popup containing Zero 740** → footer 377.

`/ufa` (63388755), Σ 8166 px: menu → tcwidget → hero 920 → 800 → 860 (21 shape + 22 image) →
5209 text (70 text) → footer 377.

`/partner` (60132875), Σ 2807 px: menu → tcwidget → hero 920 → 800 → **popup form T702** →
710 (1 img, 1 shape, CTA) → disabled 396 → footer 377.

Breakpoints per artboard are stored per field: `data-artboard-height-res-320/480/960` (and `-res-640`
where applicable); e.g. the `/` hero is 920 → 900 (960) → 860 (480) → 820 (320).
All artboards use `data-artboard-upscale="grid"` — none use `window` scaling, so the port does not need
`tilda-zero-scale` behaviour.

### Animation & interaction inventory (complete)

| Kind | Count | Where | Portable as |
|---|---|---|---|
| scroll-driven element animation (`data-animate-sbs-event="scroll"`) | **8 elements** | `/`, `/kazan`, `/ufa`, `/partner` | parse `data-animate-sbs-opts` |
| hover-driven element animation (`event="hover"`) | **5 elements** | same | same |
| hover CSS on elements | 119 / 149 / 73 / 119 `:hover` rules (`/`, `/kazan`, `/partner`, `/ufa`) | generated record CSS | plain CSS |
| `@keyframes` | **2** (`t-menuburger-anim`, `t-menuburger-anim2`) | every page | burger icon; base CSS |
| block appear-animations (`t-animate`) | **0** | — | nothing to port |
| sliders / carousels (`t-slds`) | **0** | — | nothing to port |
| video embeds | **0** | — | nothing to port |

SBS animation model: a **2-step keyframe list** per element —
`{mx,my}` px move, `{sx,sy}` scale, `op` opacity, `ro` rotate, plus
`di/dd/fi` (scroll mode) or `dt/ea/ti` (hover mode: duration, easing, time).
Present as `data-animate-sbs-opts` (13 elements) with breakpoint overrides
`-res-480` (8) and `-res-320` (4); no `-res-640`/`-res-960` overrides exist.
Trigger attrs: `data-animate-sbs-trg` (trigger selector) + `data-animate-sbs-trgofst` (offset).
`data-animate-mobile="y"` (13) disables the effect on mobile — reproduce it.

So "all animations" = 13 scroll/hover elements + element hover CSS + 2 burger keyframes.
No animation framework is used; everything is declarative.


### Zero Block anatomy (critical for a faithful port)

Published markup per artboard:

```html
<div class="t396__artboard"
     data-artboard-recid="1914306861"
     data-artboard-screens="320,480,640,960,1200"
     data-artboard-height="920"        data-artboard-height-res-320="820"
     data-artboard-height-res-480="860" data-artboard-height-res-960="900"
     data-artboard-valign="center" data-artboard-upscale="grid"
     data-artboard-ovrflw="visible">
  <div class='t396__elem tn-elem' data-elem-id='1730353224342' data-elem-type='image'
       data-field-top-value="13" data-field-left-value="20"
       data-field-top-res-960-value="…" data-field-left-res-640-value="…"
       data-field-width-value="1132" data-field-height-value="1132"
       data-field-axisx-value="left" data-field-axisy-value="top"
       data-field-container-value="grid" data-field-heightmode-value="hug"
       data-field-filewidth-value="1132" data-field-fileheight-value="1132">
    <div class="tn-atom">…</div>
  </div>
</div>
```

- Breakpoints: `320, 480, 640, 960, 1200` (media queries emitted at `max-width: 479/639/959/1199 px`).
- Per element: `top/left/width/height/fontsize` with `-res-320/480/640/960` overrides, `axisx/axisy`,
  `container` (`grid` = centered 1200 px container), units (`px`/`%`/`vh`/`vw`/`auto`), `heightmode`
  (`hug`/`fixed`/`window`), `imagefit`, `textfit`, `filewidth/fileheight`.
- Element types in use: `text`, `image`, `button`, `shape`.
- The page HTML also ships **per-record generated CSS** (`<style>` inside the record): base rules +
  `@media` blocks for all 5 breakpoints + `hover`/`animation` variants. Example: block
  `rec1914306861` = 58 KB CSS, 383 element rule sets.
- Runtime: `tilda-zero-1.1.min.js` (+ `tilda-zero-scale-1.0.min.js` when upscale=window on the published
  page; the editor API currently declares `tilda-zero-1.2.min.js`).

**Consequence:** geometry is fully declarative and machine-readable → a pixel-faithful port is
mechanizable (parse `data-field-*` → emit geometry), it is not a screenshot/tracing job.

### Volume (measured on captures)

| page | HTML | inline CSS | inline JS | Zero Block elements |
|---|---|---|---|---|
| `/` (118761336) | 718 KB | 426 KB | 9.5 KB | 2315 |
| `/ufa` (63388755) | 548 KB | 335 KB | 7.0 KB | 1917 |
| `/kazan` (57448733) | 497 KB | 289 KB | 8.1 KB | 1608 |
| `/partner` (60132875) | 170 KB | 98 KB | 7.3 KB | 564 |

≈ **6400 absolutely-positioned elements** total, plus 160 image assets (§5). Also shipped per page:
`tilda-blocks-page<pageid>.min.css` / `.min.js` on `static.tildacdn.com/ws/project11092055/`
(measured: `118761336` 29.9 KB + 9.4 KB, `57448733` 29.7 KB + 35.7 KB, `63388755` 12.9 KB + 0.5 KB,
`60132875` 23.2 KB + 8.9 KB, `122502036`/`122504626` 2.3 KB + 18 B) — the minified form of the same
generated CSS that is inlined into the HTML.

### Runtime libs actually needed

```
static.tildacdn.com/css/fonts-tildasans.css        TildaSans (project font)
static.tildacdn.com/css/tilda-grid-3.0.min.css     grid/container
static.tildacdn.com/css/tilda-animation-2.0.min.css  (only where data-animate-* is used — 3–4 attrs/page)
static.tildacdn.com/css/tilda-popup-1.1.min.css    popup (T702 / T1093)
static.tildacdn.com/css/tilda-forms-1.0.min.css    forms
static.tildacdn.com/js/tilda-scripts-3.0.min.js    core
static.tildacdn.com/js/tilda-zero-1.1.min.js       Zero Block runtime
static.tildacdn.com/js/tilda-lazyload-1.0.min.js
static.tildacdn.com/js/tilda-events-1.0.min.js     stat/analytics
static.tildacdn.com/js/tilda-menu-1.0.min.js       + tilda-menusub (menu)
static.tildacdn.com/js/tilda-popup-1.0.min.js
static.tildacdn.com/js/tilda-forms-1.0.min.js
static.tildacdn.com/js/tilda-phone-mask-1.1.min.js input masks
static.tildacdn.com/js/tilda-animation-2.0.min.js / tilda-animation-sbs-1.0.min.js
```
Per-page union of extra libs (from `getpage`): jslibs = `tilda-menu, tilda-menusub, tilda-zero-1.2,
tilda-popup, tilda-forms`; csslibs = `tilda-menusub, tilda-popup-1.1, tilda-forms`.

---

## 5. Assets & CDN

- Image URL: `https://static.tildacdn.com/<tild-hash>/<filename>`; `<tild-hash>` looks like
  `tild6330-3961-4232-b564-643732333362` and is a **stable opaque key** — keep it, don't rename.
- Transform API (verified 200): insert the op between hash and filename, **not** after the filename:
  - `https://static.tildacdn.com/<hash>/-/resize/400x/<name>.png` → 137 KB
  - `https://thb.tildacdn.com/<hash>/-/resize/20x/<name>.png` → 1.4 KB (this is what the page uses for
    lazy placeholders)
  - `https://<static|thb>.tildacdn.com/<hash>/<name>` → original (122–133 KB for the sample)
  - Appending the op after the filename (`…/<name>.jpg/-/resize/800x/`) → **404**.
- Inventory: 257 unique tildacdn URLs — 191 `static`, 65 `thb`, 1 `neo`; by type: 151 `.png`,
  50 `.jpg`, 24 `.svg`, 21 `.js`, 11 `.css`.
- **Canonical image set (deduplicated, transform variants collapsed to originals): 160 unique files.**
  The 65 `thb` URLs are 20-px lazy placeholders for art that already exists on `static` — do **not**
  download them separately.
- **Measured weight (HTTP `Content-Length`/real GET, 159 of 160 resolved): 34 275 292 B = 32.69 MiB**
  (32.7 MiB ≈ 34.3 MB).

| ext | files | total | avg |
|---|---|---|---|
| `.png` | 93 | 28.73 MiB | 316 KB |
| `.jpg` | 42 | 3.78 MiB | 92 KB |
| `.svg` | 24 | 0.18 MiB | 8 KB |

Spread: 74 files < 50 KB, 53 < 200 KB, 6 < 500 KB, 19 < 1 MiB, **7 files ≥ 1 MiB**
(`Mask_group.png` 2.83 MB, `Group_882.png` 1.35 MB, `Group_871.png` 1.16 MB, `Group_875.png` 1.10 MB,
`Group_943.png` 1.08 MB, `full_certificate.png` 1.07 MB, `Group_941.png` 1.04 MB).
Mean 211 KB, median 77 KB.

Per page (unique images *used by that page*; the union is the full 160):

| page | images | weight |
|---|---|---|
| `/` | 75 | 26.41 MiB |
| `/ufa` | 65 | 4.23 MiB |
| `/kazan` | 58 | 4.68 MiB |
| `/partner` | 21 | 1.56 MiB |
| `/13mart`, `/30mart` | 1 each | ~0 |

Note the heavy concentration: the home page carries 81 % of the image weight, mostly a handful of
multi-MB PNGs that are almost certainly over-sized for their rendered boxes — a port is a good moment
to re-encode (the originals must still be archived for fidelity).

### Other things to vendor

| item | size |
|---|---|
| `TildaSans-VF.woff2` (variable, weights 250–1000) | 83.4 KB |
| `TildaSans-VF.woff` (fallback) | 101.9 KB |
| `TildaSans-Regular.woff2` (static fallback) | 37.5 KB |
| `fonts-tildasans.css` | 0.4 KB (served gzip) |
| runtime JS/CSS libs (20 unique non-project files) | 379.4 KB unminified-on-wire total |
| per-page compiled bundles `tilda-blocks-page<id>.min.{js,css}` | 29.9+9.4, 29.7+35.7, 12.9+0.5, 23.2+8.9, 2.3+0.0 KB |

So a full offline archive is ≈ **33.5 MiB** (images + fonts + libs); a production build after
re-encoding could plausibly land in single-digit MB.

- Fonts: `fonts-tildasans.css` from `static.tildacdn.com` (TildaSans); no custom `@font-face` inline,
  no Typekit (`typekitid: ""`), no custom CSS file/text (`customcssfile`/`customcsstext` empty),
  `globalstyles_json: []`.

### Integrations / third-party (complete list found)

| Where | What |
|---|---|
| all pages | `https://ticketscloud.com/static/scripts/widget/tcwidget.js` (T131 block) — ticketing widget |
| `/kazan` | `https://670e665f9ab0d932c3a921f7.ticketscloud.org/e/67ebae8b9bed5a3b300fff8a?partner_id=…` (ticket link), `https://kzn.bfm.ru/`, `https://uralsib.ru/premium` |
| `/partner` | `https://wa.me/79625465556` |
| `/` | `https://lookatmoments.wfolio.pro/disk/lyudi-brendy-…`, `https://sheshegov.com/disk/30-03-2026-…`, `https://su1.ru/?utm_…`, `t.me/{bogner_ufa,marella_ufa,ultra_clinic_ufa}` |
| `/ufa` | `https://disk.yandex.ru/d/s4cASVgCKPSWDA` |

Forms: T702 popup (`id=form867410578` / `form841058158`), `method=POST`, `action=''`,
`data-formactiontype="0"`, `class="t-form js-form-proccess"`, `data-success-callback="t702_onSuccess"`,
`data-tilda-formskey="3fa9b449979d7bae7fdeae3611092055"`.
Fields: `Name`, `Phone` (`tilda-phone-mask`, rule `phone`), `Input` ("Какую организацию представляете?").
No external form services (comment `<!-- NO ONE SERVICES CONNECTED -->`) → posts to Tilda's own handler;
the exact submission URL is inside the minified runtime and was **not** located in
`tilda-forms-1.0.min.js` / `tilda-scripts-3.0.min.js` by string search. `[INFERENCE]` Tilda's backend
handles the POST on the page URL itself (hence `action=''`); needs confirmation at implementation time.

Analytics: only `window.dataLayer = []` on every page; no GA/GTM/Metrika/VK pixel IDs found inline.
Tilda's own counters ship as `tilda-stat-1.0.min.js` (3.7 KB, project statistics — drop in a port;
its upload URL is not plaintext in the bundle).

404: `page404id: 0` → Tilda's default page (`404 Page Not Found.`, HTTP 404, no project branding).
Duplicate index path: `/page118761336.html` also returns `200` with the same content as `/`;
canonical is `https://lyudi-brendy.ru` — emit a redirect or canonical tag in the port.
Published pages carry `data-tilda-lazy="yes"`, `data-tilda-root-zone="com"`,
`data-tilda-project-id="11092055"`, `data-tilda-project-country="RU"`.

robots.txt disallows `/tilda/{form,rec,click,scroll,popup,cart,product,event}*` and points to
`sitemap.xml`. Sitemap lists exactly the 6 pages, `lastmod` 2026-02-18 … 2026-04-06.

---

## 6. Code export — **blocked on this plan**

Tilda's own export is gated by plan. In `td-p-all.min.js` the export links are rendered as `<span>`
(disabled UI) when `plan == 0 || plan == 1`; the strings say
`Export features available only on Business plan`. Account `plan = 1` (**Personal**).

Live check: `GET /projects/exporttozip/?projectid=11092055` and
`GET /projects/pageexport/?projectid=11092055&pageid=118761336&getcode=yes` both return `200 text/html`
— the *settings page shell*, not a ZIP; nothing to download.

Also found: `comm:pagepublish`? no — `pageexport` requires `getcode=yes` and, per the UI code,
`plan ≥ 2`. Conclusion: **no supported ZIP export for this account.** Do not count on it; either
upgrade to Business (paid) or reconstruct from §3.2 + §4 (which is fully sufficient).

---

## 7. Migration strategy

The site is a static Tilda page set. Three viable levels of fidelity/maintainability:

**A. Static mirror (lowest risk, lowest value).** Snapshot the published HTML + generated CSS/JS +
downloaded assets and serve as-is. Guarantees pixel parity, keeps `hash`-free operation, but carries
~700 KB HTML/page, ~100 KB of Tilda runtime JS, jQuery-free but still Tilda-bound, and no component
structure. Good as a *safety net / reference*, bad as the deliverable.

**B. Structured re-generation (recommended).** Parse `data-field-*` + per-record CSS into a neutral
JSON model per page (element → type, box + per-breakpoint overrides, styles, asset, link/action),
then codegen static output. Fidelity comes for free because geometry is declarative; the result is
plain CSS/HTML (or components) with no Tilda runtime. Evidence for feasibility: §4 volumes are finite
(≈6400 elements) and every geometry field is a DOM attribute; hover/animation variants live in the
record CSS that ships with the same JSON.

**C. Hybrid.** B for the Zero Blocks, purpose-built components for the interactive bits that should
not be re-ported verbatim: header menu, T702 popup form (+ its submit path), TicketsCloud widget,
T390 buttons, `t270` anchors.

Recommendation: **B + C**, with A captured first as the pixel-diff baseline. Open product decisions
(framework/stack, hosting, whether the Tilda CMS is dropped or kept for the owner, form handling,
ticketing integration) are not answered yet — ask before building.

Risks to plan for:
1. **Breakpoints** `320/480/640/960/1200` must all be reproduced (4 override levels per field).
2. Zero Block `upscale="window"` / `grid` changes how widths resolve — reproduce from the artboard attrs,
   not from the rendered screenshot.
3. `tilda-lazyload` placeholder/threshold behaviour, and `thb` 20px thumbs, must be normalized (the
   `/-/resize/20x/` URLs are placeholders, not the real art) — otherwise the port bakes in 1.4 KB images.
4. The T702 form's submit target is unresolved (§5) — the form must be re-pointed at whatever backend we
   choose anyway.
5. Expired domain id `278916` in the account — check it isn't a domain the site still depends on.
6. Legal/asset: 160 image files live on Tilda's CDN under the project's keys; download them into the
   repo before Tilda-side changes (or an account lapse) can break them.

---

## 8. Reproduce the captures

The committed JSON captures in `docs/captures/` are **sanitized**: `errors_jwtsign`, `jwt_ai`,
`Tildaupload_UPLOADKEY`, `Tildaupload_PUBLICKEY`, `Tildavideoupload_UPLOADKEY`, `csrf` and
`useruploadkey` are replaced with `"REDACTED"`. Cookie jars, session hashes and HAR files are never
committed — keep them in `/tmp` or outside the repo.

```bash
# session: take hash/userid/PHPSESSID from a fresh HAR of tilda.ru/projects/
# the cookie jar lives outside the repo and is never committed
JAR=/tmp/tilda-jar.txt                             # netscape format
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36'

# projects + csrf
curl -s -b $JAR -c $JAR -A "$UA" -H 'Referer: https://tilda.ru/projects/' \
     https://tilda.ru/projects/get/getprojects/

# page list of the project
curl -s -b $JAR -c $JAR -A "$UA" -H 'Referer: https://tilda.ru/projects/' \
     --data-urlencode comm=getprojectslist --data-urlencode projectid=11092055 \
     https://tilda.ru/projects/get/getprojects/

# full page source JSON (repeat per pageid)
for pid in 118761336 57448733 63388755 60132875 122502036 122504626; do
  curl -s -b $JAR -c $JAR -A "$UA" -H "Referer: https://tilda.ru/page/?pageid=$pid" \
       --data-urlencode "pageid=$pid" --data-urlencode viewtrash= --data-urlencode minify= \
       https://tilda.ru/page/get/getpage/ -o "pages-json/$pid.json"
done

# published pages + asset list
curl -s -A "$UA" https://lyudi-brendy.ru/sitemap.xml
```

Gotchas that cost time here:
- `curl -L -c jar` on a `tilda.cc/detectdomain/` redirect **overwrites the jar** and can kill the session
  mid-run; keep a pristine copy of the jar.
- Unquoted `$UA` in a shell function splits on spaces → curl treats each word as a URL and returns
  `http=000` noise.
- `tplid` in the JSON is an **int**; `data-record-type` in published HTML is the same number as a string.
- `TD_PUBLISHED_BUNDLES`: dashboard bundles are versioned (`?v=v26100705`, editor `?v=v26100701`).
  Endpoint names are stable but re-grep the bundles if a call starts returning "Unknown command".
