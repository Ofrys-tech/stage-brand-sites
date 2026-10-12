# stage-brand-sites

Custom websites for performers, artists, and stage productions.

## Люди Бренды — hub page

Static replacement for the Tilda site `lyudi-brendy.ru`. The hub is the new root page:
it lists the three spectacles and the partner call-to-action, and carries the contact details.

Run it:

```bash
python3 -m http.server 8777        # then open http://127.0.0.1:8777/
```

No build step, no dependencies. Deploy = serve this directory (the repo root) as the web root.

### Structure

```
index.html                     hub page
assets/css/main.css            all styles + design tokens
assets/js/main.js              mobile menu, scroll reveal, year (no dependencies)
assets/fonts/TildaSans-VF.woff2
assets/img/logo.svg            «ЛЮДИ БРЕНДЫ» wordmark (from the Tilda project)
assets/img/accent-circle.svg   red roundel (#da3036)
assets/img/grid.svg            thin #373737 grid ornament
assets/img/ring.png            white ring ornament (hero)
assets/img/portrait.png        monochrome portrait (hero)
assets/img/og.png              1200×630 link preview
docs/tilda.md                  Tilda account/API/migration reconnaissance
docs/captures/                 raw captured source of the Tilda project (11092055)
```

### Design tokens (measured from the live Tilda site)

| token | value |
|---|---|
| background | `#202020`, deep `#0a0a0a`, header `#1a1a1a`, card `#171717` |
| hairlines | `#373737`, `#323232` |
| text | `#ffffff`; muted `#acacac`, `#a6a6a6`, `#949494` |
| accent | `#da3036` (soft `#ec777b`) |
| radius | pills 30–50px, cards 20px |
| type | TildaSans; display 42px/300 uppercase in accent, body 20px/300, labels 20px/400 muted, values 20px/700 accent, buttons 18px/600 |
| container | 1200px (1160px content) |
| motion | 0.2s ease-in-out transitions, matching Tilda's `--t396-speedhover` |

### Page inventory / links

| card | target |
|---|---|
| Уфа 2024 | `/ufa` |
| Казань 2025 | `/kazan` |
| Уфа 2026 | `/ufa-2026` |
| «Стать партнёром» | `/partner` |

Contacts (from `lyudi-brendy.ru` footer): `+7 993 342-12-73`, `Dir-ufa@mail.ru`,
ИП Злобина Инна Сергеевна, индекс 450091, г. Уфа, Карла Маркса, 58.

### Open decisions

- `/ufa-2026` is a **new slug**: that spectacle currently occupies `/` in Tilda. The hub takes `/`,
  so the spectacle needs its own path (and a redirect from the old one at cutover).
- Spectacle cards are ordered chronologically (01 Уфа 2024 → 02 Казань 2025 → 03 Уфа 2026);
  reordering is a matter of moving the three `<li>` blocks.
- `og:image` is relative; switch it to an absolute production URL once the domain is fixed.
- TildaSans is Tilda's own typeface, vendored here from their CDN so the site no longer depends on
  `tildacdn.com` at runtime. Confirm the licence before publishing.
- Remaining Tilda pages (kazan, ufa, ufa-2026, partner) still need porting — see `docs/tilda.md`.
