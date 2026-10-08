"""QA for the website in docs/: static checks on every generated page, then every page in headless Chrome at phone and desktop widths.

Static (no browser):
- no "every restaurant" / "all N restaurants"-style overclaims anywhere (text, meta, alt text, JSON-LD, the web app's strings)
- a Content-Security-Policy meta on every page whose hashes match each inline <script>/<style>; no inline style or on* attributes
- titles 50-60 and descriptions 140-160 characters, unique across indexable pages; one <h1>; sitemap = the indexable pages
- city pages: the title, h1 and description name only sections the page has
- JSON-LD parses; ItemList items point to an anchor on the same page; no aggregateRating/review; no empty streetAddress
- the web app keeps its localStorage under "coeats-" (Connecticut Eats uses "ce-" on the same origin)
- the store button carries no Apple logo; no letter-grade CSS; one place per brewpub license in the published data
Browser (Playwright, channel="chrome"): no horizontal scroll, no console errors, no CSP violations, no broken internal links or
images; the web app loads, searches ("pueblo slopper" finds only slopper places), opens a place, Back closes it, the phone panel is
a modal dialog, a hostile #g= doesn't break it, and saved places use the coeats- prefix.

Usage: .venv/bin/python scripts/qa-site.py            (serves docs/ itself on a free localhost port; exits 1 on any problem)
       .venv/bin/python scripts/qa-site.py --static   (static checks only, a few seconds)
Copied from wi-eats/scripts/qa-site.py. Until the custom domain is live the site sits under /colorado-eats/ on github.io, so the
pages are served under that same path here (a temporary folder with docs/ linked in as colorado-eats/).
"""
import base64
import functools
import glob
import hashlib
import html
import html.parser
import http.server
import json
import os
import re
import sys
import tempfile
import threading
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(__file__), "..")
DOCS = os.environ.get("QA_DOCS") or os.path.join(ROOT, "docs")   # QA_DOCS: check a copy (used to mutation-test these checks)
DOMAIN = open(os.path.join(DOCS, "CNAME")).read().strip() if os.path.exists(os.path.join(DOCS, "CNAME")) else "nickstrom5.github.io"
BASE = re.search(r'data-base="([^"]*)"', open(os.path.join(DOCS, "index.html")).read()).group(1)
STORAGE_PREFIX = "coeats-"

# claims the lists can't back up: the app lists what was checked or matched, never "every"/"all N" restaurants
OVERCLAIMS = [
    r"\bevery\s+(?:single\s+)?(?:colorado\s+|local\s+|licensed\s+)?(?:restaurant|brewpub|bar|caf[eé]|place to eat|eatery)",
    r"\bevery\s+place\s+in\s+(?:colorado|the\s+state)",
    r"\ball\s+(?:of\s+the\s+)?\d[\d,]*\s+(?:\w+\s+){0,2}(?:restaurants|brewpubs|places|spots|caf[eé]s|bars)\b",
    r"\b(?:all|every)\s+(?:the\s+)?(?:restaurants|brewpubs|places)\s+in\s+(?:the\s+state|colorado|town)\b",
    r"\b(?:all|every)\s+(?:of\s+)?colorado'?s\s+(?:restaurants|brewpubs)\b",
    r"\b(?:confirmed|checked|verified)\s+open\b",            # the research dates show when we checked a source, not that it's open now
    r"\bimminent health hazard at any score\b",              # unconfirmed as Colorado's rule; Boulder County records it (AR-15)
]
# Boulder County's September 2025 system move stamped records with this day: it is not an inspection date and is never shown
MIGRATION_DATES = [r"2025-09-03", r"September 3, 2025", r"Sep 3, 2025"]
# city-page words -> the section that backs them
CITY_KEYWORDS = [(r"green chile", "green-chile"), (r"brewpub", "brewpubs"), (r"michelin|james beard|honoree", "honors"),
                 (r"\boldest\b", "oldest"), (r"\bski\b", "ski"), (r"steak|\bgame\b", "game"), (r"inspection", "inspections")]


class Page(html.parser.HTMLParser):
    """The facts the static checks need from one HTML file."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.title, self.desc, self.robots, self.canonical, self.csp = "", None, "", None, None
        self.h1s, self.ids, self.section_ids, self.alts = [], [], set(), []
        self.scripts, self.styles, self.ldjson, self.bad_attrs = [], [], [], []
        self._in, self._buf, self._h1 = None, [], None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k, v in attrs:
            if k == "style" or k.startswith("on"):
                self.bad_attrs.append(f"<{tag} {k}=…>")
        if "id" in a:
            self.ids.append(a["id"])
            if tag == "section":
                self.section_ids.add(a["id"])
        if tag == "img":
            self.alts.append(a.get("alt"))
        if tag == "meta":
            if a.get("name") == "description":
                self.desc = a.get("content", "")
            elif a.get("name") == "robots":
                self.robots = a.get("content", "")
            elif (a.get("http-equiv") or "").lower() == "content-security-policy":
                self.csp = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag in ("script", "style", "title"):
            self._in, self._buf = (tag, a.get("type")), []
        if tag == "h1":
            self._h1 = []

    def handle_endtag(self, tag):
        if self._in and tag == self._in[0]:
            text = "".join(self._buf)
            kind, typ = self._in
            if kind == "title":
                self.title = text
            elif kind == "style":
                self.styles.append(text)
            elif typ == "application/ld+json":
                self.ldjson.append(text)
            elif typ in (None, "", "text/javascript", "module"):
                self.scripts.append(text)
            self._in = None
        if tag == "h1" and self._h1 is not None:
            self.h1s.append("".join(self._h1).strip())
            self._h1 = None

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)
        if self._h1 is not None:
            self._h1.append(data)


def sha(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() + "'"


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path + "." + k, k, v
            yield from walk(v, path + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")


def doc_files():
    return sorted(f for f in glob.glob(os.path.join(DOCS, "**", "*.html"), recursive=True) if "/screenshots/" not in f)


def rel(f):
    return os.path.relpath(f, DOCS)


def page_url(path):
    full = f"https://{DOMAIN}{BASE}" if DOMAIN.endswith("github.io") else f"https://{DOMAIN}"
    return full + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))


def sitemap_paths():
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in ET.parse(os.path.join(DOCS, "sitemap.xml")).getroot().findall("s:url/s:loc", ns)]
    out = []
    for u in locs:
        p = urllib.parse.urlparse(u).path
        if BASE and p.startswith(BASE):
            p = p[len(BASE):]
        p = p.lstrip("/")
        out.append(p + "index.html" if p == "" or p.endswith("/") else p)
    return out


def static_checks():
    problems = []
    pages = {rel(f): open(f, encoding="utf-8").read() for f in doc_files()}
    parsed = {p: Page(t) for p, t in pages.items()}
    in_sitemap = set(sitemap_paths())
    titles, descs = {}, {}
    for path, text in pages.items():
        pg = parsed[path]
        where = path
        indexed = "noindex" not in pg.robots
        # --- overclaims: everything a reader or a crawler sees (CSS aside)
        visible = html.unescape(re.sub(r"<style>.*?</style>", " ", text, flags=re.S))
        visible = re.sub(r"\s+", " ", visible.replace("\\u003c", "<"))
        for rx in OVERCLAIMS:
            for m in re.finditer(rx, visible, re.I):
                problems.append(f"{where}: overclaim \"{m.group(0)}\" (…{visible[max(0, m.start() - 40):m.end() + 20]}…)")
        # --- CSP
        if not pg.csp:
            problems.append(f"{where}: no Content-Security-Policy meta")
        else:
            pol = {d.split()[0]: d.split()[1:] for d in (x.strip() for x in pg.csp.split(";")) if d}
            if pol.get("default-src") != ["'none'"]:
                problems.append(f"{where}: CSP default-src isn't 'none'")
            for name, blocks in (("script-src", pg.scripts), ("style-src", pg.styles)):
                allowed = pol.get(name, [])
                if any(x in allowed for x in ("'unsafe-inline'", "'unsafe-eval'", "*", "https:", "data:")):
                    problems.append(f"{where}: CSP {name} is loose: {allowed}")
                for b in blocks:
                    if sha(b) not in allowed:
                        problems.append(f"{where}: an inline {name.split('-')[0]} block isn't in the CSP (hash {sha(b)[:20]}…)")
            for need in ("base-uri", "form-action", "connect-src", "img-src"):
                if need not in pol:
                    problems.append(f"{where}: CSP has no {need}")
        shown = re.sub(r"<script>.*?</script>", " ", visible, flags=re.S)   # the web app's code names the stamp in order to hide it
        for rx in MIGRATION_DATES:
            if re.search(rx, shown):
                problems.append(f"{where}: shows {rx}, the county's records-migration stamp, as a date")
        if pg.bad_attrs:
            problems.append(f"{where}: inline style/event attributes break the CSP: {pg.bad_attrs[:3]}")
        # --- titles, descriptions, headings, sitemap
        if len(pg.h1s) != 1:
            problems.append(f"{where}: {len(pg.h1s)} <h1>")
        if path != "404.html":
            if not 50 <= len(pg.title) <= 60:
                problems.append(f"{where}: title is {len(pg.title)} characters: {pg.title}")
            if pg.desc is None or not 140 <= len(pg.desc) <= 160:
                problems.append(f"{where}: description is {len(pg.desc or '')} characters")
        if indexed and path != "404.html":
            if pg.title in titles:
                problems.append(f"{where}: same title as {titles[pg.title]}")
            if pg.desc in descs:
                problems.append(f"{where}: same description as {descs[pg.desc]}")
            titles[pg.title], descs[pg.desc] = path, path
            if path not in in_sitemap:
                problems.append(f"{where}: indexable but not in sitemap.xml")
            if pg.canonical != page_url(path):
                problems.append(f"{where}: canonical {pg.canonical} != {page_url(path)}")
        elif path in in_sitemap:
            problems.append(f"{where}: noindex page is in sitemap.xml")
        for a in pg.alts:
            if not a:
                problems.append(f"{where}: an <img> has no alt text")
        dup_ids = {i for i in pg.ids if pg.ids.count(i) > 1}
        if dup_ids:
            problems.append(f"{where}: duplicate ids {sorted(dup_ids)[:5]}")
        # --- city pages: the title, h1 and description promise only what's on the page
        if path.startswith("cities/") and path != "cities/index.html":
            promise = " ".join([pg.title, pg.h1s[0] if pg.h1s else "", pg.desc or ""]).lower()
            for rx, sec in CITY_KEYWORDS:
                if re.search(rx, promise) and sec not in pg.section_ids:
                    problems.append(f"{where}: title/h1/description mention {rx!r} but the page has no #{sec} section")
        # --- JSON-LD
        for raw in pg.ldjson:
            try:
                ld = json.loads(raw)
            except ValueError as ex:
                problems.append(f"{where}: bad JSON-LD ({ex})")
                continue
            if "</" in raw:
                problems.append(f"{where}: JSON-LD contains a raw '</'")
            for p, k, v in walk(ld):
                if k in ("aggregateRating", "review", "reviewRating", "ratingValue"):
                    problems.append(f"{where}: JSON-LD has {k} at {p}")
                if k == "streetAddress" and not str(v).strip():
                    problems.append(f"{where}: empty streetAddress at {p}")
            for block in ([ld] + ld.get("@graph", [])) if isinstance(ld, dict) else []:
                if block.get("@type") != "ItemList":
                    continue
                own_url = pg.canonical or page_url(path)
                items = block.get("itemListElement", [])
                if block.get("numberOfItems") != len(items):
                    problems.append(f"{where}: ItemList numberOfItems {block.get('numberOfItems')} != {len(items)}")
                for li in items:
                    it = li.get("item", {})
                    u = it.get("url", "")
                    if not u.startswith(own_url + "#"):
                        problems.append(f"{where}: ItemList item {it.get('name')!r} url {u!r} isn't on this page")
                    elif u.split("#", 1)[1] not in pg.ids:
                        problems.append(f"{where}: ItemList item {it.get('name')!r} points to #{u.split('#', 1)[1]}, which isn't on the page")
                    s = it.get("sameAs")
                    if s and not re.match(r"https?://", s):
                        problems.append(f"{where}: sameAs {s!r} isn't http(s)")
        # --- links: only http(s), mailto and tel leave the site
        for href in re.findall(r'href="([^"]*)"', text):
            if re.match(r"\s*(javascript|data|vbscript):", href, re.I) and not href.startswith("data:image/svg+xml"):
                problems.append(f"{where}: unsafe link {href[:40]}")
        # --- the App Store button has no Apple logo until it's Apple's own badge
        for m in re.finditer(r'<a class="btn store-btn"[^>]*>(.*?)</a>', text, re.S):
            if "<svg" in m.group(1):
                problems.append(f"{where}: the early-access button carries an Apple logo")
        if re.search(r"\.ex-g-[A-F]\b|\bletter grade\b", text):
            problems.append(f"{where}: letter-grade CSS or wording")
    # --- the web app's storage keys
    ex = parsed.get("explore/index.html")
    if ex:
        js = "\n".join(ex.scripts)
        if f'"{STORAGE_PREFIX}"' not in js:
            problems.append(f"explore/index.html: localStorage prefix {STORAGE_PREFIX!r} not found")
        for m in re.finditer(r"""localStorage\.(?:get|set|remove)Item\(\s*(["'`])([^"'`]*)\1""", js):
            if not m.group(2).startswith(STORAGE_PREFIX):
                problems.append(f"explore/index.html: localStorage key {m.group(2)!r} doesn't start with {STORAGE_PREFIX!r}")
        if re.search(r"""["'`]ce-["'`]""", js):
            problems.append("explore/index.html: still uses Connecticut Eats' \"ce-\" storage prefix")
    else:
        problems.append("explore/index.html is missing")
    # --- one place per brewpub license in the published data (the Brewpubs page and the web app agree)
    try:
        core = json.load(open(os.path.join(DOCS, "data", "core.json")))
        detail = json.load(open(os.path.join(DOCS, "data", "detail.json")))
        seen = {}
        for i, g in enumerate(core["cols"]["g"]):
            if g and g & 2 and core["cols"]["v"][i] != 1:
                for l in (detail[i] or {}).get("lic", []):
                    if str(l.get("type", "")).startswith(("Brew Pub", "Distillery Pub")):
                        if l["id"] in seen:
                            problems.append(f"data: brewpub license {l['id']} on two places: {core['cols']['n'][seen[l['id']]]!r} and {core['cols']['n'][i]!r}")
                        seen[l["id"]] = i
        for i, dt in enumerate(core["cols"].get("idt", [])):
            if dt and str(dt).startswith("2025-09-03"):
                problems.append(f"data: core.json gives {core['cols']['n'][i]!r} the migration stamp 2025-09-03 as its inspection date")
        for i, d in enumerate(detail):
            ins = (d or {}).get("in") or {}
            if any(str(x.get("d") or "").startswith("2025-09-03") for x in [ins] + list(ins.get("h") or [])):
                problems.append(f"data: detail.json gives {core['cols']['n'][i]!r} the migration stamp 2025-09-03 as an inspection date")
            w = (d or {}).get("w")
            if w and not re.match(r"https?://", w):
                problems.append(f"data: website {w!r} for {core['cols']['n'][i]!r} isn't http(s)")
    except (OSError, ValueError, KeyError) as ex:
        problems.append(f"data: couldn't read core/detail.json ({ex})")
    return problems, len(pages)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    root = DOCS
    if BASE:   # serve docs/ at /colorado-eats/, the path GitHub Pages will use
        root = tempfile.mkdtemp()
        os.symlink(os.path.abspath(DOCS), os.path.join(root, BASE.strip("/")))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


def local_exists(path):
    path = urllib.parse.unquote(path.split("#")[0].split("?")[0])
    if BASE and path.startswith(BASE + "/"):
        path = path[len(BASE):]
    f = os.path.join(DOCS, path.lstrip("/"))
    return os.path.isfile(f) or os.path.isfile(os.path.join(f, "index.html"))


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", s.replace("'", "")).strip() + " "


def expected_slopper_hits():
    """Green chile places a search for "slopper" should find: the ones whose name, dishes or address say slopper."""
    core = json.load(open(os.path.join(DOCS, "data", "core.json")))
    C = core["cols"]
    return sum(1 for i in range(len(C["id"])) if C["hc"][i] == 1 and (C["g"][i] or 0) & 1 and C["v"][i] != 1
               and " slopper" in norm(" ".join(str(x) for x in (C["n"][i], C["dish"][i], C["a"][i]) if x)))


CSP_PROBE = """window.__csp = []; document.addEventListener("securitypolicyviolation",
  e => window.__csp.push(e.violatedDirective + " " + (e.blockedURI || "inline") + " @" + (e.sourceFile || "") + ":" + e.lineNumber));"""


def browser_checks(problems):
    from playwright.sync_api import sync_playwright
    base = serve()
    paths = [rel(f) for f in doc_files()]
    urls = [base + BASE + "/" + ("" if p == "index.html" else p.removesuffix("index.html")) for p in paths]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        for width in (375, 1280):
            ctx = browser.new_context(viewport={"width": width, "height": 900})
            ctx.add_init_script(CSP_PROBE)
            page = ctx.new_page()
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for url in urls:
                errors.clear()
                page.goto(url, wait_until="networkidle")
                where = f"{urllib.parse.urlparse(url).path} @{width}"
                over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if over > 1:
                    problems.append(f"{where}: scrolls sideways by {over}px")
                if page.locator("h1").count() != 1:
                    problems.append(f"{where}: {page.locator('h1').count()} <h1>")
                problems += [f"{where}: CSP violation: {v}" for v in page.evaluate("window.__csp || []")]
                if width == 1280:   # links are the same at both widths
                    refs = page.evaluate("""[...document.querySelectorAll('a[href],img[src],link[href],script[src]')]
                        .map(e => e.getAttribute('href') || e.getAttribute('src'))""")
                    for ref in refs:
                        full = urllib.parse.urljoin(url, ref)
                        p = urllib.parse.urlparse(full)
                        if p.scheme in ("mailto", "tel", "data"):
                            continue
                        if p.netloc in (urllib.parse.urlparse(base).netloc, DOMAIN) and not local_exists(p.path):
                            problems.append(f"{where}: broken link {ref}")
                        if p.fragment and p.netloc == urllib.parse.urlparse(base).netloc and p.path == urllib.parse.urlparse(url).path:
                            if not page.evaluate("(id) => !!document.getElementById(id)", urllib.parse.unquote(p.fragment)):
                                problems.append(f"{where}: link to missing #{p.fragment}")
                    imgs = page.evaluate("[...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)")
                    problems += [f"{where}: image didn't load {s}" for s in imgs]
                problems += [f"{where}: console error: {e}" for e in errors]
            # ------------------------------------------------ the web app
            errors.clear()
            ex = base + BASE + "/explore/"
            page.goto(base + BASE + "/", wait_until="networkidle")             # a page before it, so Back has somewhere to leave to
            page.goto(ex + "#g=greenchile", wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=20000)
            search = page.locator('#ex-q').first
            search.fill("slopper")
            page.wait_for_timeout(500)
            want, got = expected_slopper_hits(), page.locator(".ex-row").count()
            if got != want:
                problems.append(f"explore @{width}: 'slopper' listed {got} green chile places, expected the {want} that serve one")
            search.fill("pueblo slopper")
            page.wait_for_timeout(500)
            if not page.locator(".ex-row").count():
                problems.append(f"explore @{width}: search 'pueblo slopper' found nothing")
            else:
                page.locator(".ex-row").first.click()
                page.wait_for_timeout(700)
                panel = page.locator("#ex-panel")
                if not panel.is_visible() or not panel.locator("a", has_text="Directions").count():
                    problems.append(f"explore @{width}: opening a place showed no details")
                else:
                    if width == 375:
                        modal = page.evaluate("""[document.querySelector('#ex-panel').getAttribute('role'),
                            document.querySelector('#ex-panel').getAttribute('aria-modal'), document.querySelector('#ex-app').inert,
                            document.querySelector('footer').inert]""")
                        if modal != ["dialog", "true", True, True]:
                            problems.append(f"explore @{width}: the open place sheet isn't a modal dialog with the page behind it inert: {modal}")
                    page.locator("#ex-save").click()
                    keys = page.evaluate("Object.keys(localStorage)")
                    bad = [k for k in keys if not k.startswith(STORAGE_PREFIX)]
                    if bad or not keys:
                        problems.append(f"explore @{width}: localStorage keys {keys} (want all to start {STORAGE_PREFIX!r})")
                    page.locator("#ex-save").click()
                    page.go_back()
                    page.wait_for_timeout(600)
                    if not page.url.startswith(ex) or panel.is_visible():
                        problems.append(f"explore @{width}: Back with a place open didn't just close it (now at {page.url}, panel visible: {panel.is_visible()})")
                    elif width == 375 and page.evaluate("document.querySelector('#ex-app').inert"):
                        problems.append(f"explore @{width}: the page stayed inert after the sheet closed")
            search.fill("🍕")
            page.wait_for_timeout(400)
            if page.locator(".ex-row").count():
                problems.append(f"explore @{width}: an emoji search listed places")
            for hostile in ("#g=constructor", "#g=__proto__&sort=toString"):
                errors.clear()
                page.goto(ex + hostile, wait_until="networkidle")
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(500)
                if not page.locator(".ex-row").count() or errors:
                    problems.append(f"explore @{width}: {hostile} broke the list ({errors[:1]})")
            page.goto(ex + "#g=honors&sort=nearest", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.wait_for_function("document.querySelectorAll('.ex-row').length > 0", timeout=20000)
            if "Nearest" in page.locator("#ex-count").inner_text():
                problems.append(f"explore @{width}: says 'Nearest' with no location")
            problems += [f"explore @{width}: CSP violation: {v}" for v in page.evaluate("window.__csp || []")]
            problems += [f"explore @{width}: console error: {e}" for e in errors]
            ctx.close()
        browser.close()
    return len(urls)


def main():
    problems, n = static_checks()
    if "--static" in sys.argv:
        print(f"{n} pages, static checks")
    else:
        n = browser_checks(problems)
        print(f"{n} pages × 2 widths + the web app")
    for p in problems:
        print("  ✗", p)
    print("OK" if not problems else f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
