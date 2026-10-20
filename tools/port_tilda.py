#!/usr/bin/env python3
"""Port the captured Tilda pages into self-hosted static pages.

Source: docs/captures/tilda-11092055/published-html/*.html (verbatim snapshots)
Output: <route>/index.html with every CDN reference rewritten to a local asset.

The captured HTML already contains the full generated Zero Block CSS inline, so a
page stays pixel-identical as long as the base libraries, the per-page blocks
bundle and the images are served locally. That is all this script does — it never
touches layout, except for the deliberate removals listed in PATCHES.

    python3 tools/port_tilda.py plan     # print the asset lists to fetch
    python3 tools/port_tilda.py build    # write <route>/index.html
"""

import json
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
# Their id is stable across the spectacle pages; removing the 1px border keeps the
# faint panel fill but removes the arc.
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

IMG_EXT = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".avif")
URL_RE = re.compile(r"""https://(?:static|thb|optim)\.tildacdn\.com/[^"'\s)\\]*""")
LIB_RE = re.compile(r"""https://(?:neo|static)\.tildacdn\.com/[^"'\s)]*\.(?:js|css)(?:\?[^"'\s)]*)?""")
ANCHOR_RE = re.compile(r"""<a\b([^>]*?)href="([^"]*)"([^>]*)>(.*?)</a>""", re.S)


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
        clean = strip_query(url)
        if clean.lower().endswith(IMG_EXT):
            local = image_local(url)
            if local:
                images.add((url, local))
    for url in LIB_RE.findall(html):
        libs.add((url, lib_local(url)))
    return sorted(images), sorted(libs)


def map_href(href, inner):
    if href.startswith("#") or re.match(r"^[a-z]+:", href):
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


def port(html, page):
    images, libs = collect(html)

    # 1. telemetry scripts and CDN prefetch hints — drop the whole tag
    for url in DROP_SCRIPTS:
        html = re.sub(r"<script\b[^>]*" + re.escape(url) + r"[^>]*>\s*</script>\s*", "", html)
    html = re.sub(r'<link[^>]*rel="dns-prefetch"[^>]*tildacdn[^>]*>\s*', "", html)
    # dead reference left in the Tilda project: /script.js does not exist (404 on the live site too)
    html = re.sub(r'<script[^>]*src="script\.js[^"]*"[^>]*>\s*</script>\s*', "", html)

    # 2. libraries and images -> local, longest URL first so no prefix eats a suffix
    mapping = [(u, l) for u, l in libs + images]
    for url, local in sorted(mapping, key=lambda x: -len(x[0])):
        html = html.replace(url, local)

    # 3. internal links
    def repl_anchor(m):
        before, href, after, inner = m.group(1), m.group(2), m.group(3), m.group(4)
        return f'<a{before}href="{map_href(href, inner)}"{after}>{inner}</a>'

    html = ANCHOR_RE.sub(repl_anchor, html)

    # 4. strip the protruding stadium outlines (border only, fill stays)
    for elem_id in STADIUM_IDS.get(page, []):
        html = re.sub(
            r'(#rec\d+ \.tn-elem\[data-elem-id="%s"\] \.tn-atom\{[^}]*?)--t396-borderwidth:\s*1px'
            % re.escape(elem_id),
            r"\1--t396-borderwidth:0px",
            html,
        )

    # 5. native lazy loading below the first screen (hero stays eager, popups stay eager
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

    # 6. housekeeping
    html = html.replace('<html lang="en"', '<html lang="ru"')
    return html, images, libs


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    all_images, all_libs = set(), set()

    for page, route, source in PAGES:
        src = os.path.join(CAPTURES, page)
        html = open(src, encoding="utf-8").read()
        out, images, libs = port(html, page)
        all_images.update(images)
        all_libs.update(libs)

        if mode == "build":
            dst_dir = os.path.join(ROOT, route)
            os.makedirs(dst_dir, exist_ok=True)
            marker = (
                f"<!-- ported from the Tilda page {source} (captured snapshot);\n"
                f"     all assets are served locally from ../assets -->\n"
            )
            body = out.replace("</head>", marker + "</head>", 1) if "</head>" in out else marker + out
            with open(os.path.join(dst_dir, "index.html"), "w", encoding="utf-8") as fh:
                fh.write(body)
            print(f"{route:10} {len(body):>8} bytes -> {route}/index.html")
        else:
            print(f"{route:10} images={len(images):3} libs={len(libs):2}")

    if mode == "plan":
        img_path = os.path.join(ROOT, "tools", "_images.txt")
        lib_path = os.path.join(ROOT, "tools", "_libs.txt")
        with open(img_path, "w") as fh:
            for url, local in sorted(all_images):
                fh.write(f"{url}\t{local}\n")
        with open(lib_path, "w") as fh:
            for url, local in sorted(all_libs):
                fh.write(f"{url}\t{local}\n")
        print(f"\nunique images: {len(all_images)}  unique libs: {len(all_libs)}")
        print(f"wrote {img_path} and {lib_path}")


if __name__ == "__main__":
    main()
