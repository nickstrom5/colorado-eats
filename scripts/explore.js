// Colorado Eats web app: the iPhone app's guides, search, filters, map and place details, in the browser.
// Ported from wi-eats/scripts/explore.js; keep its guide rules in step with ColoradoEats/Models/Guide.swift.
// Same data file as the app (split into core + detail by scripts/make-site.py). No cookies, no trackers;
// saved places and the last guide live in this browser's localStorage only (keys start with coeats-, because Connecticut Eats,
// on the same github.io origin, uses ce-).
// The page runs under a strict Content-Security-Policy (hash-pinned inline script and style): never add inline event
// handlers or inline style attributes to the HTML built here; set properties from code instead.
(() => {
  "use strict";
  const BASE = document.documentElement.dataset.base || "";
  const $ = (s) => document.querySelector(s);
  // every value that goes into innerHTML passes through esc(), numbers included (the data file is trusted, but not that much)
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const own = (o, k) => typeof k === "string" && Object.prototype.hasOwnProperty.call(o, k);   // Object.hasOwn, for older Safari too
  const PREFIX = "coeats-";
  const store = {
    get(k, d) { try { const v = localStorage.getItem(PREFIX + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem(PREFIX + k, JSON.stringify(v)); } catch { /* private mode */ } },
  };
  // only http(s) links leave the page; bare hosts ("example.com/menu") get https://
  const safeUrl = (u) => {
    u = String(u ?? "").trim();
    if (/^https?:\/\/[^\s"'<>\\]+$/i.test(u)) return u;
    if (/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}(?:[/?#][^\s"'<>\\]*)?$/i.test(u)) return "https://" + u;
    return null;
  };
  const num = (x) => (x == null || x === "" || !Number.isFinite(Number(x)) ? null : Number(x));
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const fmtDate = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s ?? "")); return m ? `${MONTHS[+m[2] - 1]} ${+m[3]}, ${m[1]}` : String(s ?? ""); };
  // Boulder County's September 2025 records-system move stamped hundreds of inspections 2025-09-03: not an inspection date, so
  // never shown as one. Missing dates (the pipeline nulls those) read "not published" and sort after dated inspections.
  const MIGRATION_DAY = "2025-09-03";
  const insDate = (s) => { const m = /^\d{4}-\d{2}-\d{2}/.exec(String(s ?? "")); return m && m[0] !== MIGRATION_DAY ? m[0] : null; };
  const NO_DATE_NOTE = "date not published (recorded during Boulder County's September 2025 system move)";

  // ---------------------------------------------------------------- search (a port of ColoradoEats/Models/Search.swift)
  const typeSyn = { avenue: "ave", av: "ave", street: "st", boulevard: "blvd", road: "rd", drive: "dr", place: "pl", court: "ct",
    parkway: "pkwy", highway: "hwy", lane: "ln", trail: "trl", circle: "cir", terrace: "ter" };
  const syn = { ...typeSyn, north: "n", south: "s", east: "e", west: "w", saint: "st", mount: "mt", fort: "ft" };
  const abbrs = new Set(Object.values(syn)), typeAbbrs = new Set(Object.values(typeSyn));
  const CHILE = 1, BREWPUB = 2, GAME = 4, SKITOWN = 8, OLDEST = 16, SKIDINING = 32;
  // dishes such as "slopper" are not tags: they're in each place's search text (its dishes), so they find only the places that serve one
  const tagPhrases = [["green chile", CHILE], ["green chili", CHILE], ["green chilli", CHILE],
    ["smothered burrito", CHILE], ["brewpubs", BREWPUB], ["brew pubs", BREWPUB], ["brewpub", BREWPUB], ["brew pub", BREWPUB],
    ["ski towns", SKITOWN], ["ski town", SKITOWN]];
  function normalize(s) {
    let t = String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    t = t.replace(/\b([a-z0-9])\s*&\s*([a-z0-9])\b/g, "$1$2").replace(/&/g, " and ").replace(/['’`]/g, "");
    return t.replace(/[^\p{L}\p{N}]+/gu, " ").trim();
  }
  const normAddr = (s) => normalize(s).split(" ").map((w) => syn[w] || w).join(" ");

  function parse(text) {
    const q = { tokens: [], town: null, townPhrase: null, tag: 0, tagPhrase: null };
    let raw = normalize(text).split(" ").filter(Boolean);
    if (!raw.length) return q;
    let mapped = raw.map((w) => syn[w] || w);
    const find = (phrase) => {
      const p = phrase.split(" ");
      for (let i = 0; i + p.length <= mapped.length; i++) if (p.every((w, k) => mapped[i + k] === w)) return [i, i + p.length];
      return null;
    };
    const cut = ([a, b]) => { const words = raw.slice(a, b).join(" "); raw.splice(a, b - a); mapped.splice(a, b - a); return words; };
    for (const [phrase, tag] of tagPhrases) { const r = find(normalize(phrase)); if (r) { q.tag = tag; q.tagPhrase = cut(r); break; } }
    for (const key of TOWN_KEYS_BY_LENGTH) {
      const r = find(key);
      if (r && !(r[1] < mapped.length && typeAbbrs.has(mapped[r[1]]))) { q.town = TOWN_KEYS[key]; q.townPhrase = cut(r); break; }
    }
    const stop = new Set(["the", "and", "of", "a", "in", "near"]);
    let idx = raw.map((_, i) => i);
    if (idx.some((i) => !stop.has(mapped[i]))) idx = idx.filter((i) => !stop.has(mapped[i]));
    idx.forEach((i, n) => {
      const token = raw[i], isLast = n === idx.length - 1;
      if (own(syn, token)) { q.tokens.push([` ${syn[token]} `, ` ${token}`]); return; }
      const whole = (abbrs.has(token) && (!isLast || token.length > 1)) || (token.length <= 2 && !isLast);
      const needles = [" " + token + (whole ? " " : "")];
      if (isLast && token.length >= 3) for (const [word, abbr] of Object.entries(typeSyn)) if (word !== token && word.startsWith(token)) needles.push(` ${abbr} `);
      q.tokens.push(needles);
    });
    if (q.tokens.length >= 2 && idx.length && typeAbbrs.has(mapped[idx[idx.length - 1]])) {
      const last = idx[idx.length - 1], prev = idx[idx.length - 2];
      q.tokens.splice(-2, 2, [` ${mapped[prev]} ${mapped[last]} `, ` ${raw[prev]} ${raw[last]}`]);
    }
    return q;
  }
  const qEmpty = (q) => !q.tokens.length && !q.town && !q.tag;
  function matches(p, q) {
    if (q.tag && !(p.g & q.tag)) {
      const stem = normalize(q.tagPhrase || "").replace(/s$/, "");
      if (!stem || !p.nameText.includes(" " + stem)) return false;
    }
    if (q.town && p.c !== q.town && !p.nameText.includes(" " + normalize(q.townPhrase || ""))) return false;
    return q.tokens.every((needles) => needles.some((n) => p.search.includes(n)));
  }
  const nameMatches = (p, q) => q.tokens.length && q.tokens.every((needles) => needles.some((n) => p.nameText.includes(n)));

  // ---------------------------------------------------------------- guides (ColoradoEats/Models/Guide.swift)
  const TIERS = "Colorado's tiers: Pass (0–49 risk points), Re-Inspection Required (50–109) or Closure (110+ points). Boulder County also records a Closure when it closes a place for an imminent health hazard, such as a sewage backup, whatever the points. Fewer points is better.";
  const GUIDES = {
    greenchile: { title: "Green Chile", sub: "Hand-checked smothered burritos, Pueblo sloppers and chile by the bowl", inc: (p) => p.hc && p.g & CHILE, sorts: ["featured", "nearest", "name"] },
    brewpubs: { title: "Brewpubs", sub: "Places with a Colorado Brew Pub or Distillery Pub license", inc: (p) => p.g & BREWPUB, sorts: ["name", "nearest"] },
    ski: { title: "Ski Town Dining", sub: "Hand-checked dining in Aspen, Vail, Breckenridge, Telluride and more", inc: (p) => p.hc && p.g & SKIDINING, sorts: ["featured", "nearest", "name"] },
    game: { title: "Game & Steakhouses", sub: "Bison, elk, trout and steak, hand-checked", inc: (p) => p.hc && p.g & GAME, sorts: ["featured", "nearest", "name"] },
    honors: { title: "MICHELIN & James Beard", sub: "MICHELIN Guide Colorado 2026 and James Beard honorees", inc: (p) => p.mi > 0 || p.jb, sorts: ["iconic", "nearest"] },
    oldest: { title: "Oldest Places", sub: "Founding years at the same address, as each place documents them, oldest first", inc: (p) => p.f != null, sorts: ["oldest"], ranked: true },
    inspections: { title: "Inspections", sub: "Boulder County's official inspection results: each place's result at its latest inspection, as recorded. " + TIERS, inc: (p) => p.ir != null, sorts: ["recent", "fewest", "most", "nearest"] },
    all: { title: "All Restaurants", sub: "Restaurants, cafés, bars and bakeries statewide", inc: () => true, sorts: ["name", "nearest"] },
    saved: { title: "Saved", sub: "Places you saved in this browser", inc: (p) => saved.has(p.id), sorts: ["name", "nearest"] },
  };
  const SORT_LABEL = { featured: "Featured first", nearest: "Nearest", oldest: "Oldest first", name: "A to Z", iconic: "MICHELIN, then James Beard",
    recent: "Latest inspection first", fewest: "Fewest risk points", most: "Most risk points" };
  const RES = ["Pass", "Re-Inspection Required", "Closure"];
  const resCls = (r) => (r === 0 || r === 1 || r === 2 ? r : "x");
  const MI = ["", "MICHELIN Recommended", "Bib Gourmand", "1 MICHELIN Star", "2 MICHELIN Stars", "3 MICHELIN Stars"];

  // ---------------------------------------------------------------- state
  let P = [], D = null, CAL = {}, TOWN_KEYS = {}, TOWN_KEYS_BY_LENGTH = [], GENERATED = "";
  let here = null, shown = 100, current = [], view = "list";
  const savedRaw = store.get("saved", []);
  const saved = new Set(Array.isArray(savedRaw) ? savedRaw.filter((x) => typeof x === "string" && x.length < 64) : []);
  const st = { g: "greenchile", q: "", sort: "", town: "", cuisine: "", chains: false, p: "" };

  const miles = (a, b) => {
    const r = Math.PI / 180, dLa = (b.la - a.la) * r, dLo = (b.lo - a.lo) * r;
    const h = Math.sin(dLa / 2) ** 2 + Math.cos(a.la * r) * Math.cos(b.la * r) * Math.sin(dLo / 2) ** 2;
    return 3958.8 * 2 * Math.asin(Math.sqrt(h));
  };
  const milesText = (m) => (m < 10 ? m.toFixed(1) : Math.round(m)) + " mi";

  function order() {
    const g = GUIDES[st.g];
    let o = st.sort && g.sorts.includes(st.sort) ? st.sort : ["greenchile", "ski", "game"].includes(st.g) && here ? "nearest" : g.sorts[0];
    if (o === "nearest" && !here) o = g.sorts.find((s) => s !== "nearest") || o;   // no location yet: say what the list is really sorted by
    return o;
  }

  function allows(p) {
    if (p.v && st.g !== "saved") return false;            // gas-station counters, stadium stands and the like
    if (st.town && p.c !== st.town) return false;
    if (st.cuisine && p.cu !== st.cuisine) return false;
    if (st.chains && p.ch >= 5) return false;
    return true;
  }

  function list() {
    const g = GUIDES[st.g], q = parse(st.q), o = order();
    if (qEmpty(q) && st.q.trim()) return [];   // typed something, but nothing searchable ("🍕", "!!!")
    let out = P.filter((p) => g.inc(p) && allows(p) && (qEmpty(q) || matches(p, q)));
    const byName = (a, b) => a.n.localeCompare(b.n, "en", { sensitivity: "base" });
    const dist = (p) => (here && p.la != null ? miles(here, p) : Infinity);
    if (o === "nearest" && here) out.sort((a, b) => dist(a) - dist(b) || byName(a, b));
    else if (o === "featured") out.sort((a, b) => (b.ip ?? -1) - (a.ip ?? -1) || (a.f ?? 9999) - (b.f ?? 9999) || byName(a, b));
    else if (o === "oldest") out.sort((a, b) => (a.f ?? 9999) - (b.f ?? 9999) || byName(a, b));
    else if (o === "iconic") {   // MICHELIN distinction, then the James Beard honor, then name (the app's order)
      const jb = (p) => (p.h & 1 ? 4 : p.h & 2 ? 3 : p.h & 4 ? 2 : p.h & 8 ? 1 : 0);
      out.sort((a, b) => (b.mi || 0) - (a.mi || 0) || jb(b) - jb(a) || byName(a, b));
    }
    else if (o === "recent") out.sort((a, b) => (b.idt ? 1 : 0) - (a.idt ? 1 : 0) || String(b.idt || "").localeCompare(String(a.idt || "")) || byName(a, b));
    else if (o === "fewest") out.sort((a, b) => (a.ipt ?? 0) - (b.ipt ?? 0) || byName(a, b));
    else if (o === "most") out.sort((a, b) => (b.ipt ?? 0) - (a.ipt ?? 0) || byName(a, b));
    else out.sort(byName);
    if (q.tokens.length && !g.ranked) {       // name matches first when searching
      const named = out.filter((p) => nameMatches(p, q));
      if (named.length && named.length < out.length) { const ids = new Set(named); out = named.concat(out.filter((p) => !ids.has(p))); }
    }
    return out;
  }

  // ---------------------------------------------------------------- rendering
  function chips(p, max) {
    const c = [];
    const jb = p.h & 1 ? "America's Classic" : p.h & 2 ? "James Beard winner" : p.h & 4 ? "James Beard finalist" : p.h & 8 ? "James Beard semifinalist" : null;
    if (p.mi && MI[p.mi]) c.push(`<span class="tag tag-mi">${esc(MI[p.mi])}</span>`);
    if (jb) c.push(`<span class="tag tag-jb">${esc(jb)}</span>`);
    if (p.hc && p.g & CHILE) c.push('<span class="tag">Green chile</span>');
    if (p.g & BREWPUB) c.push('<span class="tag">Brewpub</span>');
    if (p.hc && p.g & GAME) c.push('<span class="tag">Game &amp; steak</span>');
    if (p.g & OLDEST && p.f) c.push(`<span class="tag tag-plain">Since ${esc(p.f)}</span>`);
    if (p.ch >= 5) c.push(`<span class="tag tag-plain">Chain · ${esc(p.ch)}</span>`);
    if (p.t === 0 && !p.h && !p.mi && !p.hc) c.push('<span class="tag tag-dash">Listing only</span>');
    return (max ? c.slice(0, max) : c).join("");
  }

  function metric(p, o) {
    if (o === "nearest" && here && p.la != null) return [milesText(miles(here, p)), "away"];
    if (p.ir != null && st.g === "inspections") return [RES[p.ir] || "", `${p.ipt ?? "?"} risk pts · ${p.idt ? fmtDate(p.idt) : "date not published"}`];
    if (p.f && st.g !== "all") return [String(p.f), "since"];
    return null;
  }

  function render() {
    const g = GUIDES[st.g], o = order();
    current = list();
    document.querySelectorAll(".ex-guides button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.g === st.g)));
    $("#ex-sub").textContent = g.sub;
    const sortSel = $("#ex-sort");
    sortSel.innerHTML = g.sorts.map((s) => `<option value="${esc(s)}"${s === o ? " selected" : ""}>${esc(SORT_LABEL[s])}</option>`).join("");
    sortSel.disabled = g.sorts.length < 2;
    const filters = [st.town && `in ${st.town}`, st.cuisine && st.cuisine, st.chains && "no chains"].filter(Boolean);
    $("#ex-count").textContent = `${current.length.toLocaleString()} ${current.length === 1 ? "place" : "places"} · ${SORT_LABEL[o]}` + (filters.length ? ` · ${filters.join(", ")}` : "");
    $("#ex-clear").hidden = !filters.length;
    $("#ex-locate").hidden = Boolean(here);
    if (view === "list") renderList(o); else drawMap();
    saveHash();
  }

  function renderList(o) {
    const ol = $("#ex-list");
    const g = GUIDES[st.g];
    if (!current.length) {
      ol.innerHTML = `<li class="ex-empty">${st.g === "saved" ? "Nothing saved yet. Open a place and tap Save to keep it here, in this browser." : "No places match. Try fewer words or clear the filters."}</li>`;
      $("#ex-more").hidden = true;
      return;
    }
    ol.innerHTML = current.slice(0, shown).map((p, i) => {
      const m = metric(p, o);
      const rank = g.ranked ? `<span class="ex-rank${i < 3 ? " top" : ""}" aria-label="Rank ${i + 1}">${i + 1}</span>` : "";
      const where = st.g === "inspections" ? [p.a, p.c].filter(Boolean).join(", ") : [p.c, p.cu].filter(Boolean).join(" · ");
      const big = st.g === "inspections" && m ? `<span class="ex-res ex-res-${resCls(p.ir)}">${esc(m[0])}</span>` : m ? `<b>${esc(m[0])}</b>` : "";
      return `<li><button class="ex-row" data-i="${esc(p.i)}">${rank}<span class="ex-main"><b>${esc(p.n)}</b><span class="ex-town">${esc(where)}</span><span class="ex-chips">${chips(p, 4)}</span></span>${m ? `<span class="ex-metric">${big}<small>${esc(m[1])}</small></span>` : ""}</button></li>`;
    }).join("");
    const left = current.length - shown;
    $("#ex-more").hidden = left <= 0;
    $("#ex-more").textContent = `Show more (${left.toLocaleString()} left)`;
  }

  // ---------------------------------------------------------------- place panel
  const JUR = { 1: "City and County of Denver business licenses", 2: "Boulder County Public Health inspection records", 3: "Colorado liquor licenses" };
  const TIER = { 2: "On an official record", 1: "Confirmed listing", 0: "Listing only" };

  function rate(p) {
    const src = SOURCES[p.s] || "meta";
    const group = src === "meta" ? (p.t === 1 ? "meta_high" : "meta_mid") : (src === "AllThePlaces" || src === "DAC") ? "brand_feed" : null;
    if (!group) return null;
    const v = ["Denver", "Boulder County"].map((a) => CAL[a]?.groups?.[group]?.official).filter((x) => typeof x === "number");
    if (!v.length) return null;
    const lo = Math.round(Math.min(...v) * 100), hi = Math.round(Math.max(...v) * 100);
    return lo === hi ? `${lo}%` : `${lo}–${hi}%`;
  }

  function howWeKnow(p) {
    const src = SOURCES[p.s] || "meta";
    if (src === "research") return "On our hand-checked list (checked in Sep–Oct 2026 against a 2025 or 2026 source). The open map data didn't list it as a place to eat, so it's placed from its own map listing or street address.";
    if (p.t === 2) return src === "official"
      ? `From the ${JUR[p.j] || "official records"}. The open map data didn't have it, so its location comes from the record's street address.`
      : `Matched to the ${JUR[p.j] || "official records"}.`;
    const r = rate(p);
    return (p.t === 1 ? "A high-confidence listing in Overture's open map data." : "A single listing in Overture's open map data, so it may be closed or misfiled.")
      + (r ? ` Checked against Denver's licenses and Boulder County's inspected facilities, listings like this matched an official record ${r} of the time.` : "")
      + (p.hc ? " It's also on our hand-checked list, checked in Sep–Oct 2026 against a 2025 or 2026 source." : "");
  }

  const kv = (k, v) => (v == null || v === "" ? "" : `<div class="ex-kv"><span>${esc(k)}</span><b>${esc(v)}</b></div>`);
  const section = (t, body) => `<section class="ex-sec"><h3>${esc(t)}</h3>${body}</section>`;
  const phone = matchMedia("(max-width: 600px)");
  let listAtPush = null;   // the list's URL state when a place was opened with pushState (Back then closes the panel)

  // on phones the panel is a bottom sheet over the page: a modal dialog, with everything behind it inert
  function panelMode() {
    const panel = $("#ex-panel"), open = !panel.hidden, modal = open && phone.matches;
    if (modal) { panel.setAttribute("role", "dialog"); panel.setAttribute("aria-modal", "true"); }
    else { panel.removeAttribute("role"); panel.removeAttribute("aria-modal"); }
    const behind = [...document.querySelectorAll("body > .skip, .wrap > header, .wrap > nav, .wrap > footer, #main > *")].filter((el) => el !== panel);
    behind.forEach((el) => { el.inert = modal; });
  }

  function openPlace(p, push = true) {
    const panel = $("#ex-panel");
    const wasOpen = !panel.hidden;
    st.p = p.id;
    const d = (D && D[p.i]) || {};
    const la = num(p.la), lo = num(p.lo);
    const addr = [p.a, [p.c, p.z].filter(Boolean).join(" ")].filter(Boolean).join(", ");
    const apple = la != null && lo != null
      ? `https://maps.apple.com/?q=${encodeURIComponent(p.n)}&ll=${la},${lo}`
      : `https://maps.apple.com/?q=${encodeURIComponent(p.n + ", " + addr)}`;
    const dirs = la != null && lo != null ? `https://maps.apple.com/?daddr=${la},${lo}&dirflg=d` : apple;
    const site = safeUrl(d.w);
    const tel = d.ph ? String(d.ph).replace(/[^\d+]/g, "") : "";
    let html = `<button class="ex-close" id="ex-close" aria-label="Close">×</button>
      <p class="ex-kicker">${esc((p.c || "Colorado").toUpperCase())}</p>
      <h2 id="ex-pname">${esc(p.n)}</h2>
      <p class="ex-addr">${esc([addr, p.cu].filter(Boolean).join(" · "))}</p>
      ${here && la != null ? `<p class="ex-dist">${esc(milesText(miles(here, p)))} away</p>` : ""}
      <p class="ex-chips">${chips(p)}</p>
      <div class="ex-actions">
        <a class="btn ex-apple" href="${esc(apple)}" rel="noopener" target="_blank">Ratings, hours &amp; photos · Apple Maps</a>
        <div class="ex-act-row">
          <a href="${esc(dirs)}" rel="noopener" target="_blank">Directions</a>
          ${tel ? `<a href="tel:${esc(tel)}">Call</a>` : ""}
          ${site ? `<a href="${esc(site)}" rel="noopener nofollow" target="_blank">Website</a>` : ""}
          <button id="ex-save" aria-pressed="${saved.has(p.id)}">${saved.has(p.id) ? "Saved" : "Save"}</button>
        </div>
      </div>`;
    if (p.hc && (d.note || d.dish || p.f || d.seas)) {
      html += section("Hand-checked", (d.note ? `<p>${esc(d.note)}</p>` : "") + kv("On the menu", d.dish ? String(d.dish).split("; ").join(", ") : "")
        + kv("Open here since", p.f) + (d.fn ? `<p class="ex-fine">${esc(d.fn)}</p>` : "") + kv("Season", d.seas)
        + `<p class="ex-fine">Checked in Sep–Oct 2026 against a 2025 or 2026 source: the place's own site or menu, or local news. Menus and seasons change, and mountain places close for mud season in spring and fall, so check before you go.</p>`);
    }
    if (p.mi || d.jbf) {
      const lines = [...(p.mi && MI[p.mi] ? [MI[p.mi] + " · MICHELIN Guide Colorado 2026"] : []), ...(d.jbf ? String(d.jbf).split("; ").map((x) => "James Beard: " + x) : [])];
      html += section("Honors", `<ul>${lines.map((l) => `<li>${esc(l)}</li>`).join("")}</ul><p class="ex-fine">Honors are facts, not ratings. MICHELIN is a trademark of Michelin; James Beard Award is a trademark of the James Beard Foundation.</p>`);
    }
    if (d.in && typeof d.in === "object") {
      const i = d.in, pts = num(i.p), latest = insDate(i.d);
      const hist = Array.isArray(i.h) ? i.h : [], cited = Array.isArray(i.i) ? i.i : [];
      html += section("Health inspections · Boulder County",
        `<p class="ex-result"><span class="ex-res ex-res-${resCls(i.r)}">${esc(RES[i.r] || "")}</span> Latest inspection${latest ? " " + esc(fmtDate(latest)) : ": " + esc(NO_DATE_NOTE)} · ${esc(pts ?? "?")} risk point${pts === 1 ? "" : "s"}</p>`
        // in the county's order: two inspections on one day (a routine, then its re-inspection) are both listed
        + `<ul>${hist.map((v) => `<li>${esc(insDate(v.d) ? fmtDate(insDate(v.d)) : "Date not published")} · ${[v.t, RES[v.r], v.p != null ? v.p + " pts" : ""].filter(Boolean).map(esc).join(" · ")}</li>`).join("")}</ul>`
        + (cited.length ? `<p class="ex-fine">Cited at the latest inspection: ${esc(cited.slice(0, 8).join("; "))}${cited.length > 8 ? "…" : ""}</p>` : "")
        + `<p class="ex-fine">${esc(TIERS)} Source: Boulder County Public Health on data.colorado.gov. These are the county's recorded results, not a grade of ours; one inspection is a snapshot of one day.</p>`);
    }
    const lics = Array.isArray(d.lic) ? d.lic : [];
    // a past expiry date reads like a lapsed license, so only a date still ahead is shown
    const lic = lics.map((l) => kv(l.src, [l.type, l.id, l.exp && String(l.exp) >= String(GENERATED) && "expires " + fmtDate(l.exp)].filter(Boolean).join(" · "))).join("");
    const liquorLic = lics.some((l) => /liquor/i.test(String(l.src)));
    html += section("Official records", lic + kv("Serves alcohol", d.liq ? `Yes · ${d.liq} license` : liquorLic ? "" : "Not matched to a state liquor license (unknown)")
      + `<p class="ex-fine">${lic || d.in ? "From the City and County of Denver's active business licenses, the State of Colorado's active liquor licenses and Boulder County's inspections." : "No Denver license, state liquor license or Boulder County inspection record matched this place. Most Colorado counties don't publish their records in bulk, so a missing record means unknown, not unlicensed."}</p>`);
    html += section("How we know it's here", kv("Listed as", TIER[p.t]) + (p.t === 2 ? kv("Official record", JUR[p.j]) : "")
      + (p.ch >= 2 ? kv("Locations in Colorado", p.ch.toLocaleString()) : "") + `<p class="ex-fine">${esc(howWeKnow(p))}</p>`);
    const store_url = safeUrl(window.APP_STORE_URL);   // set in the page footer script once the App Store listing exists
    html += store_url
      ? `<p class="ex-app">Save it on your phone: <a href="${esc(store_url)}" rel="noopener">get the free iPhone app</a></p>`
      : `<p class="ex-app">The iPhone app is coming soon. <a href="${BASE}/#download">Get early access</a></p>`;
    panel.innerHTML = html;
    panel.dataset.id = p.id;
    panel.hidden = false;
    document.body.classList.add("ex-open");
    panelMode();
    $("#ex-close").onclick = () => closePlace();
    $("#ex-save").onclick = (e) => {
      if (saved.has(p.id)) saved.delete(p.id); else saved.add(p.id);
      store.set("saved", [...saved]);
      e.target.textContent = saved.has(p.id) ? "Saved" : "Save";
      e.target.setAttribute("aria-pressed", String(saved.has(p.id)));
      if (st.g === "saved") render();
    };
    panel.scrollTop = 0;
    $("#ex-close").focus();
    if (push) {
      if (wasOpen) saveHash();            // one Back step per panel, not per place looked at
      else { listAtPush = listHash(); saveHash(true); }
    }
    if (!D) loadDetail().then(() => { if (st.p === p.id) openPlace(p, false); });
  }

  // fromHistory: the Back button (or a hash link) already moved the URL, so don't touch history again
  function closePlace(fromHistory = false) {
    const was = st.p;
    st.p = "";
    const panel = $("#ex-panel");
    panel.hidden = true;
    delete panel.dataset.id;
    document.body.classList.remove("ex-open");
    panelMode();
    if (!fromHistory) {
      // the list hasn't changed since the panel opened: step back over the entry openPlace pushed, so Back isn't a dead click
      if (history.state && history.state.coeats === "place" && listHash() === listAtPush) history.back();
      else saveHash();
    }
    listAtPush = null;
    const row = was && document.querySelector(`.ex-row[data-i="${P.findIndex((p) => p.id === was)}"]`);
    if (row) row.focus();
  }

  // ---------------------------------------------------------------- map (canvas: county outlines + a dot per place)
  let SHAPES = null, cam = null;
  const LAT0 = 39.0, KX = Math.cos(LAT0 * Math.PI / 180);
  const proj = (lo, la) => [(lo + 105.5) * KX, -(la - LAT0)];

  function fitCam(w, h) {
    const [x0, y0] = proj(-109.1, 41.05), [x1, y1] = proj(-102.0, 36.95);
    const k = Math.min(w / (x1 - x0), h / (y1 - y0)) * 0.95;
    return { k, x: (w - (x1 - x0) * k) / 2 - x0 * k, y: (h - (y1 - y0) * k) / 2 - y0 * k };
  }

  // calls f on every ring, however deeply it's nested (the state is [polygon[ring[point]]], each county [ring[point]])
  const eachRing = (g, f) => {
    if (!Array.isArray(g) || !g.length) return;
    if (Array.isArray(g[0]) && typeof g[0][0] === "number") f(g); else g.forEach((x) => eachRing(x, f));
  };

  async function drawMap() {
    const cv = $("#ex-map"), wrap = $("#ex-mapwrap");
    const w = wrap.clientWidth, h = wrap.clientHeight, dpr = window.devicePixelRatio || 1;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    if (!cam) cam = fitCam(w, h);
    if (!SHAPES) SHAPES = await fetchJSON(`${BASE}/data/co_shapes.json`).catch(() => ({ state: [], counties: [] }));
    const c = cv.getContext("2d");
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, w, h);
    const X = (lo, la) => { const [x, y] = proj(lo, la); return [x * cam.k + cam.x, y * cam.k + cam.y]; };
    const ring = (r) => { r.forEach(([lo, la], i) => { const [x, y] = X(lo, la); i ? c.lineTo(x, y) : c.moveTo(x, y); }); c.closePath(); };
    c.fillStyle = "#fff";   // the map stays light in dark mode (its frame is light too), so the navy dots keep their contrast
    c.beginPath(); eachRing(SHAPES.state, ring); c.fill("evenodd");
    c.strokeStyle = "rgba(85,98,122,.35)"; c.lineWidth = 0.8;
    for (const co of SHAPES.counties || []) { c.beginPath(); eachRing(co.c, ring); c.stroke(); }
    const pts = current.filter((p) => p.la != null);
    const r = Math.max(2.2, Math.min(5, 1.6 + cam.k / 120));
    for (const classic of [false, true]) {
      c.fillStyle = classic ? "#ffd700" : "#002868";
      c.strokeStyle = "#002868"; c.lineWidth = 1;
      for (const p of pts) {
        if (Boolean((p.hc && p.g & (CHILE | GAME | SKIDINING)) || p.g & BREWPUB || p.mi) !== classic) continue;
        const [x, y] = X(p.lo, p.la);
        if (x < -5 || y < -5 || x > w + 5 || y > h + 5) continue;
        c.beginPath(); c.arc(x, y, classic ? r + 1 : r, 0, 6.2832); c.fill(); if (classic) c.stroke();
      }
    }
    $("#ex-maphint").textContent = pts.length ? `${pts.length.toLocaleString()} ${pts.length === 1 ? "place" : "places"} · tap a dot` : "No places to show";
  }

  function nearestDot(px, py) {
    let best = null, bd = 14 * 14;
    for (const p of current) {
      if (p.la == null) continue;
      const [x0, y0] = proj(p.lo, p.la), x = x0 * cam.k + cam.x, y = y0 * cam.k + cam.y;
      const d = (x - px) ** 2 + (y - py) ** 2;
      if (d < bd) { bd = d; best = p; }
    }
    return best;
  }

  function zoomAt(f, px, py) {
    const k = Math.min(Math.max(cam.k * f, 40), 60000);
    const s = k / cam.k;
    cam = { k, x: px - (px - cam.x) * s, y: py - (py - cam.y) * s };
    drawMap();
  }

  function mapEvents() {
    const cv = $("#ex-map");
    const ptrs = new Map();
    let moved = false, pinch0 = null;
    cv.addEventListener("wheel", (e) => { e.preventDefault(); const b = cv.getBoundingClientRect(); zoomAt(e.deltaY < 0 ? 1.25 : 0.8, e.clientX - b.left, e.clientY - b.top); }, { passive: false });
    cv.addEventListener("pointerdown", (e) => { loadDetail(); cv.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]); moved = false; pinch0 = null; });
    cv.addEventListener("pointermove", (e) => {
      if (!ptrs.has(e.pointerId)) return;
      const prev = ptrs.get(e.pointerId);
      ptrs.set(e.pointerId, [e.clientX, e.clientY]);
      if (ptrs.size === 2) {
        const [a, b] = [...ptrs.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
        const r = cv.getBoundingClientRect();
        if (pinch0) zoomAt(d / pinch0, (a[0] + b[0]) / 2 - r.left, (a[1] + b[1]) / 2 - r.top);
        pinch0 = d; moved = true; return;
      }
      const dx = e.clientX - prev[0], dy = e.clientY - prev[1];
      if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
      cam.x += dx; cam.y += dy; drawMap();
    });
    const up = (e) => {
      ptrs.delete(e.pointerId);
      if (!moved && ptrs.size === 0) {
        const b = cv.getBoundingClientRect(), p = nearestDot(e.clientX - b.left, e.clientY - b.top);
        if (p) openPlace(p);
      }
      if (ptrs.size < 2) pinch0 = null;
    };
    cv.addEventListener("pointerup", up);
    cv.addEventListener("pointercancel", (e) => ptrs.delete(e.pointerId));
    $("#ex-zin").onclick = () => zoomAt(1.6, cv.clientWidth / 2, cv.clientHeight / 2);
    $("#ex-zout").onclick = () => zoomAt(0.625, cv.clientWidth / 2, cv.clientHeight / 2);
    window.addEventListener("resize", () => { if (view === "map") drawMap(); });
  }

  function centerOn(pt) {
    const cv = $("#ex-map"), w = cv.clientWidth, h = cv.clientHeight;
    const k = 4000, [x, y] = proj(pt.lo, pt.la);
    cam = { k, x: w / 2 - x * k, y: h / 2 - y * k };
  }

  // ---------------------------------------------------------------- data, URL state, controls
  let SOURCES = [];
  async function fetchJSON(url) { const r = await fetch(url); if (!r.ok) throw new Error(r.status + " " + url); return r.json(); }
  let detailPromise = null;
  // detail.json (addresses' extras, notes, licenses, inspections) is fetched only once someone reaches for a place
  function loadDetail() {
    detailPromise ||= fetchJSON(`${BASE}/data/detail.json`).then((d) => { D = Array.isArray(d) ? d : []; }).catch(() => { D = []; });
    return detailPromise;
  }

  async function load() {
    const d = await fetchJSON(`${BASE}/data/core.json`);
    GENERATED = d.generated; CAL = d.calibration || {}; SOURCES = d.srcs || [];
    const C = d.cols, n = C.id.length, towns = new Map();
    P = new Array(n);
    for (let i = 0; i < n; i++) {
      const city = C.c[i] == null ? null : d.cities[C.c[i]], cu = d.cuisines[C.cu[i]], brand = C.b[i] == null ? null : d.brands[C.b[i]];
      const county = C.co[i] == null ? null : d.counties[C.co[i]];
      const p = { i, id: String(C.id[i]), n: String(C.n[i] ?? ""), c: city, cu, t: C.t[i], s: C.s[i], a: C.a[i], z: C.z[i], la: C.la[i], lo: C.lo[i],
        ch: num(C.ch[i]) || 1, v: C.v[i] === 1, g: C.g[i] || 0, hc: C.hc[i] === 1, ip: C.ip[i], f: num(C.f[i]), h: C.h[i] || 0, j: C.j[i],
        mi: num(C.mi[i]) || 0, jb: C.jb[i] === 1, dish: C.dish[i], ir: C.ir[i], ipt: num(C.ipt[i]), idt: insDate(C.idt[i]) };
      p.search = " " + normalize([p.n, city, county, p.z, cu, brand, p.dish].filter(Boolean).join(" ")) + " " + normAddr(p.a || "") + " ";
      p.nameText = " " + normalize([p.n, brand].filter(Boolean).join(" ")) + " ";
      P[i] = p;
      if (city && !p.v) towns.set(city, (towns.get(city) || 0) + 1);
    }
    const byCount = [...towns.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    for (const [name] of byCount) { const k = normAddr(name); if (!own(TOWN_KEYS, k)) TOWN_KEYS[k] = name; }
    TOWN_KEYS_BY_LENGTH = Object.keys(TOWN_KEYS).sort((a, b) => b.length - a.length);
    $("#ex-town").innerHTML = '<option value="">All towns</option>' + [...towns.keys()].sort((a, b) => a.localeCompare(b)).map((t) => `<option>${esc(t)}</option>`).join("");
    const cuis = new Map();
    for (const p of P) if (!p.v) cuis.set(p.cu, (cuis.get(p.cu) || 0) + 1);
    $("#ex-cuisine").innerHTML = '<option value="">All kinds</option>' + [...cuis.entries()].sort((a, b) => b[1] - a[1]).map(([c, k]) => `<option value="${esc(c)}">${esc(c)} (${esc(k.toLocaleString())})</option>`).join("");
  }

  const guideOk = (g) => own(GUIDES, g);
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    const last = store.get("guide", "greenchile");
    // a returning visitor gets the guide they used last, unless it's an empty Saved list
    st.g = guideOk(h.get("g")) ? h.get("g") : guideOk(last) && !(last === "saved" && !saved.size) ? last : "greenchile";
    st.q = h.get("q") || ""; st.town = h.get("town") || ""; st.cuisine = h.get("kind") || ""; st.chains = h.get("chains") === "1";
    st.sort = h.get("sort") || ""; st.p = h.get("p") || "";
  }
  function hashOf(withPlace) {
    const h = new URLSearchParams();
    h.set("g", st.g);
    if (st.q) h.set("q", st.q); if (st.town) h.set("town", st.town); if (st.cuisine) h.set("kind", st.cuisine);
    if (st.chains) h.set("chains", "1"); if (st.sort) h.set("sort", st.sort); if (withPlace && st.p) h.set("p", st.p);
    return "#" + h.toString();
  }
  const listHash = () => hashOf(false);
  // filter changes replace the current history entry; opening a place pushes one, so Back closes the panel
  function saveHash(push = false) {
    const url = hashOf(true);
    if (push) history.pushState({ coeats: "place" }, "", url);
    else history.replaceState(st.p ? { coeats: "place" } : null, "", url);
    store.set("guide", st.g);
  }

  function locate() {
    if (!navigator.geolocation) { $("#ex-locmsg").textContent = "This browser can't share its location."; return; }
    $("#ex-locmsg").textContent = "Finding you…";
    navigator.geolocation.getCurrentPosition((pos) => {
      here = { la: pos.coords.latitude, lo: pos.coords.longitude };
      $("#ex-locmsg").textContent = "Sorted by distance from you. Your location stays in this browser.";
      st.sort = GUIDES[st.g].sorts.includes("nearest") ? "nearest" : st.sort;
      if (view === "map") centerOn(here);
      shown = 100; render();
    }, () => { $("#ex-locmsg").textContent = "Location is off for this site. Allow it in your browser settings to sort by distance."; },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
  }

  function setView(v) {
    view = v;
    document.querySelectorAll(".ex-view button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === v)));
    $("#ex-listwrap").hidden = v !== "list";
    $("#ex-mapwrap").hidden = v !== "map";
    render();
    if (v === "map" && phone.matches) $("#ex-mapwrap").scrollIntoView({ block: "nearest" });   // on phones the map starts below the fold
  }

  // the URL moved under us: Back/Forward (popstate) or a link to another #hash (hashchange). Both can fire for one step.
  function fromURL() {
    const before = listHash();
    readHash();
    if (listHash() !== before) { syncInputs(); shown = 100; render(); }
    const p = st.p && P.find((x) => x.id === st.p);
    const panel = $("#ex-panel");
    if (p) { if (panel.hidden || panel.dataset.id !== p.id) openPlace(p, false); }
    else if (!panel.hidden) closePlace(true);
  }

  function controls() {
    document.querySelectorAll(".ex-guides button").forEach((b) => b.onclick = () => { if (guideOk(b.dataset.g)) st.g = b.dataset.g; st.sort = ""; shown = 100; render(); });
    let t = null;
    $("#ex-q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { st.q = e.target.value; shown = 100; render(); }, 120); });
    $("#ex-sort").onchange = (e) => { st.sort = e.target.value; if (st.sort === "nearest" && !here) locate(); shown = 100; render(); };
    $("#ex-town").onchange = (e) => { st.town = e.target.value; shown = 100; render(); };
    $("#ex-cuisine").onchange = (e) => { st.cuisine = e.target.value; shown = 100; render(); };
    $("#ex-chains").onchange = (e) => { st.chains = e.target.checked; shown = 100; render(); };
    $("#ex-clear").onclick = () => { st.town = st.cuisine = ""; st.chains = false; syncInputs(); shown = 100; render(); };
    $("#ex-locate").onclick = locate;
    $("#ex-more").onclick = () => { shown += 200; renderList(order()); };
    document.querySelectorAll(".ex-view button").forEach((b) => b.onclick = () => setView(b.dataset.v));
    $("#ex-list").addEventListener("click", (e) => { const b = e.target.closest(".ex-row"); if (b && P[+b.dataset.i]) openPlace(P[+b.dataset.i]); });
    for (const ev of ["pointerover", "focusin"]) $("#ex-list").addEventListener(ev, () => loadDetail(), { once: true });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && st.p) closePlace(); });
    window.addEventListener("popstate", fromURL);
    window.addEventListener("hashchange", fromURL);
    phone.addEventListener?.("change", panelMode);
    mapEvents();
  }
  function syncInputs() {
    $("#ex-q").value = st.q; $("#ex-town").value = st.town; $("#ex-cuisine").value = st.cuisine; $("#ex-chains").checked = st.chains;
  }

  (async () => {
    $("#ex-loading").hidden = false;   // hidden in the HTML, so a browser without JavaScript shows only the <noscript> note
    readHash();
    try { await load(); } catch (e) { $("#ex-loading").textContent = "The restaurant list couldn't load. Refresh to try again."; return; }
    syncInputs(); controls();
    $("#ex-app").hidden = false;
    $("#ex-loading").hidden = true;
    render();
    const open = st.p && P.find((p) => p.id === st.p);
    if (open) { await loadDetail(); openPlace(open, false); }
  })();
})();
