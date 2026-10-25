#!/usr/bin/env python3
"""Port the captured Tilda pages into self-hosted static pages.

Source: docs/captures/tilda-11092055/published-html/*.html (verbatim snapshots)
Output: <route>/index.html with every CDN reference rewritten to a local asset.

The captured HTML already contains the full generated Zero Block CSS inline, so a
page stays pixel-identical as long as the base libraries, the per-page blocks
bundle and the images are served locally. That is all this script does — it never
touches layout, except for the deliberate patches listed below.

    python3 tools/port_tilda.py plan     # print the asset lists to fetch
    python3 tools/port_tilda.py build    # write <route>/index.html
"""

import hashlib
import os
import re
import sys
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURES = os.path.join(ROOT, "docs", "captures", "tilda-11092055", "published-html")

# source capture -> route directory -> canonical Tilda URL (for reference only)
PAGES = [
    ("index.html", "ufa-2026", "https://lyudi-brendy.ru/"),
    ("ufa.html", "ufa", "https://lyudi-brendy.ru/ufa"),
    ("kazan.html", "kazan", "https://lyudi-brendy.ru/kazan"),
    ("partner.html", "partner", "https://lyudi-brendy.ru/partner"),
]

IMG_DIR = "assets/img/tilda"
LIB_DIR = "assets/tilda"

# Telemetry only, never needed for rendering.
DROP_SCRIPTS = [
    "https://neo.tildacdn.com/js/tilda-fallback-1.0.min.js",
    "https://static.tildacdn.com/js/tilda-stat-1.0.min.js",
]

# Decorative 3600x420 stadium outlines that stick out of the viewport.
# Removing the 1px border keeps the faint panel fill but removes the arc.
# The two outlines that used to cross the partner block on the root page are gone
# from that page entirely (see PARTNER_DECOR).
STADIUM_IDS = {
    "index.html": ["1730353345862"],
    "ufa.html": ["1730353296026", "1730353345862"],
    "kazan.html": ["1730353296026", "1730353345862"],
    "partner.html": ["1730353296026", "1730353345862"],
}

# Decorative shapes that paint over the partner block on the root page: both are
# 3600px stadium panels parked on the section boundary, and their rounded ends land
# on content (measured at 1440px):
#   1730353296026        880..4480 x 1770..1972 -> «Красный ключ» card 222x47, its
#                        logo 210x31, the «Наши партнеры» heading 75x52
#   1773398078166000002  -3263..337 x 1759..1961 -> first logo card 3x36
PARTNER_DECOR = {
    "index.html": ["1730353296026", "1773398078166000002"],
}

LINK_MAP = {
    "/kazan": "../kazan/",
    "/ufa": "../ufa/",
    "/ufa-2026": "../ufa-2026/",
    "/partner": "../partner/",
}

# Spectacle-to-spectacle links are redundant now that the hub owns navigation.
# The header menu items are deleted, the Zero Block buttons are hidden via CSS.
CROSS_ROUTES = ("../kazan/", "../ufa/", "../ufa-2026/")

# In-page anchor targets, per page (Tilda copied the Kazan ids into the other pages,
# which left "О спектакле" / "Партнеры" / "Актеры" dead).
NAV_TARGETS = {
    "index.html": {"about": "rec1914306871", "partners": "rec1914306881", "actors": "rec1914306891"},
    "ufa.html": {"about": "rec867373853", "partners": "rec867373854", "actors": "rec867373855"},
    "kazan.html": {"about": "rec819069608", "partners": "partners", "actors": "rec819096772"},
    "partner.html": {"about": "rec841045060", "partners": "rec841045061"},
}
LEGACY_ANCHORS = {
    "#rec819069608": "about",
    "#rec819093951": "partners",
    "#rec819096772": "actors",
}
# The "ПОДРОБНЕЕ" roundel on the old root page opened the photo popup instead of
# scrolling down; send it to the "О спектакле" section like on the other pages.
ROUNDEL_FIX = {"index.html": {"1730353388260": "about"}}

# Bottom plaque on the spectacle pages: date pill, time pill and the photo button.
# Same element ids on all three pages, different footer records.
# /ufa-2026/: «Смотреть фото» goes straight to report 2; the report chooser popup
# (record rec2124454941, holding «Фотоотчёт 1» and «Фотоотчёт 2») is deleted.
PHOTO_LINK = {
    "index.html": (
        "1730353109947",
        "https://sheshegov.com/disk/30-03-2026-blagotvoritelnyy-spektakl-lyudi-i-brendy-7qctt7",
    )
}
DROP_RECORDS = {"index.html": ["rec2124454941"]}

# Kazan hero: date/time/ticket buttons at the top right.
EXTRA_HIDE = {
    "kazan": ("rec819063241", ["1739783125890", "1739783086566", "1730353109947"]),
}

FOOTER_DROP = {
    "index.html": (
        "rec1914306901",
        ["1730363799998", "1730363799994", "1730363799990", "1730363626329"],
    ),
    "ufa.html": (
        "rec867373856",
        ["1730363799998", "1730363799994", "1730363799990", "1730363626329"],
    ),
    "kazan.html": (
        "rec819137808",
        ["1730363799998", "1730363799994", "1730363799990", "1730363626329"],
    ),
    # the partner page only has the «Стать партнером» button and its 300x231 plaque
    "partner.html": ("rec841045063", ["1730363799990", "1730363626329"]),
}

# Footer contacts: phone/email become real links, street addresses open a map.
PHONE = ("1730363682952", "+7 993 342-12-73", "tel:+79933421273")
EMAIL = ("1730363704507", "Dir-ufa@mail.ru", "mailto:Dir-ufa@mail.ru")
# element id -> map query (city is added where the atom only carries the street)
MAP_LINKS = {
    "index.html": {"1730363758756": "Уфа, ул. Заки Валиди, 2"},
    "ufa.html": {"1730363758756": "Уфа, ул. Заки Валиди, 34"},
    "kazan.html": {
        "1730363758756": "Казань, ул. Николая Ершова, 57А",
        "1740986464647": "Казань, КЦ Сайдаш, Ершова, 57а",
    },
    "partner.html": {},
}
IP_ATOM = "1730363734622"

# Back-to-hub pill sits in the nav row, left of "О спектакле"; the nav buttons are
# pushed right by this much so nothing overlaps.
HOME_SHIFT = 170
NAV_TARGETS_BY_ROLE = ("about", "partners", "actors")

# /ufa/: «Смотреть фото» stood at the far right of the hero and left a 342px hole
# after «Актеры». Pull it into the nav row with a 20px gap. Both elements switch to
# the <=1199 breakpoint layout, so the measured gap is 342px from 1200px up and
# 210px at 960..1199 — the pull is the gap minus the 20px target.
NAV_PULL = {
    "ufa": {"rec": "rec867373852", "elem": "1730353109947", "wide": -322, "narrow": -190},
    # /partner/: «Стать партнером» 20px right of «Партнеры»
    "partner": {"rec": "rec841045059", "elem": "1730353109947", "wide": -394, "narrow": -174},
}

HOME_BUTTON = (
    '<a class="lb-home" href="../" aria-label="На главную страницу">'
    '<span class="lb-home__arrow" aria-hidden="true">←</span>'
    '<span class="lb-home__text">На главную</span></a>'
)

IMG_EXT = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".avif")
URL_RE = re.compile(r"""https://(?:static|thb|optim)\.tildacdn\.com/[^"'\s)\\]*""")
LIB_RE = re.compile(r"""https://(?:neo|static)\.tildacdn\.com/[^"'\s)]*\.(?:js|css)(?:\?[^"'\s)]*)?""")
ANCHOR_RE = re.compile(r"""<a\b([^>]*?)href="([^"]*)"([^>]*)>(.*?)</a>""", re.S)
THEME_RE = re.compile(r"^(?:tel|mailto|whatsapp|javascript|data|sms):", re.I)


def strip_query(url):
    return url.split("?")[0]


# The partner thank-you letter was replaced by a corrected 4K version: the word
# «Уважаемый» became «Уважаемая» and the scan was re-rendered at 2704x3840.
# Stored as WebP (0.6 MB instead of a 12 MB PNG), so the reference is renamed.
RENAMES = {
    "full_certificate.png": "full_certificate.webp",
    "pr.png": "pr.webp",  # clickable preview of the same letter
}


def image_local(url):
    """static.tildacdn.com/<hash>/<name> and thb/.../-/resize/20x/<name> -> one file."""
    clean = strip_query(url)
    m = re.match(r"https://(?:static|thb|optim)\.tildacdn\.com/([^/]+)/(?:.+/)?([^/]+)$", clean)
    if not m:
        return None
    digest, name = m.group(1), m.group(2)
    name = RENAMES.get(name, name)
    return f"../{IMG_DIR}/{digest}/{name}"


def lib_local(url):
    clean = strip_query(url)
    if clean.endswith("css/fonts-tildasans.css"):
        return f"../{LIB_DIR}/fonts.css"
    name = clean.rsplit("/", 1)[-1]
    return f"../{LIB_DIR}/{name}"


def collect(html):
    images, libs = set(), set()
    for url in URL_RE.findall(html):
        if strip_query(url).lower().endswith(IMG_EXT):
            local = image_local(url)
            if local:
                images.add((url, local))
    for url in LIB_RE.findall(html):
        libs.add((url, lib_local(url)))
    return sorted(images), sorted(libs)


def map_href(href, inner):
    if href.startswith("#") or THEME_RE.match(href):
        return href
    m = re.match(r"^(?:https?:)?//lyudi-brendy\.ru(/[^?#]*)?(\?[^#]*)?$", href)
    if m:
        path = (m.group(1) or "/").rstrip("/") or "/"
        query = m.group(2) or ""
    elif href.startswith("/"):
        path = href.split("?")[0].rstrip("/") or "/"
        query = ""
    else:
        return href

    if path == "/":
        return "../ufa-2026/" if "2026" in inner else "../"
    if path in LINK_MAP:
        return LINK_MAP[path] + query
    # unknown route (ad stubs etc.) — leave pointing at the live site
    return href


def remap_anchors(html, page):
    """Rewrite links, then repair the in-page anchors Tilda left pointing at Kazan."""
    targets = NAV_TARGETS.get(page, {})
    roundels = ROUNDEL_FIX.get(page, {})
    counters = {"elem": None}

    def repl(m):
        before, href, after, inner = m.group(1), m.group(2), m.group(3), m.group(4)
        href = map_href(href, inner)
        role = LEGACY_ANCHORS.get(href)
        if role and role in targets:
            href = "#" + targets[role]
        return f'<a{before}href="{href}"{after}>{inner}</a>'

    html = ANCHOR_RE.sub(repl, html)

    # the roundel is an image inside its own anchor; patch it by element id
    for elem_id, role in roundels.items():
        target = targets.get(role)
        if not target:
            continue
        pattern = re.compile(
            r"(<div class='t396__elem tn-elem[^']*' data-elem-id='%s'[^>]*>\s*<a class='tn-atom' href=\")[^\"]*(\")"
            % re.escape(elem_id)
        )
        html = pattern.sub(lambda m: m.group(1) + "#" + target + m.group(2), html)
    return html


def remove_element(html, elem_id):
    """Delete a whole Zero Block element (its <div class='t396__elem …'> subtree)."""
    pos = html.find("data-elem-id='%s'" % elem_id)
    if pos < 0:
        return html
    start = html.rfind("<div class='t396__elem", 0, pos)
    if start < 0:
        return html
    depth = 0
    for m in re.finditer(r"<div\b|</div>", html[start:]):
        if m.group(0) == "</div>":
            depth -= 1
            if depth == 0:
                return html[:start] + html[start + m.end():]
        else:
            depth += 1
    return html


def remove_record(html, rec_id):
    """Delete a whole Tilda block: <div id="recN" class="r t-rec" …> … </div>."""
    start = html.find('<div id="%s" class="r t-rec"' % rec_id)
    if start < 0:
        return html
    depth = 0
    for m in re.finditer(r"<div\b|</div>", html[start:]):
        if m.group(0) == "</div>":
            depth -= 1
            if depth == 0:
                return html[:start] + html[start + m.end():]
        else:
            depth += 1
    return html


def repoint_button(html, elem_id, url):
    """Point a Zero Block button element at an external URL instead of a popup."""
    pos = html.find("data-elem-id='%s'" % elem_id)
    if pos < 0:
        return html
    m = re.search(r"""<a class='tn-atom' href="[^"]*"([^>]*)>""", html[pos: pos + 3000])
    if not m:
        return html
    absolute = pos + m.start()
    tag = m.group(0)
    new = re.sub(r'href="[^"]*"', 'href="%s" target="_blank" rel="noopener noreferrer"' % url, tag, count=1)
    return html[:absolute] + new + html[absolute + len(tag):]


def strip_dead_css(html, ids):
    """Remove the generated CSS rules of deleted elements (they keep the payload small)."""
    for elem_id in ids:
        html = re.sub(
            r'#rec\d+ \.tn-elem\[data-elem-id="%s"\][^{}]*\{[^{}]*\}\s*' % re.escape(elem_id),
            "",
            html,
        )
    return html


def strip_cross_links(html):
    """Delete cross-spectacle menu items and collect the Zero Block buttons to hide."""
    for route in CROSS_ROUTES:
        html = re.sub(
            r'<li[^>]*>\s*<a[^>]*href="%s"[^>]*>.*?</li>\s*' % re.escape(route),
            "",
            html,
            flags=re.S,
        )

    hidden = set()
    pattern = re.compile(
        r"""<a class='tn-atom' href="(?:%s)\"""" % "|".join(re.escape(r) for r in CROSS_ROUTES)
    )
    while True:
        m = pattern.search(html)
        if not m:
            break
        elem = re.findall(r"data-elem-id='(\d+)'", html[: m.start()])
        if not elem:
            break
        hidden.add(elem[-1])
        html = remove_element(html, elem[-1])
    return html, hidden


def nav_geometry(html, page):
    """Base and <=1199 `left` of the "О спектакле" hero button, plus the hero record id."""
    targets = NAV_TARGETS.get(page, {})
    if "about" not in targets:
        return None
    about_id = None
    # the about target is a record, not the button: find the button that links to it
    for m in re.finditer(r"data-elem-id='(\d+)'[^>]*data-elem-type='button'", html):
        tail = html[m.end(): m.end() + 900]
        if 'href="#%s"' % targets["about"] in tail:
            about_id = m.group(1)
            break
    if about_id is None:
        return None
    rule = re.search(r'#(rec\d+) \.tn-elem\[data-elem-id="%s"\]\{[^}]*?left:(calc\([^)]*\)|[-\d.]+px)' % about_id, html)
    if not rule:
        return None
    hero_rec = rule.group(1)
    base_left = rule.group(2)
    media = re.search(
        r'@media screen and \(max-width:1199px\)\{#%s \.tn-elem\[data-elem-id="%s"\]\{[^}]*?left:(calc\([^)]*\)|[-\d.]+px)'
        % (hero_rec, about_id),
        html,
    )
    small_left = media.group(1) if media else None
    return {"rec": hero_rec, "about": about_id, "base_left": base_left, "small_left": small_left}


ATOM_RE = r"""<div class=['"]tn-atom['"]\s*field=['"]tn_text_%s['"]>(.*?)</div>"""


def link_atom(html, elem_id, render):
    """Replace the inner markup of one text atom (matched by its unique field name)."""
    pattern = re.compile(ATOM_RE % re.escape(elem_id), re.S)
    return pattern.sub(lambda m: m.group(0).replace(m.group(1), render(m.group(1)), 1), html, count=1)


def fix_contacts(html, page):
    # phone
    phone_id, phone_text, phone_href = PHONE
    html = link_atom(
        html,
        phone_id,
        lambda _: '<a class="lb-link" href="%s">%s</a>' % (phone_href, phone_text),
    )
    # email
    email_id, email_text, email_href = EMAIL
    html = link_atom(
        html,
        email_id,
        lambda _: '<a class="lb-link" href="%s">%s</a>' % (email_href, email_text),
    )
    # street -> map
    for elem_id, query in MAP_LINKS.get(page, {}).items():
        url = "https://yandex.ru/maps/?text=" + quote(query)
        html = link_atom(
            html,
            elem_id,
            lambda inner, url=url: '<a class="lb-link" href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
            % (url, inner.strip()),
        )
    # address punctuation: no dot before a comma, no dot at the end of the line
    def tidy(inner):
        inner = re.sub(r"\.(?=\s*,)", "", inner)
        inner = re.sub(r"\.\s*$", "", inner)
        return inner

    html = link_atom(html, IP_ATOM, tidy)
    return html


def add_home_button(html):
    """The T456 header on these pages is an empty 0x0 placeholder (all navigation lives
    in the hero Zero Block), so the back button is placed in the hero artboard."""
    m = re.search(r'<div class="t396__artboard"[^>]*>', html)
    if not m:
        return html
    return html[: m.end()] + HOME_BUTTON + html[m.end():]


MOBILE_HOME = (
    '<a class="lb-home-mobile" href="../">'
    '<span aria-hidden="true">←</span> На главную</a>'
)

MOBILE_MENU_SCRIPT = (
    '<script src="../assets/js/tilda-mobile-menu.js?v=20261025a" defer></script>\n'
)

# Tilda renders every visible title as an absolutely positioned div, so the ported
# pages have no heading for assistive tech. Keep one in the document, out of flow.
PAGE_H1 = {
    "index.html": "Документальный благотворительный спектакль «Люди Бренды» в Уфе — 2026",
    "ufa.html": "Документальный благотворительный спектакль «Люди Бренды» в Уфе",
    "kazan.html": "Документальный благотворительный спектакль «Люди Бренды» в Казани",
    "partner.html": "Стать партнёром проекта «Люди Бренды»",
}

SR_ONLY = (
    "position:absolute;width:1px;height:1px;margin:-1px;padding:0;"
    "overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);"
    "white-space:nowrap;border:0"
)


def add_page_heading(html, page):
    title = PAGE_H1.get(page)
    if not title:
        return html
    m = re.search(r"<body\b[^>]*>", html)
    if not m:
        return html
    h1 = '<h1 style="%s">%s</h1>' % (SR_ONLY, title)
    return html[: m.end()] + h1 + html[m.end():]


def add_mobile_home(html):
    """The back pill is desktop-only; phones get the same link at the top of the
    Tilda mobile menu, which is the only navigation surface on narrow screens."""
    m = re.search(
        r'<div\b[^>]*class="[^"]*tmenu-mobile__menucontent_hidden[^"]*"[^>]*>', html
    )
    if not m:
        return html
    return html[: m.end()] + MOBILE_HOME + html[m.end():]


SITE_CSS_MARKER = "<!--site-css-->"


def link_site_css(html, route):
    """Placeholder: main() replaces it with the real tag once the CSS is generated,
    including a content hash so browsers never keep a stale stylesheet."""
    return html.replace("</head>", SITE_CSS_MARKER + "\n</head>", 1)


def site_css(route, nav, hidden, footer_drop):
    nav = nav or {}
    left = nav.get("base_left", "calc(50% - 600px + 197px)")
    small_left = nav.get("small_left")
    css = [
        f"/* Generated by tools/port_tilda.py for /{route}/ — do not edit by hand. */",
        "",
        "/* tel/mailto/map links inside text atoms keep the inherited look */",
        ".t396 .tn-atom a.lb-link {",
        "\tcolor: inherit !important;",
        "\ttext-decoration: underline !important;",
        "\ttext-decoration-thickness: 1px !important;",
        "\ttext-underline-offset: 3px !important;",
        "\ttext-decoration-color: rgba(172, 172, 172, 0.5) !important;",
        "\ttransition: text-decoration-color 0.2s ease-in-out;",
        "}",
        "",
        ".t396 .tn-atom a.lb-link:hover,",
        ".t396 .tn-atom a.lb-link:focus-visible { text-decoration-color: #da3036 !important; }",
        "",
        "/* smooth scrolling for the in-page anchors (ПОДРОБНЕЕ, О спектакле, ...) */",
        "html { scroll-behavior: smooth; }",
        "@media screen and (prefers-reduced-motion: reduce) {",
        "\thtml { scroll-behavior: auto; }",
        "}",
        "",
        "/* back-to-hub pill: same look as the «Смотреть фото» button, left of «О спектакле» */",
        ".lb-home {",
        "\tposition: absolute;",
        "\ttop: 11px;",
        f"\tleft: {left};",
        "\twidth: 154px;",
        "\theight: 52px;",
        "\tz-index: 900;",
        "\tdisplay: inline-flex;",
        "\talign-items: center;",
        "\tjustify-content: center;",
        "\tgap: 6px;",
        "\tborder: 0;",
        "\tborder-radius: 30px;",
        "\tbackground: #da3036;",
        "\tcolor: #fff !important;",
        "\tfont-family: 'TildaSans', Arial, sans-serif;",
        "\tfont-size: 17px;",
        "\tfont-weight: 600;",
        "\tline-height: 1;",
        "\twhite-space: nowrap;",
        "\ttext-decoration: none;",
        "\ttransition: background-color 0.2s ease-in-out;",
        "}",
        "",
        ".lb-home:hover,",
        ".lb-home:focus-visible { background: #c92b31; }",
        "",
        ".lb-home__arrow { font-size: 17px; line-height: 1; }",
        "",
    ]
    if small_left:
        css += ["@media screen and (max-width: 1199px) {", f"\t.lb-home {{ left: {small_left}; }}", "}", ""]
    css += [
        "/* the back pill belongs to the desktop nav row; phones get the same link",
        "   at the top of the Tilda mobile menu instead of a button over the content */",
        "@media screen and (max-width: 959px) {",
        "\t.lb-home { display: none; }",
        "}",
        "",
        ".lb-home-mobile {",
        "\tdisplay: block;",
        "\tpadding: 16px 20px;",
        "\tbackground: #1a1a1a;",
        "\tborder-bottom: 1px solid rgba(255, 255, 255, 0.12);",
        "\tcolor: #fff !important;",
        "\tfont-family: 'TildaSans', Arial, sans-serif;",
        "\tfont-size: 17px;",
        "\tfont-weight: 600;",
        "\tline-height: 1.4;",
        "\ttext-decoration: none;",
        "\ttransition: color 0.2s ease-in-out, background-color 0.2s ease-in-out;",
        "}",
        "",
        ".lb-home-mobile:hover,",
        ".lb-home-mobile:focus-visible { color: #da3036 !important; background: #222; }",
        "",
        "/* Tilda's mobile header ends at 980px, but the Zero Block nav row with the",
        "   back pill takes over at 960px; hide the duplicate bar between the two */",
        "@media screen and (min-width: 960px) and (max-width: 980px) {",
        "\t.t-screenmax-980px { display: none !important; }",
        "}",
        "",
        "/* phones: the Tilda menu becomes a full-screen sheet and locks the page",
        "   behind it instead of a short dropdown that scrolls away with the header */",
        "@media screen and (max-width: 980px) {",
        "\t.tmenu-mobile__menucontent_hidden {",
        "\t\tposition: fixed !important;",
        "\t\ttop: 64px !important;",
        "\t\tright: 0 !important;",
        "\t\tbottom: 0 !important;",
        "\t\tleft: 0 !important;",
        "\t\theight: auto !important;",
        "\t\toverflow-y: auto;",
        "\t\tz-index: 989;",
        "\t}",
        "\tbody:has(.tmenu-mobile_opened) { overflow: hidden; }",
        "}",
        "",
        "/* make room for the pill in the desktop nav row */",
    ]
    if nav.get("rec") and nav.get("about"):
        css.append("@media screen and (min-width: 960px) {")
        css.append(f'\t#{nav["rec"]} .tn-elem[data-elem-id="{nav["about"]}"] {{ margin-left: {HOME_SHIFT}px; }}')
        for role in ("partners", "actors"):
            eid = nav.get("elem_" + role)
            if eid:
                css.append(f'\t#{nav["rec"]} .tn-elem[data-elem-id="{eid}"] {{ margin-left: {HOME_SHIFT}px; }}')
        css.append("}")
        css.append("")
    pull = NAV_PULL.get(route)
    if pull:
        css += [
            "/* «Смотреть фото» joins the nav row right after «Актеры» */",
            "@media screen and (min-width: 960px) {",
            f'\t#{pull["rec"]} .tn-elem[data-elem-id="{pull["elem"]}"] {{ margin-left: {pull["narrow"]}px; }}',
            "}",
            "@media screen and (min-width: 1200px) {",
            f'\t#{pull["rec"]} .tn-elem[data-elem-id="{pull["elem"]}"] {{ margin-left: {pull["wide"]}px; }}',
            "}",
            "",
        ]
    css.append("/* spectacle-to-spectacle buttons, the footer plaque and the kazan ticket block"
               " are deleted from the markup by tools/port_tilda.py */")
    return "\n".join(css) + "\n"


def port(html, page, route):
    images, libs = collect(html)

    # 1. telemetry scripts and CDN prefetch hints — drop the whole tag
    for url in DROP_SCRIPTS:
        html = re.sub(r"<script\b[^>]*" + re.escape(url) + r"[^>]*>\s*</script>\s*", "", html)
    html = re.sub(r'<link[^>]*rel="dns-prefetch"[^>]*tildacdn[^>]*>\s*', "", html)
    # dead reference left in the Tilda project: /script.js does not exist (404 on the live site too)
    html = re.sub(r'<script[^>]*src="script\.js[^"]*"[^>]*>\s*</script>\s*', "", html)

    # 2. libraries and images -> local, longest URL first so no prefix eats a suffix
    for url, local in sorted(libs + images, key=lambda x: -len(x[0])):
        html = html.replace(url, local)

    # 3. links + in-page anchors
    html = remap_anchors(html, page)

    # 4. drop cross-spectacle navigation
    html, hidden = strip_cross_links(html)

    # 5. contacts: tel/mailto links, map links, address punctuation
    html = fix_contacts(html, page)

    # 6. home button + our stylesheet (contains the hide rules for steps 4 and 9)
    nav = nav_geometry(html, page)
    if nav:
        for role in ("partners", "actors"):
            target = NAV_TARGETS.get(page, {}).get(role)
            if not target:
                continue
            for m in re.finditer(r"data-elem-id='(\d+)'[^>]*data-elem-type='button'", html):
                if 'href="#%s"' % target in html[m.end(): m.end() + 900]:
                    nav["elem_" + role] = m.group(1)
                    break
    html = add_home_button(html)
    html = add_mobile_home(html)
    html = link_site_css(html, route)

    # 7. strip the protruding stadium outlines (border only, fill stays)
    for elem_id in STADIUM_IDS.get(page, []):
        html = re.sub(
            r'(#rec\d+ \.tn-elem\[data-elem-id="%s"\] \.tn-atom\{[^}]*?)--t396-borderwidth:\s*1px'
            % re.escape(elem_id),
            r"\1--t396-borderwidth:0px",
            html,
        )

    # 8. native lazy loading below the first screen (hero stays eager, popups stay eager
    #    so nothing pops in half-loaded when the dialog opens)
    seen = [0]

    def lazy_segment(part, allow):
        def repl(m):
            seen[0] += 1
            if not allow or seen[0] <= 4 or "loading=" in m.group(1):
                return m.group(0)
            return '<img loading="lazy" decoding="async"' + m.group(1) + ">"

        return re.sub(r"<img\b([^>]*)>", repl, part)

    segments = re.split(r"(?=<div id=\"rec\d+\" class=\"r t-rec\")", html)
    popup_records = set()
    for ids in re.findall(r'data-popup-rec-ids="([0-9,]+)"', html):
        popup_records.update(i for i in ids.split(",") if i)

    def segment_allows(seg):
        if "t-popup" in seg:
            return False
        m = re.match(r'<div id="rec(\d+)"', seg)
        return not (m and m.group(1) in popup_records)

    html = "".join(lazy_segment(seg, segment_allows(seg)) for seg in segments)

    # 8b. delete (not just hide) the blocks we do not want, plus their dead CSS
    doomed = list(hidden)
    footer = FOOTER_DROP.get(page)
    if footer:
        doomed += footer[1]
    extra = EXTRA_HIDE.get(route)
    if extra:
        doomed += extra[1]
    doomed += PARTNER_DECOR.get(page, [])
    for elem_id in doomed:
        html = remove_element(html, elem_id)
    html = strip_dead_css(html, doomed)

    # 8c. photo reports: direct link + drop the chooser
    photo = PHOTO_LINK.get(page)
    if photo:
        html = repoint_button(html, photo[0], photo[1])
    for rec_id in DROP_RECORDS.get(page, []):
        html = remove_record(html, rec_id)

    # 9. housekeeping: language, accessible heading, menu script
    html = re.sub(r"<html\b[^>]*>", '<html lang="ru">', html, count=1)
    html = add_page_heading(html, page)
    if "</body>" in html:
        html = html.replace("</body>", MOBILE_MENU_SCRIPT + "</body>", 1)
    return html, images, libs, hidden, nav


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    all_images, all_libs = set(), set()
    all_hidden = set()

    for page, route, source in PAGES:
        src = os.path.join(CAPTURES, page)
        html = open(src, encoding="utf-8").read()
        out, images, libs, hidden, nav = port(html, page, route)
        all_images.update(images)
        all_libs.update(libs)
        all_hidden.update(hidden)

        if mode == "build":
            css = site_css(route, nav, hidden, FOOTER_DROP.get(page))
            with open(os.path.join(ROOT, "assets", "tilda", f"site-{route}.css"), "w", encoding="utf-8") as fh:
                fh.write(css)
            digest = hashlib.sha1(css.encode("utf-8")).hexdigest()[:8]
            tag = f'<link rel="stylesheet" href="../assets/tilda/site-{route}.css?v={digest}">\n'
            out = out.replace(SITE_CSS_MARKER, tag)
            dst_dir = os.path.join(ROOT, route)
            os.makedirs(dst_dir, exist_ok=True)
            marker = (
                f"<!-- ported from the Tilda page {source} (captured snapshot);\n"
                f"     all assets are served locally from ../assets;\n"
                f"     cross-spectacle nav removed, hub button added — see tools/port_tilda.py -->\n"
            )
            body = out.replace("</head>", marker + "</head>", 1) if "</head>" in out else marker + out
            with open(os.path.join(dst_dir, "index.html"), "w", encoding="utf-8") as fh:
                fh.write(body)
            print(f"{route:10} {len(body):>8} bytes -> {route}/index.html  hidden={len(hidden)}")
        else:
            print(f"{route:10} images={len(images):3} libs={len(libs):2}")

    if mode != "build":
        img_path = os.path.join(ROOT, "tools", "_images.txt")
        lib_path = os.path.join(ROOT, "tools", "_libs.txt")
        with open(img_path, "w") as fh:
            for url, local in sorted(all_images):
                fh.write(f"{url}\t{local.replace('../', '')}\n")
        with open(lib_path, "w") as fh:
            for url, local in sorted(all_libs):
                fh.write(f"{url}\t{local.replace('../', '')}\n")
        print(f"\nunique images: {len(all_images)}  unique libs: {len(all_libs)}")
        print(f"wrote {img_path} and {lib_path}")


if __name__ == "__main__":
    main()
