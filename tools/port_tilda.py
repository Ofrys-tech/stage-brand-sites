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

import os
import re
import sys

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
STADIUM_IDS = {
    "index.html": ["1730353296026", "1730353345862", "1773398078166000002"],
    "ufa.html": ["1730353296026", "1730353345862"],
    "kazan.html": ["1730353296026", "1730353345862"],
    "partner.html": [],
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
FOOTER_DROP = {
    "index.html": ("rec1914306901", ["1730363799998", "1730363799994", "1730363799990"]),
    "ufa.html": ("rec867373856", ["1730363799998", "1730363799994", "1730363799990"]),
    "kazan.html": ("rec819137808", ["1730363799998", "1730363799994", "1730363799990"]),
    "partner.html": None,
}

# Back-to-hub pill sits in the nav row, left of "О спектакле"; the nav buttons are
# pushed right by this much so nothing overlaps.
HOME_SHIFT = 170
NAV_TARGETS_BY_ROLE = ("about", "partners", "actors")

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


def image_local(url):
    """static.tildacdn.com/<hash>/<name> and thb/.../-/resize/20x/<name> -> one file."""
    clean = strip_query(url)
    m = re.match(r"https://(?:static|thb|optim)\.tildacdn\.com/([^/]+)/(?:.+/)?([^/]+)$", clean)
    if not m:
        return None
    digest, name = m.group(1), m.group(2)
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
    for m in pattern.finditer(html):
        prefix = html[: m.start()]
        rec = re.findall(r'<div id="(rec\d+)"', prefix)
        elem = re.findall(r"data-elem-id='(\d+)'", prefix)
        if rec and elem:
            hidden.add((rec[-1], elem[-1]))
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


def add_home_button(html):
    """The T456 header on these pages is an empty 0x0 placeholder (all navigation lives
    in the hero Zero Block), so the back button is placed in the hero artboard."""
    m = re.search(r'<div class="t396__artboard"[^>]*>', html)
    if not m:
        return html
    return html[: m.end()] + HOME_BUTTON + html[m.end():]


def link_site_css(html, route):
    tag = f'<link rel="stylesheet" href="../assets/tilda/site-{route}.css">\n'
    return html.replace("</head>", tag + "</head>", 1)


def site_css(route, nav, hidden, footer_drop):
    nav = nav or {}
    left = nav.get("base_left", "calc(50% - 600px + 197px)")
    small_left = nav.get("small_left")
    css = [
        f"/* Generated by tools/port_tilda.py for /{route}/ — do not edit by hand. */",
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
        "/* phones: the nav row has no room, pin the pill to the corner */",
        "@media screen and (max-width: 959px) {",
        "\t.lb-home {",
        "\t\tposition: fixed;",
        "\t\ttop: 10px;",
        "\t\tleft: 10px;",
        "\t\twidth: auto;",
        "\t\theight: 40px;",
        "\t\tpadding: 0 14px;",
        "\t\tfont-size: 15px;",
        "\t}",
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
    css.append("/* hidden: spectacle-to-spectacle buttons (the hub owns navigation) */")
    for rec, elem in sorted(hidden):
        css.append(f'#{rec} .tn-elem[data-elem-id="{elem}"] {{ display: none !important; }}')
    if footer_drop:
        rec, ids = footer_drop
        css.append("")
        css.append("/* hidden: bottom date/time plaque and photo button */")
        for elem in ids:
            css.append(f'#{rec} .tn-elem[data-elem-id="{elem}"] {{ display: none !important; }}')
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

    # 5. home button + our stylesheet (contains the hide rules for steps 4 and 9)
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
    html = link_site_css(html, route)

    # 6. strip the protruding stadium outlines (border only, fill stays)
    for elem_id in STADIUM_IDS.get(page, []):
        html = re.sub(
            r'(#rec\d+ \.tn-elem\[data-elem-id="%s"\] \.tn-atom\{[^}]*?)--t396-borderwidth:\s*1px'
            % re.escape(elem_id),
            r"\1--t396-borderwidth:0px",
            html,
        )

    # 7. native lazy loading below the first screen (hero stays eager, popups stay eager
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

    # 8. housekeeping
    html = html.replace('<html lang="en"', '<html lang="ru"')
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
