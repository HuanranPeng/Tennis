#!/usr/bin/env python3
"""
Fetch ultraperformanceacademy.net and produce a static mirror that matches the
live Hostinger/Zyro SSR output: full HTML + Astro CSS/JS bundles + local assets.

Re-run after site updates: python3 scripts/build_offline.py
"""
from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
import ssl
import sys
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(__file__).resolve().parent / ".cache"
ASSETS_SITE = ROOT / "assets" / "site"
ASSETS_MEDIA = ROOT / "assets" / "media"
ASSETS_FONTS = ROOT / "assets" / "fonts"
ASSETS_ASTRO = ROOT / "assets" / "astro"
ASTRO_WEB_PREFIX = "/_astro-1777938346575/"
ASTRO_REL = "assets/astro/"

BASE = "https://ultraperformanceacademy.net"
CDN = "https://assets.zyrosite.com/ALp7EGXM9ls0JPOx"
HERO_VIDEO = "https://videos.pexels.com/video-files/5740606/5740606-uhd_2160_4096_25fps.mp4"
HERO_POSTER = (
    "https://images.pexels.com/videos/5740606/pexels-photo-5740606.jpeg"
    "?auto=compress&cs=tinysrgb&fit=crop&h=1200&w=630"
)

URLS = [
    ("/", "home.html"),
    ("/programs", "programs.html"),
    ("/group-lessons", "group-lessons.html"),
    ("/summerholiday-camp", "summerholiday-camp.html"),
    ("/coaches", "coaches.html"),
    ("/contact", "contact.html"),
    ("/small-group", "small-group.html"),
]

SLUG_TO_FILE = {
    "home": "index.html",
    "programs": "programs.html",
    "group-lessons": "group-lessons.html",
    "summerholiday-camp": "summerholiday-camp.html",
    "coaches": "coaches.html",
    "contact": "contact.html",
    "small-group": "small-group.html",
}

NAV_ORDER = [
    ("home", "Home", "index.html"),
    ("programs", "Programs", "programs.html"),
    ("small-group", "Small Group", "small-group.html"),
    ("group-lessons", "Group Lessons", "group-lessons.html"),
    ("summerholiday-camp", "Summer/Holiday Camp", "summerholiday-camp.html"),
    ("coaches", "Coaches", "coaches.html"),
    ("contact", "Contact", "contact.html"),
]


def unwrap(x):
    if isinstance(x, list) and len(x) == 2 and isinstance(x[0], int):
        return unwrap(x[1])
    if isinstance(x, dict):
        return {k: unwrap(v) for k, v in x.items()}
    if isinstance(x, list):
        return [unwrap(i) for i in x]
    return x


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=600) as r:
        return r.read()


def load_page_data_from_html(raw: str) -> dict:
    idx = raw.find('component-url="/_astro-1777938346575/Page.')
    if idx == -1:
        raise ValueError("Page island not found")
    start = raw.rfind("<astro-island", 0, idx)
    end = raw.find("></astro-island>", idx)
    if end == -1:
        raise ValueError("Page island end not found")
    chunk = raw[start : end + len("></astro-island>")]
    m = re.search(r'props="(\{.*\})"\s+ssr', chunk, re.DOTALL)
    if not m:
        raise ValueError("props not found")
    decoded = html_lib.unescape(m.group(1))
    data = json.loads(decoded)
    return unwrap(data["pageData"])


def merge_ud(parts: list[dict]) -> dict:
    merged = {"pages": {}, "blocks": {}, "elements": {}}
    for ud in parts:
        merged["pages"].update(ud.get("pages", {}))
        merged["blocks"].update(ud.get("blocks", {}))
        merged["elements"].update(ud.get("elements", {}))
    return merged


def collect_site_filenames(ud: dict) -> set[str]:
    out: set[str] = set()

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get("origin") == "assets" and obj.get("path"):
                out.add(obj["path"])
            if obj.get("type") == "GridGallery":
                for im in obj.get("images", []) or []:
                    if isinstance(im, list) and len(im) == 2:
                        im = im[1]
                    if isinstance(im, dict) and im.get("path"):
                        out.add(im["path"])
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(ud)
    nav = ud["blocks"].get("header")
    if nav:
        p = (nav.get("settings") or {}).get("logoImagePath")
        if p:
            out.add(p)
    return out


def rewrite_links(html: str) -> str:
    def repl(m):
        href = m.group(1)
        if href.startswith(("http://", "https://", "mailto:", "tel:", "#")):
            return m.group(0)
        core = href.split("?", 1)[0].strip().rstrip("/")
        if core in ("", "/"):
            return 'href="index.html"'
        slug = core.lstrip("/")
        if slug in SLUG_TO_FILE:
            return f'href="{SLUG_TO_FILE[slug]}"'
        return m.group(0)

    return re.sub(r'href="([^"]+)"', repl, html)


def local_asset(path: str) -> str:
    return f"assets/site/{path}"


def render_social(el: dict) -> str:
    parts = []
    for item in el.get("links", []) or []:
        if isinstance(item, list) and len(item) == 2:
            item = item[1]
        if not isinstance(item, dict):
            continue
        link = item.get("link") or ""
        svg = item.get("svg") or ""
        if link:
            parts.append(
                f'<a href="{html_lib.escape(link)}" rel="noopener noreferrer" '
                f'target="_blank" class="gen-social-a">{svg}</a>'
            )
    return '<div class="social gen-social">' + "".join(parts) + "</div>"


def render_form(el: dict) -> str:
    schema = (el.get("settings") or {}).get("schema") or []
    rows = []
    for field in schema:
        if isinstance(field, list) and len(field) == 2:
            field = field[1]
        if not isinstance(field, dict):
            continue
        fid = field.get("id", "")
        label = field.get("inputLabel") or field.get("name") or ""
        ph = field.get("placeholder") or ""
        tag = field.get("tag") or "input"
        lid = html_lib.escape(label)
        pid = html_lib.escape(ph)
        if tag == "textarea":
            rows.append(
                f'<label class="gen-label"><span class="gen-label-t">{lid}</span>'
                f'<textarea name="{html_lib.escape(fid)}" rows="5" placeholder="{pid}"></textarea></label>'
            )
        else:
            rows.append(
                f'<label class="gen-label"><span class="gen-label-t">{lid}</span>'
                f'<input type="text" name="{html_lib.escape(fid)}" placeholder="{pid}" /></label>'
            )
    btn = el.get("submitButtonData") or {}
    btntext = btn.get("content") or "Submit"
    success = (el.get("settings") or {}).get("successMessage") or ""
    note = (
        "Static offline copy: this form is not connected to the live site. "
        "Please email "
        '<a href="mailto:champ.for.life@ultraperformanceacademy.net">champ.for.life@ultraperformanceacademy.net</a>.'
    )
    return (
        f'<div class="gen-form-wrap">'
        f'<form class="gen-form" action="#" method="get" onsubmit="return false;">'
        f'{"".join(rows)}'
        f'<button type="button" class="gen-submit">{html_lib.escape(btntext)}</button>'
        f'<p class="gen-form-note">{note}</p>'
        f'<p class="gen-form-success-msg">{html_lib.escape(success)}</p>'
        f"</form></div>"
    )


def render_map(el: dict) -> str:
    src = (el.get("settings") or {}).get("src") or ""
    if not src:
        return ""
    esc = html_lib.escape(src, quote=True)
    return (
        f'<div class="gen-map"><iframe title="Map" loading="lazy" '
        f'src="{esc}" referrerpolicy="no-referrer-when-downgrade"></iframe></div>'
    )


def render_button(el: dict) -> str:
    text = el.get("content") or "Button"
    href = el.get("href") or "#"
    if isinstance(href, str) and href.startswith("/"):
        slug = href.strip("/").split("/")[0]
        if slug in SLUG_TO_FILE:
            href = SLUG_TO_FILE[slug]
    return (
        f'<p class="gen-button-wrap"><a class="gen-submit gen-button" '
        f'href="{html_lib.escape(href)}">{html_lib.escape(text)}</a></p>'
    )


def render_element(elid: str, ud: dict) -> str:
    el = ud["elements"].get(elid)
    if not el:
        return ""
    typ = el.get("type")
    if typ == "GridTextBox":
        c = el.get("content") or ""
        c = rewrite_links(c)
        c = re.sub(
            r"https://assets\.zyrosite\.com/ALp7EGXM9ls0JPOx/([^\"\\s]+)",
            lambda m: local_asset(m.group(1)),
            c,
        )
        return f'<div class="gen-text">{c}</div>'
    if typ == "GridImage":
        st = el.get("settings") or {}
        path = st.get("path")
        if not path:
            return ""
        alt = html_lib.escape(st.get("alt") or "")
        br = ""
        if isinstance(st.get("styles"), dict):
            br = st["styles"].get("borderRadius") or ""
        style = f"border-radius:{br};" if br else ""
        return (
            f'<figure class="gen-img" style="{style}">'
            f'<img src="{local_asset(path)}" alt="{alt}" loading="lazy" /></figure>'
        )
    if typ == "GridGallery":
        imgs = el.get("images") or []
        figs = []
        for im in imgs:
            if isinstance(im, list) and len(im) == 2:
                im = im[1]
            if not isinstance(im, dict):
                continue
            p = im.get("path")
            if not p:
                continue
            figs.append(
                f'<figure><img src="{local_asset(p)}" alt="" loading="lazy" /></figure>'
            )
        return '<div class="gallery-masonry gen-gallery">' + "".join(figs) + "</div>"
    if typ == "GridShape":
        col = el.get("color") or "transparent"
        return (
            f'<div class="gen-shape" style="background-color:{html_lib.escape(col)};'
            f'border-radius:12px;height:100%;min-height:100%"></div>'
        )
    if typ == "GridSocialIcons":
        return render_social(el)
    if typ == "GridForm":
        return render_form(el)
    if typ == "GridMap":
        return render_map(el)
    if typ == "GridButton":
        return render_button(el)
    return ""


def layout_padding(block: dict) -> str:
    st = (block.get("settings") or {}).get("styles") or {}
    pad = st.get("block-padding") or st.get("m-block-padding")
    return pad or ""


def overlay_style(bg: dict) -> str:
    g = bg.get("gradient") or {}
    angle = g.get("angle", 135)
    cols = g.get("colors") or []
    stops = []
    for c in cols:
        if isinstance(c, list) and len(c) == 2:
            c = c[1]
        if isinstance(c, dict) and c.get("value"):
            stops.append(c["value"])
    try:
        op = float(bg.get("overlay-opacity") or 0.5)
    except (TypeError, ValueError):
        op = 0.5
    op = max(0.0, min(1.0, op))
    if len(stops) >= 2:
        return (
            f"background:linear-gradient({angle}deg,{stops[0]},{stops[1]});"
            f"opacity:{op};"
        )
    return f"background:rgba(0,0,0,{op});"


def block_background_style(bg: dict) -> str:
    if not bg:
        return ""
    parts = []
    cur = bg.get("current")
    if cur == "color" and bg.get("color"):
        parts.append(f"background-color:{bg['color']}")
    if cur == "gradient":
        g = bg.get("gradient") or {}
        angle = g.get("angle", 135)
        cols = g.get("colors") or []
        stops = []
        for c in cols:
            if isinstance(c, list) and len(c) == 2:
                c = c[1]
            if isinstance(c, dict) and c.get("value"):
                stops.append(c["value"])
        if len(stops) >= 2:
            parts.append(f"background:linear-gradient({angle}deg,{stops[0]},{stops[1]})")
    return ";".join(parts)


def canvas_extents(components: list, ud: dict, box_key: str) -> tuple[int, int]:
    """Bounding box size from editor coordinates (desktop or mobile)."""
    max_r = 1
    max_b = 1
    for cid in components:
        el = ud["elements"].get(cid)
        if not el:
            continue
        box = el.get(box_key) or {}
        if "left" not in box and "width" not in box:
            continue
        l = int(box.get("left") or 0)
        t = int(box.get("top") or 0)
        w = int(box.get("width") or 0)
        h = int(box.get("height") or 0)
        max_r = max(max_r, l + w)
        max_b = max(max_b, t + h)
    return max_r, max_b


def block_has_canvas_positions(block: dict, ud: dict) -> bool:
    for cid in block.get("components", []) or []:
        el = ud["elements"].get(cid)
        if not el:
            continue
        d = el.get("desktop")
        if isinstance(d, dict) and "left" in d and isinstance(d.get("width"), (int, float)):
            return True
    return False


def wrap_canvas_item(fragment: str, el: dict, cw: int, ch: int, mcw: int, mch: int) -> str:
    if not fragment:
        return ""
    d = el.get("desktop") or {}
    if not isinstance(d, dict) or "left" not in d:
        return fragment
    m = el.get("mobile") or {}
    dl = int(d.get("left") or 0)
    dt = int(d.get("top") or 0)
    dwi = int(d.get("width") or 1)
    dhgt = int(d.get("height") or 0)
    ml = int(m.get("left", dl) if "left" in m else dl)
    mt = int(m.get("top", dt) if "top" in m else dt)
    mwi = int(m.get("width", dwi) if m.get("width") else dwi) or 1
    mhgt = int(m.get("height", dhgt) if m.get("height") is not None else dhgt)

    typ = el.get("type")
    fluid_height = typ in (
        "GridTextBox",
        "GridGallery",
        "GridSocialIcons",
        "GridForm",
        "GridMap",
        "GridButton",
    )
    extra = " gen-canvas-item--fluid" if fluid_height else ""
    vs = (
        f"--d-l:{dl};--d-t:{dt};--d-w:{max(dwi, 1)};--d-h:{dhgt};"
        f"--m-l:{ml};--m-t:{mt};--m-w:{max(mwi, 1)};--m-h:{mhgt};"
        f"--cw:{cw};--ch:{ch};--mcw:{mcw};--mch:{mch};"
    )
    return f'<div class="gen-canvas-item{extra}" style="{vs}">{fragment}</div>'


def render_block_inner_canvas(block: dict, ud: dict, outer_class: str | None = None) -> str:
    components = block.get("components", []) or []
    dw, dh = canvas_extents(components, ud, "desktop")
    mw, mh = canvas_extents(components, ud, "mobile")
    desk_min = int((block.get("desktop") or {}).get("minHeight") or 0)
    mob_min = int((block.get("mobile") or {}).get("minHeight") or 0)
    ch = max(dh, desk_min, 1)
    mch = max(mh, mob_min, 1)
    mcw = max(mw, 1)
    cw = max(dw, 1)

    parts = []
    for cid in components:
        el = ud["elements"].get(cid)
        inner = render_element(cid, ud)
        if el:
            parts.append(wrap_canvas_item(inner, el, cw, ch, mcw, mch))
        else:
            parts.append(inner)
    inner_html = "".join(parts)
    min_styles = (
        f"--cw:{cw};--ch:{ch};--mcw:{mcw};--mch:{mch};"
        f"min-height:{ch}px;--canvas-min-mobile:{mch}px"
    )
    cls = outer_class or "gen-layout-inner gen-layout-inner--canvas"
    return f'<div class="{cls}" style="{min_styles}">{inner_html}</div>'


def render_block_layout(bid: str, ud: dict) -> str:
    block = ud["blocks"].get(bid)
    if not block or block.get("type") != "BlockLayout":
        return ""
    bg = block.get("background") or {}
    cur = bg.get("current")
    use_canvas = block_has_canvas_positions(block, ud)
    comps = block.get("components", []) or []
    flat_inner = "".join(render_element(cid, ud) for cid in comps)

    if cur == "video":
        ov = overlay_style(bg)
        hero_cls = "hero gen-hero" + (" hero--canvas" if use_canvas else "")
        if use_canvas:
            inner = render_block_inner_canvas(
                block,
                ud,
                outer_class="hero__content gen-layout-inner--canvas hero__content--canvas",
            )
        else:
            inner = f'<div class="hero__content">{flat_inner}</div>'
        return f"""<section class="{hero_cls}">
  <div class="hero__media">
    <video autoplay muted loop playsinline poster="assets/media/hero-poster.jpg">
      <source src="assets/media/hero.mp4" type="video/mp4" />
    </video>
    <div class="hero__overlay" style="{ov}"></div>
  </div>
  {inner}
</section>"""

    style = block_background_style(bg)
    att = block.get("attachment")
    if att == "fixed":
        style = (style + ";background-attachment:fixed") if style else "background-attachment:fixed"
    pad = layout_padding(block)
    if pad:
        style = f"{style};padding:{pad}" if style else f"padding:{pad}"
    inner_wrapped = (
        render_block_inner_canvas(block, ud)
        if use_canvas
        else f'<div class="gen-layout-inner">{flat_inner}</div>'
    )
    return f'<section class="gen-layout" style="{html_lib.escape(style)}">{inner_wrapped}</section>'


def render_page(slug: str, ud: dict) -> str:
    page = next((pv for pv in ud["pages"].values() if pv.get("slug") == slug), None)
    if not page:
        return "<p>Page not found.</p>"
    parts = []
    for bid in page.get("blocks", []) or []:
        b = ud["blocks"].get(bid)
        if b and b.get("type") == "BlockLayout":
            parts.append(render_block_layout(bid, ud))
    return "\n".join(parts)


def render_footer(ud: dict) -> str:
    inner = render_block_layout("zSiG-O", ud)
    return f'<footer class="site-footer gen-footer">{inner}</footer>'


def nav_html(current_slug: str) -> str:
    items = []
    for slug, label, fn in NAV_ORDER:
        cur = ' aria-current="page"' if slug == current_slug else ""
        items.append(f'<a href="{fn}"{cur}>{html_lib.escape(label)}</a>')
    return "\n          ".join(items)


def shell(title: str, desc: str, slug: str, body: str, ud: dict) -> str:
    nav_block = ud["blocks"].get("header") or {}
    logo_path = (nav_block.get("settings") or {}).get("logoImagePath")
    logo_src = local_asset(logo_path) if logo_path else ""
    footer = rewrite_links(render_footer(ud))
    css_href = "css/styles.css"
    font_href = "assets/fonts/fonts.css"
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html_lib.escape(title)}</title>
    <meta name="description" content="{html_lib.escape(desc)}" />
    <link rel="stylesheet" href="{font_href}" />
    <link rel="stylesheet" href="{css_href}" />
  </head>
  <body>
    <header class="site-header">
      <div class="header-inner">
        <a class="logo" href="index.html" aria-label="Ultra Performance Academy home">
          <img src="{logo_src}" alt="Ultra Performance Academy" width="272" height="117" />
        </a>
        <button type="button" class="nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="site-nav" aria-label="Open menu">
          <span></span><span></span><span></span>
        </button>
        <nav class="nav" id="site-nav" aria-label="Main">
          {nav_html(slug)}
        </nav>
      </div>
    </header>
    <main class="site-main">
{body}
    </main>
    {footer}
    <script>
      (function () {{
        var btn = document.getElementById("nav-toggle");
        var nav = document.getElementById("site-nav");
        if (!btn || !nav) return;
        function setOpen(open) {{
          nav.classList.toggle("is-open", open);
          btn.setAttribute("aria-expanded", open ? "true" : "false");
          btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
          document.body.classList.toggle("nav-open", open);
        }}
        btn.addEventListener("click", function (e) {{
          e.stopPropagation();
          setOpen(!nav.classList.contains("is-open"));
        }});
        nav.querySelectorAll("a").forEach(function (a) {{
          a.addEventListener("click", function () {{ setOpen(false); }});
        }});
        document.addEventListener("click", function () {{
          if (nav.classList.contains("is-open")) setOpen(false);
        }});
        nav.addEventListener("click", function (e) {{ e.stopPropagation(); }});
        document.addEventListener("keydown", function (e) {{
          if (e.key === "Escape") setOpen(false);
        }});
      }})();
    </script>
  </body>
</html>
"""


def download_one(args: tuple[str, str]) -> tuple[str, bool, str]:
    url, dest = args
    dest_path = Path(dest)
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(fetch_bytes(url))
        return (dest, True, "")
    except Exception as e:
        return (dest, False, str(e))


def collect_astro_seeds_from_html(html: str) -> set[str]:
    return set(re.findall(r"/_astro-1777938346575/([^\"'\s>]+)", html))


def download_astro_bundle() -> list[tuple[str, str]]:
    ASSETS_ASTRO.mkdir(parents=True, exist_ok=True)
    seeds: set[str] = set()
    for _path, fname in URLS:
        p = CACHE / fname
        if p.exists():
            seeds |= collect_astro_seeds_from_html(p.read_text(encoding="utf-8"))

    seen: set[str] = set()
    q: deque[str] = deque(sorted(seeds))
    bad: list[tuple[str, str]] = []

    def add_js_deps(text: str) -> None:
        for pat in (
            r'from"\./([^"]+)"',
            r"from'\./([^']+)'",
            r'import\("\./([^"]+)"',
            r"import\('\./([^']+)'",
        ):
            for m in re.finditer(pat, text):
                dep = m.group(1)
                if dep not in seen:
                    q.append(dep)
        for m in re.finditer(r'"_astro-1777938346575/([^"]+)"', text):
            dep = m.group(1)
            if dep not in seen:
                q.append(dep)

    while q:
        name = q.popleft()
        if name in seen:
            continue
        url = BASE + ASTRO_WEB_PREFIX + name
        dest = ASSETS_ASTRO / name
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(fetch_bytes(url))
        except Exception as e:
            bad.append((name, str(e)))
            continue
        seen.add(name)
        if name.endswith(".js"):
            try:
                add_js_deps(dest.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass

    return bad


def collect_zyro_filenames_from_html(html: str) -> set[str]:
    found: set[str] = set()
    for pat in (
        r"https://assets\.zyrosite\.com/cdn-cgi/image/[^\"'\s<>]+?/ALp7EGXM9ls0JPOx/([^\"'\s<>?&]+)",
        r"https://assets\.zyrosite\.com/ALp7EGXM9ls0JPOx/([^\"'\s<>?&]+)",
    ):
        for m in re.finditer(pat, html):
            fn = m.group(1).split("?")[0].rstrip("\\")
            if fn and ".." not in fn:
                found.add(fn)
    return found


def rewrite_ssr_html(html: str) -> str:
    html = html.replace(f'href="{ASTRO_WEB_PREFIX}', f'href="{ASTRO_REL}')
    html = html.replace(f"href='{ASTRO_WEB_PREFIX}", f"href='{ASTRO_REL}")
    html = html.replace(f'component-url="{ASTRO_WEB_PREFIX}', f'component-url="{ASTRO_REL}')
    html = html.replace('"/_astro-1777938346575/', f'"{ASTRO_REL}')
    html = html.replace("'/_astro-1777938346575/", f"'{ASTRO_REL}")

    def zyro_local(m: re.Match[str]) -> str:
        fn = m.group(1).split("?")[0].rstrip("\\")
        return f"assets/site/{fn}"

    html = re.sub(
        r"https://assets\.zyrosite\.com/cdn-cgi/image/[^\"'\s<>]+?/ALp7EGXM9ls0JPOx/([^\"'\s<>?&]+)",
        zyro_local,
        html,
    )
    html = re.sub(
        r"https://assets\.zyrosite\.com/ALp7EGXM9ls0JPOx/([^\"'\s<>?&]+)",
        zyro_local,
        html,
    )

    html = re.sub(
        r"<link[^>]*https://cdn\.zyrosite\.com/u1/google-fonts/font-faces[^>]*>",
        '<link rel="stylesheet" href="assets/fonts/fonts.css" />',
        html,
    )

    html = re.sub(
        r"https://videos\.pexels\.com/video-files/5740606/[^\"'\s<>]+\.mp4[^\"']*",
        "assets/media/hero.mp4",
        html,
    )
    html = re.sub(
        r"https://images\.pexels\.com/videos/5740606/[^\"'\s<>]+",
        "assets/media/hero-poster.jpg",
        html,
    )

    for slug in ("programs", "group-lessons", "summerholiday-camp", "coaches", "contact", "small-group"):
        fn = SLUG_TO_FILE[slug]
        html = re.sub(rf'href="/{slug}"', f'href="{fn}"', html)
        html = re.sub(rf"href='/{slug}'", f"href='{fn}'", html)
        html = re.sub(
            rf'href="https://ultraperformanceacademy\.net/{re.escape(slug)}"',
            f'href="{fn}"',
            html,
        )
        html = re.sub(
            rf'href="https://ultraperformanceacademy\.net/{re.escape(slug)}/"',
            f'href="{fn}"',
            html,
        )
    html = re.sub(r'href="https://ultraperformanceacademy\.net/"', 'href="index.html"', html)
    html = re.sub(r"href='https://ultraperformanceacademy\.net/'", "href='index.html'", html)
    html = re.sub(r'href="https://ultraperformanceacademy\.net"', 'href="index.html"', html)
    html = re.sub(r'href="/"', 'href="index.html"', html)
    html = re.sub(r"href='/'", "href='index.html'", html)

    # Entry animations keep .transition blocks at opacity:0 until JS runs. Opening
    # as file:// or vscode-webview often blocks ES modules, so nothing appears.
    _anim_fallback = (
        '<script>(function(){var p=location.protocol,s=location.search;'
        'if(/[?&]anim=1(?:&|$)/.test(s))document.documentElement.classList.add("respect-zyro-animations");'
        'if(p==="file:"||p==="vscode-webview:"||/[?&]static=1(?:&|$)/.test(s))'
        'document.documentElement.classList.add("no-entry-anim");})();</script>'
        '<link rel="stylesheet" href="assets/astro/animation-fallback.css" />'
    )
    if "animation-fallback.css" not in html:
        html = html.replace("</head>", _anim_fallback + "</head>", 1)

    _header_poly = (
        '<script src="assets/astro/header-scroll-polyfill.js"></script>'
        '<script src="assets/astro/mobile-nav-polyfill.js"></script>'
    )
    if "header-scroll-polyfill.js" not in html:
        html = html.replace("</body>", _header_poly + "</body>", 1)
    elif "mobile-nav-polyfill.js" not in html:
        html = html.replace(
            '<script src="assets/astro/header-scroll-polyfill.js"></script>',
            '<script src="assets/astro/header-scroll-polyfill.js"></script>'
            '<script src="assets/astro/mobile-nav-polyfill.js"></script>',
            1,
        )

    return html


def collect_unsplash_urls(html: str) -> set[str]:
    return set(re.findall(r"https://images\.unsplash\.com[^\"'\s<>]+", html))


def build_unsplash_map(urls: set[str]) -> dict[str, str]:
    m: dict[str, str] = {}
    ASSETS_SITE.mkdir(parents=True, exist_ok=True)
    for u in sorted(urls):
        low = u.split("?")[0].lower()
        ext = ".jpg"
        if low.endswith(".png"):
            ext = ".png"
        elif low.endswith(".webp"):
            ext = ".webp"
        h = hashlib.sha256(u.encode()).hexdigest()[:20]
        fn = f"unsplash-{h}{ext}"
        dest = ASSETS_SITE / fn
        if not dest.exists():
            try:
                dest.write_bytes(fetch_bytes(u))
            except Exception:
                continue
        m[u] = f"assets/site/{fn}"
    return m


def apply_unsplash_map(html: str, umap: dict[str, str]) -> str:
    for remote, local in umap.items():
        html = html.replace(remote, local)
    return html


def build_font_css() -> None:
    css_url = (
        "https://fonts.googleapis.com/css2?"
        "family=Lato:wght@400;500;600&family=Oswald:wght@300;400;500;700&display=swap"
    )
    req = urllib.request.Request(
        css_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        gcss = r.read().decode("utf-8", errors="replace")

    latin_blocks = re.findall(
        r"/\*\s*latin\s*\*/\s*(@font-face\s*\{[^}]+\})",
        gcss,
        flags=re.IGNORECASE,
    )
    if not latin_blocks:
        latin_blocks = re.findall(r"@font-face\s*\{[^}]+\}", gcss)

    ASSETS_FONTS.mkdir(parents=True, exist_ok=True)
    out_css: list[str] = []
    for i, block in enumerate(latin_blocks):
        u_m = re.search(r"url\(([^)]+)\)", block)
        if not u_m:
            continue
        url = u_m.group(1).strip('"').replace("&amp;", "&")
        if not url.startswith("http"):
            continue
        fname = f"font-{i}.woff2"
        (ASSETS_FONTS / fname).write_bytes(fetch_bytes(url))
        block2 = re.sub(
            r"url\([^)]+\)\s*format\('woff2'\)",
            f"url('{fname}') format('woff2')",
            block,
            count=1,
        )
        block2 = re.sub(r"unicode-range:[^;]+;", "", block2)
        out_css.append(block2.strip())

    (ASSETS_FONTS / "fonts.css").write_text("\n\n".join(out_css) + "\n", encoding="utf-8")


def patch_astro_bundle_paths() -> None:
    """Vite mapDeps uses _astro-.../ paths rooted at site /; flatten to ./ alongside chunks."""
    old = "_astro-1777938346575/"
    new = "./"
    for p in ASSETS_ASTRO.glob("*.js"):
        t = p.read_text(encoding="utf-8", errors="replace")
        if old not in t:
            continue
        p.write_text(t.replace(old, new), encoding="utf-8")


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    raw_pages: list[str] = []
    for path, fname in URLS:
        url = BASE + "/" if path == "/" else BASE + path
        print("fetch", url)
        raw = fetch(url)
        (CACHE / fname).write_text(raw, encoding="utf-8")
        raw_pages.append(raw)

    parts: list[dict] = []
    for raw in raw_pages:
        try:
            parts.append(load_page_data_from_html(raw))
        except Exception as e:
            print("parse error", e)

    ud = merge_ud(parts)
    ASSETS_SITE.mkdir(parents=True, exist_ok=True)
    ASSETS_MEDIA.mkdir(parents=True, exist_ok=True)

    files = set(collect_site_filenames(ud))
    for raw in raw_pages:
        files |= collect_zyro_filenames_from_html(raw)

    jobs = [(f"{CDN}/{fn}", str(ASSETS_SITE / fn)) for fn in sorted(files)]
    jobs.append((HERO_VIDEO, str(ASSETS_MEDIA / "hero.mp4")))
    jobs.append((HERO_POSTER, str(ASSETS_MEDIA / "hero-poster.jpg")))

    print("download", len(jobs), "site/media files …")
    bad: list[tuple[str, str]] = []
    ok = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(download_one, j) for j in jobs]
        for fut in as_completed(futs):
            dest, success, err = fut.result()
            if success:
                ok += 1
            else:
                bad.append((dest, err))
    print("ok", ok, "fail", len(bad))
    for dest, err in bad[:20]:
        print(" FAIL", dest, err)

    print("fonts …")
    try:
        build_font_css()
    except Exception as e:
        print("font build error", e)

    print("astro bundle …")
    astro_bad = download_astro_bundle()
    for name, err in astro_bad:
        bad.append((name, err))
        print(" FAIL astro", name, err)
    patch_astro_bundle_paths()

    unsplash_all: set[str] = set()
    for raw in raw_pages:
        unsplash_all |= collect_unsplash_urls(raw)
    unsplash_map = build_unsplash_map(unsplash_all)
    print("unsplash local", len(unsplash_map), "/", len(unsplash_all))

    for path, cname in URLS:
        slug = "home" if path == "/" else path.lstrip("/")
        out_path = ROOT / SLUG_TO_FILE[slug]
        raw = (CACHE / cname).read_text(encoding="utf-8")
        out = rewrite_ssr_html(raw)
        out = apply_unsplash_map(out, unsplash_map)
        out_path.write_text(out, encoding="utf-8")
        print("write", out_path.relative_to(ROOT))

    print("done.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
