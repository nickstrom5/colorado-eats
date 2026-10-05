"""Builds site/index.html (the private web leaderboard) from wi-eats/site/index.html, with Colorado's boards, sources and palette.
Every replacement is asserted, so a change in the Wisconsin page fails loudly instead of leaving Wisconsin text behind.
Usage: .venv/bin/python scripts/make-leaderboard.py"""
import os, re, sys
ROOT = os.path.join(os.path.dirname(__file__), "..")
src = open(os.path.join(ROOT, "..", "wi-eats", "site", "index.html")).read()
s = src
def R(a, b, n=1):
    global s
    c = s.count(a)
    if c != n:
        sys.exit(f"expected {n} of {a[:90]!r}, found {c}")
    s = s.replace(a, b)

# ---------------- head, palette, type
R('<title>Wisconsin Restaurant Leaderboard</title>', '<meta charset="utf-8">\n<title>Colorado Restaurant Leaderboard</title>')
R('<meta name="description" content="Every restaurant in Wisconsin, ranked on ratings, popularity, fish fry, supper clubs, custard, value and estimated sales.">',
  '<meta name="description" content="Every restaurant in Colorado, ranked on ratings, popularity, honors, green chile, brewpubs, value, estimated sales and official inspection results.">')
R('family=Saira+Extra+Condensed:wght@600;700;800;900&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400', 'family=Barlow+Condensed:wght@600;700;800&family=Barlow:ital,wght@0,400;0,500;0,600;0,700;1,400')
R('''  /* Packers: green #203731, gold #FFB612, white. Light-only by design; gold is a fill with green text on it, never text on white. */
  color-scheme:light;
  --bg:#FFFFFF; --surface:#FFFFFF; --surface-2:#F1F5F2; --surface-3:#E1EAE4;
  --ink:#14241D; --ink-2:#2E4238; --muted:#53665B; --rule:#DAE3DD; --rule-2:#B6C6BC;
  --green:#203731; --green-2:#2D5242; --gold:#FFB612; --gold-soft:#FFE7A8; --on-gold:#203731;
  --map-fill:#EEF3EF; --map-line:#C2D1C7; --dot-edge:rgba(20,36,29,.35);
  --seq1:#CFE2D5; --seq2:#9CC4A9; --seq3:#5F9A74; --seq4:#326B4B; --seq5:#203731;
  --scrim:rgba(20,36,29,.38);
  --shadow:0 1px 2px rgba(20,36,29,.06),0 8px 28px rgba(20,36,29,.10);
  --display:"Saira Extra Condensed","Arial Narrow","Roboto Condensed",sans-serif;
  --body:"Source Sans 3",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;''',
'''  /* Layout: sticky leaderboard tabs over a filter rail + ranked list; one Colorado element, a Front Range ridgeline under the header.
     Colorado flag: blue #002868, red #BF0A30, gold #FFD700 (1.4:1 on white, so gold is only ever a fill under blue text), white.
     Light-only by design, like the Chicago and Wisconsin leaderboards: every color is set explicitly below. */
  color-scheme:light;
  --bg:#FFFFFF; --surface:#FFFFFF; --surface-2:#F1F4F9; --surface-3:#E0E6F0;
  --ink:#0F1B33; --ink-2:#2A3A5A; --muted:#55627A; --rule:#DCE2EC; --rule-2:#B5C0D3;
  --green:#002868; --green-2:#1C3F86; --gold:#FFD700; --gold-soft:#FFF1A6; --on-gold:#002868; --red:#BF0A30;
  --map-fill:#F0F3F8; --map-line:#C6D0E0; --dot-edge:rgba(15,27,51,.35);
  --seq1:#CFDAEE; --seq2:#97AEDA; --seq3:#5576B8; --seq4:#2A4C92; --seq5:#002868;
  --scrim:rgba(15,27,51,.38);
  --shadow:0 1px 2px rgba(15,27,51,.06),0 8px 28px rgba(15,27,51,.10);
  --display:"Barlow Condensed","Arial Narrow","Roboto Condensed",sans-serif;
  --body:"Barlow",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;''')
R('body{margin:0;background:var(--bg);', 'html,body{background:var(--bg)}\nbody{margin:0;background:var(--bg);')
R('.hmid{padding:22px 16px 18px;border-bottom:4px solid var(--gold)}', '.hmid{padding:22px 16px 10px}\n.ridge{display:block;width:100%;height:26px;margin-top:-1px}\n.ridge .r1{fill:var(--green)} .ridge .r2{fill:var(--gold)} .ridge .r3{fill:var(--red)}')
R('.tab.wi{border-color:#D9A21A;background:#FFF9EA}', '.tab.wi{border-color:#C9A800;background:#FFFBE0}')
R('.chips.wi .chip[aria-pressed="false"]{background:#FFF9EA;border-color:#D9A21A}', '.chips.wi .chip[aria-pressed="false"]{background:#FFFBE0;border-color:#C9A800}')
R('.badge.sc{background:var(--gold-soft);color:var(--on-gold)}', '.badge.sc{background:var(--gold-soft);color:var(--on-gold)}\n.badge.mi{background:var(--red);color:#fff}\n.res{display:inline-block;font:700 11.5px/1.5 var(--body);letter-spacing:.04em;text-transform:uppercase;padding:1px 7px;border-radius:5px;white-space:nowrap}\n.res-0{background:#DDEFE3;color:#0E5A2B} .res-1{background:#FFE9C2;color:#6B3A00} .res-2{background:#F9D5DB;color:#7A0019}')
R('.fhint{font-size:12.5px;color:#8A4B00;margin:0}', '.fhint{font-size:12.5px;color:#8A1A2E;margin:0}')
R('#map{display:block;width:100%;max-width:min(760px,max(240px,calc((100dvh - var(--stickyH) - 120px) * 0.95)));margin:0 auto;aspect-ratio:0.95;touch-action:manipulation}',
  '#map{display:block;width:100%;max-width:min(980px,max(260px,calc((100dvh - var(--stickyH) - 120px) * 1.36)));margin:0 auto;aspect-ratio:1.36;touch-action:manipulation}')
R('@media (max-height:500px){#map{max-width:max(160px,calc((100dvh - var(--stickyH) - 70px) * 0.95))}}', '@media (max-height:500px){#map{max-width:max(160px,calc((100dvh - var(--stickyH) - 70px) * 1.36))}}')

# ---------------- header and filters
RIDGE = ('<svg class="ridge" viewBox="0 0 1200 26" preserveAspectRatio="none" aria-hidden="true">'
         '<path class="r2" d="M0 26V20L60 17L110 19L170 12L210 15L260 8L300 13L345 6L380 11L430 4L470 10L520 7L560 13L610 9L650 14L700 6L745 12L790 9L840 15L890 10L930 14L980 8L1030 13L1080 11L1130 16L1200 13V26Z"/>'
         '<path class="r1" d="M0 26V23L60 21L110 22L170 16L210 18L260 12L300 16L345 10L380 14L430 8L470 13L520 11L560 16L610 13L650 17L700 10L745 15L790 13L840 18L890 14L930 17L980 12L1030 16L1080 15L1130 19L1200 17V26Z"/>'
         '<rect class="r3" x="0" y="24" width="1200" height="2"/></svg>')
R('''    <p class="kicker" id="kicker">Wisconsin · map listings as of Sep 2026</p>
    <h1 id="h1">Every Wisconsin restaurant, <span class="count">ranked</span></h1>
    <p class="lede" id="lede">Supper clubs, taverns, custard stands, Friday fish fries and the places in between, from Superior to Kenosha. Each one is ranked on ratings, popularity, value and estimated sales, with Wisconsin's own boards for fish fry, supper clubs, custard and cheese curds. Flip any leaderboard to see the bottom.</p>
  </div></div>''',
'''    <p class="kicker" id="kicker">Colorado · map listings as of Sep 2026</p>
    <h1 id="h1">Every Colorado restaurant, <span class="count">ranked</span></h1>
    <p class="lede" id="lede">Green chile joints, brewpubs, ski-town dining rooms, MICHELIN stars and the places in between, from Julesburg to Cortez. Each one is ranked on ratings, popularity, value and estimated sales, with Colorado boards for green chile, brewpubs, ski towns and the oldest places, and Boulder County's official inspection results. Flip any leaderboard to see the bottom.</p>
  </div></div>''' + RIDGE)
R('<select id="city"><option value="">All of Wisconsin</option></select>', '<select id="city"><option value="">All of Colorado</option></select>')
R('<span class="flabel" id="l-tags">Wisconsin classics</span>', '<span class="flabel" id="l-tags">Colorado guides</span>')
R('<label class="toggle"><input type="checkbox" id="confirmed"> Only confirmed places (on a Milwaukee or Dane County license list, or in two sources)</label>',
  '<label class="toggle"><input type="checkbox" id="confirmed"> Only confirmed places (on a Denver license, a state liquor license or a Boulder County inspection record, or in two sources)</label>')
R('<p class="wnote">Each ingredient is a 0–100 percentile across Wisconsin.', '<p class="wnote">Each ingredient is a 0–100 percentile across Colorado.')
R('WI Score recipe: <span id="wname">', 'CO Score recipe: <span id="wname">')
R('placeholder="Search name, town, street, zip, “fish fry”…"', 'placeholder="Search name, town, street, zip, “green chile”…"')

# ---------------- constants
R('const TAGS = [["supper","Supper clubs",1],["fishfry","Fish fry",2],["custard","Frozen custard",8],["curds","Cheese curds",4]];',
  'const TAGS = [["greenchile","Green chile",1],["brewpub","Brewpubs",2],["game","Game & steak",4],["skitown","Ski towns",8],["oldest","Oldest places",16]];')
R('const JUR = ["", "City of Milwaukee", "Public Health Madison & Dane County"];', 'const JUR = ["", "Denver business license", "Boulder County inspection record", "Colorado liquor license"];')
R('research:"our verified list, placed with its Google listing"', 'research:"our hand-checked list, placed on its street address"')
R('try { S = sanitize(JSON.parse(localStorage.getItem("wi-eats") || "null")); }', 'try { S = sanitize(JSON.parse(localStorage.getItem("co-eats") || "null")); }')
R('localStorage.setItem("wi-eats", JSON.stringify(rest));', 'localStorage.setItem("co-eats", JSON.stringify(rest));')
R('let D = [], META = {}, SHAPES = null, WI_BOUNDS = null,', 'let D = [], META = {}, SHAPES = null, WI_BOUNDS = null, RESN = ["Pass", "Re-Inspection Required", "Closure"],')

# ---------------- boards
a = s.index('const sigShow = '); b = s.index('const board = () =>')
BOARDS = r'''const ratedShow = r => [stars(r.rating), revs(r)+(r.reviews === 1 ? " review" : " reviews")+" ('21)"];
const resPill = r => `<span class="res res-${r.in_r}">${esc(RESN[r.in_r])}</span>`;
const MI_TXT = ["", "MICHELIN Recommended", "Bib Gourmand", "1 MICHELIN Star", "2 MICHELIN Stars", "3 MICHELIN Stars"];
const B = [
  {id:"overall", tab:"CO Score", top:"Top CO Score", bottom:"Lowest CO Score", metric:"CO Score", val:r=>r.score,
   sub:()=>"A blend of rating, popularity, value and estimated profit, weighted by the CO Score recipe in the filters. Places missing some data are pulled toward 40, a little below the middle.",
   show:r=>[Math.round(r.score), "CO Score"]},
  {id:"rating", tab:"Rating", top:"Highest rated", bottom:"Lowest rated", metric:"rating", val:r=>r.bayes, need:(r,d)=>r.reviews >= (d==="top"?15:40),
   sub:"Google star rating as of the Sep 2021 snapshot, adjusted for review count so a 5.0 from three friends doesn't beat a 4.8 from 3,000 strangers.",
   show:ratedShow, dup:"rating"},
  {id:"popular", tab:"Popularity", top:"Most popular", bottom:"Least popular", metric:"reviews", val:r=>r.reviews, need:r=>r.reviews!=null,
   sub:"Total Google reviews as of Sep 2021: the best public stand-in for how many people walk through the door. Places opened since aren't in the snapshot, and the snapshot caps counts at 9,998 (shown as 9,998+).",
   show:r=>[revs(r), (r.reviews === 1 ? "review" : "reviews")+" ('21) · "+stars(r.rating)], dup:"rating"},
  {id:"gems", tab:"Hidden gems", top:"Hidden gems", bottom:"Popular but panned", metric:"rating", val:r=>r.gem, need:(r,d)=> d==="top" ? (r.reviews>=20 && r.reviews<=250 && r.chain_n<5) : r.reviews>=600,
   sub:"Top: independents with 20–250 reviews and great ratings. Bottom: places with 600+ reviews and the lowest ratings. Both from the Sep 2021 snapshot.",
   show:ratedShow, dup:"rating"},
  {id:"greenchile", wi:true, tab:"Green chile", top:"Green chile, highest rated", bottom:"Green chile, lowest rated", metric:"rating", val:r=>r.bayes, need:r=>(r.tags & 1) && r.rating!=null,
   sub:"Places we hand-checked in Sep–Oct 2026 for Colorado green chile on the current menu: smothered and breakfast burritos, chile by the bowl, Pueblo sloppers. Each has a 2025–26 source. Ranked by Google rating (Sep 2021), adjusted for review count.",
   show:ratedShow, dup:"rating"},
  {id:"brewpub", wi:true, tab:"Brewpubs", top:"Brewpubs, highest rated", bottom:"Brewpubs, lowest rated", metric:"rating", val:r=>r.bayes, need:r=>(r.tags & 2) && r.rating!=null,
   sub:"Places holding an active Colorado Brew Pub or Distillery Pub liquor license (state Liquor Enforcement Division), which lets them brew or distill and serve on site. Ranked by Google rating (Sep 2021), adjusted for review count.",
   show:ratedShow, dup:"rating"},
  {id:"skitown", wi:true, tab:"Ski towns", top:"Ski towns, highest rated", bottom:"Ski towns, lowest rated", metric:"rating", val:r=>r.bayes, need:(r,d)=>(r.tags & 8) && r.reviews >= (d==="top"?15:40),
   sub:"Every place in Aspen, Snowmass, Vail, Avon, Beaver Creek, Breckenridge, Frisco, Keystone, Steamboat, Telluride, Crested Butte, Winter Park and Durango. Mountain-town places close for mud season in spring and fall; that doesn't mean closed. Ranked by Google rating (Sep 2021), adjusted for review count.",
   show:ratedShow, dup:"rating"},
  {id:"iconic", tab:"Iconic", top:"Most iconic", bottom:"Least iconic", metric:"iconic points", val:r=>r.s_icon, need:r=>r.s_icon!=null,
   sub:"Only places with an honor or a long, verified history: MICHELIN Guide Colorado 2026 (stars, Bib Gourmand, Recommended), James Beard awards and nominations 2023–26, America's Classics, and places we verified open at the same address since 1960 or earlier. Points for honors, years open and how many people know it.",
   show:r=>[Math.round(r.s_icon), "iconic pts" + (r.founded ? " · since " + r.founded : "")]},
  {id:"value", tab:"Value", top:"Best bang for buck", bottom:"Worst value", metric:"value score", val:r=>r.value_raw, need:r=>r.rating!=null,
   sub:"Rating (2021) relative to price level: a 4.7 at $ beats a 4.7 at $$$.",
   show:r=>[stars(r.rating)+" "+dollars(r.price)+(r.price_est?ESTTAG:""), "value "+Math.round(r.i_value)+" · rating '21"], dup:"rating"},
  {id:"price", tab:"Price", top:"Priciest", bottom:"Cheapest", metric:"price", val:r=>r.spend,
   sub:"Google price level (filled in from the chain or cuisine when missing, and marked est.) with typical spend per person. Within a price level, ties are ordered by CO Score.",
   show:r=>[dollars(r.price)+(r.price_est?ESTTAG:""), "~$"+r.spend+"/person "+ESTTAG]},
  {id:"sales", tab:"Sales", top:"Highest sales", bottom:"Lowest sales", metric:"sales", val:r=>r.rev, need:(r,d)=>r.rev!=null && (d==="top" || r.rev_src!=="model-low"), est:true,
   sub:d=>`Estimated yearly sales. Locations of chains with a published average (${META.model?.n_chains ?? "80+"} brands) use that average scaled by how busy the location is; independents use a model.` + (d==="bottom" ? " This end leaves out places with no review data (their figures are rough placeholders). The model never goes below $100K a year, so the very bottom is a tie, ordered by CO Score." : ""),
   show:r=>[money(r.rev), "sales/yr · " + src(r)], dup:"sales"},
  {id:"profit", tab:"Profit", top:"Most profitable", bottom:"Least profitable", metric:"profit", val:r=>r.profit, need:(r,d)=>r.profit!=null && (d==="top" || r.rev_src!=="model-low"), est:true,
   sub:d=>"Estimated yearly pre-tax profit: estimated sales × a typical margin for the segment, nudged by how well-loved the place is." + (d==="bottom" ? " This end leaves out places with no review data (their figures are rough placeholders). The sales model never goes below $100K a year, so the very bottom is mostly places at that floor, ordered by margin and then CO Score." : ""),
   show:r=>[money(r.profit), "profit/yr "+ESTTAG]},
  {id:"food", tab:"Food cost", top:"Biggest food bill", bottom:"Smallest food bill", metric:"food bill", val:r=>r.rev*r.food_cost/100, need:(r,d)=>r.rev!=null && (d==="top" || r.rev_src!=="model-low"), est:true,
   sub:d=>"Estimated yearly food purchases: estimated sales × the typical food-cost share for the cuisine (steak ~38%, pizza ~26%)." + (d==="bottom" ? " This end leaves out places with no review data. The sales model never goes below $100K a year, so the very bottom is mostly places at that floor." : ""),
   show:r=>[money(r.rev*r.food_cost/100), r.food_cost+"% food cost "+ESTTAG]},
  {id:"clean", tab:"Inspections", top:"Fewest risk points at latest inspection", bottom:"Most risk points at latest inspection", metric:"risk points", val:r=>r.in_r == null ? null : -r.in_p, need:r=>r.in_r!=null,
   tie:(a,b,d)=> d==="top" ? (a.in_r-b.in_r) : (b.in_r-a.in_r),
   sub:d=>`Boulder County only: it's the one part of Colorado that publishes inspection results in bulk. Each place shows its official result at its latest inspection (Colorado's rating: Pass, Re-Inspection Required or Closure) and the risk points behind it. Lower points are better: Pass is 0–49, Re-Inspection Required 50–109, Closure 110+, and a Closure can also follow an imminent health hazard at any score. Inspections from Sep 2025 through ${META.inspections_through || "Jul 2026"}.` + (d==="bottom" ? " One inspection is a snapshot of one day, and most places here passed." : ""),
   show:r=>[`${resPill(r)}`, `${plural(r.in_p, "risk point", "risk points")} · ${esc(r.in_d)}`], dup:"grade"},
];'''
s = s[:a] + BOARDS + "\n" + s[b:]

# ---------------- rows, badges, stats
R('''  if (r.hon & 1) h += `<span class="badge jbf">America's Classic</span>`;''',
  '''  if (r.mi) h += `<span class="badge mi">${MI_TXT[r.mi]}</span>`;
  if (r.hon & 1) h += `<span class="badge jbf">America's Classic</span>`;''')
R('''  if ((r.hon & 16) && !(r.hon & 7)) h += `<span class="badge icon">Icon</span>`;
  if ((r.tags & 1) && !/supper ?club/i.test(r.name)) h += `<span class="badge sc">Supper club</span>`;''',
  '''  if ((r.hon & 16) && r.founded) h += `<span class="badge icon">Since ${esc(r.founded)}</span>`;
  if (r.tags & 1) h += `<span class="badge sc">Green chile</span>`;
  if (r.tags & 2) h += `<span class="badge sc">Brewpub</span>`;''')
R('''  if (r.ff_n >= 3 && b.id !== "fishfry") bits.push(`<span>${r.ff_n} <i>fish fry mentions</i></span>`);
  if (r.grade) bits.push(`<span class="${dup("grade")}" title="Our grade from Dane County inspection results, not an official grade"><span class="grade sm g-${r.grade}">${r.grade}</span> <i>our inspection grade</i></span>`);''',
  '''  if (r.in_r != null) bits.push(`<span class="${dup("grade")}" title="Official result at the latest Boulder County inspection">${resPill(r)} <i>${esc(r.addr || "")} · inspected ${esc(r.in_d)}</i></span>`);''')
R('''  if (S.board !== "overall" && r.score != null) bits.push(`<span>${Math.round(r.score)} <i>WI Score</i></span>`);''',
  '''  if (S.board !== "overall" && r.score != null) bits.push(`<span>${Math.round(r.score)} <i>CO Score</i></span>`);''')
R('''const TAG_PH = [["friday fish fry","fishfry"],["fish fries","fishfry"],["fish fry","fishfry"],["fishfry","fishfry"],["supper clubs","supper"],["supper club","supper"],
  ["supperclub","supper"],["frozen custard","custard"],["custard","custard"],["cheese curds","curds"],["cheese curd","curds"],["curds","curds"]].map(([p, t]) => [norm(p), t]);''',
  '''const TAG_PH = [["green chile","greenchile"],["green chili","greenchile"],["green chilli","greenchile"],["sloppers","greenchile"],["slopper","greenchile"],
  ["smothered burrito","greenchile"],["brewpubs","brewpub"],["brew pubs","brewpub"],["brewpub","brewpub"],["brew pub","brewpub"],["ski towns","skitown"],["ski town","skitown"],
  ["oldest","oldest"],["game","game"]].map(([p, t]) => [norm(p), t]);''')
R('''  // "fish fry", "supper club", "custard", "cheese curds" mean the Wisconsin tags, not words in a name''', '''  // "green chile", "brewpub", "ski town" mean the Colorado guides, not words in a name''')
R('''  // "fond du lac fish fry" means the town; "green bay rd" or "madison st" is a street, not the town''', '''  // "pueblo green chile" means the town; "colorado blvd" or "lincoln st" is a street, not the town''')
R('''  // a town named in the search ("fond du lac fish fry") narrows to it; a place NAMED that way still counts''', '''  // a town named in the search ("pueblo green chile") narrows to it; a place NAMED that way still counts''')
R('''    return `No places match “${esc(S.q.trim())}” in Wisconsin.''', '''    return `No places match “${esc(S.q.trim())}” in Colorado.''')
R('''  const setPh = () => { $("#q").placeholder = innerWidth < 400 ? "Search name, town, street…" : "Search name, town, street, zip, “fish fry”…"; };''', '''  const setPh = () => { $("#q").placeholder = innerWidth < 400 ? "Search name, town, street…" : "Search name, town, street, zip, “green chile”…"; };''')
R('''  if (S.board === "overall" && !weightTotal) return `The WI Score recipe is empty.''', '''  if (S.board === "overall" && !weightTotal) return `The CO Score recipe is empty.''')
R('''  if (pool.length && board().id === "clean") return `${plural(pool.length, "place matches", "places match")} ${what}, but inspection results are only published for Dane County (Madison and its suburbs). ${f.length ? undo + " to see them." : ""}`;''',
  '''  if (pool.length && board().id === "clean") return `${plural(pool.length, "place matches", "places match")} ${what}, but inspection results are only published in bulk for Boulder County (Boulder, Longmont, Lafayette, Louisville and nearby). ${f.length ? undo + " to see them." : ""}`;''')
R('''"All of Wisconsin"}</option>`''', '''"All of Colorado"}</option>`''')
R('''$("#cityhint").textContent = `No Wisconsin town matches''', '''$("#cityhint").textContent = `No Colorado town matches''')
R('''    else if (cityFromBox && S.city) { S.city = ""; cityFromBox = false; rerender(); }   // "Wausauk" is no longer Wausau''', '''    else if (cityFromBox && S.city) { S.city = ""; cityFromBox = false; rerender(); }   // "Durangoo" is no longer Durango''')
R('''    const hit = CITY_N.get(v) || (CITIES.find(([c]) => (" " + norm(c)).includes(" " + v)) || [])[0];   // CITIES is biggest first: "bay" -> Green Bay''',
  '''    const hit = CITY_N.get(v) || (CITIES.find(([c]) => (" " + norm(c)).includes(" " + v)) || [])[0];   // CITIES is biggest first: "springs" -> Colorado Springs''')
R('''const cols = [["name","City or town"],["n","Places","r"],["score","Avg WI Score","r"]''', '''const cols = [["name","City or town"],["n","Places","r"],["score","Avg CO Score","r"]''')

# ---------------- map
R('shapesPending = fetchJSON("wi_shapes.json").then(j => {', 'shapesPending = fetchJSON("co_shapes.json").then(j => {')
R("WI_BOUNDS = a[0] < a[1] ? a : [-92.9, -86.8, 42.49, 47.08];", "WI_BOUNDS = a[0] < a[1] ? a : [-109.06, -102.04, 36.99, 41.0];")
R("const w = c.clientWidth || 600, h = Math.round(w / 0.95);", "const w = c.clientWidth || 600, h = Math.round(w / 1.36);")
R("  ctx.save(); land(); ctx.clip(\"evenodd\");   // county lines stop at the shore", "  ctx.save(); land(); ctx.clip(\"evenodd\");   // county lines stop at the state line")
R('''  $("#live").textContent = pool.length === 1 ? `Only one place matches your filters: ${r.name}.` : `Random pick: ${r.name}, ${r.city || "Wisconsin"}.`;''',
  '''  $("#live").textContent = pool.length === 1 ? `Only one place matches your filters: ${r.name}.` : `Random pick: ${r.name}, ${r.city || "Colorado"}.`;''')

# ---------------- drawer
a = s.index('function calibNote(r) {'); b = s.index('function sigCard(n, rt, what)')
s = s[:a] + r'''function calibNote(r) {
  const c = (META.calibration || {}).areas || {}, g = k => [c["Denver"]?.groups?.[k], c["Boulder County"]?.groups?.[k]].filter(Boolean);
  const range = k => { const v = g(k).map(x => x.official); if (!v.length) return null; const lo = Math.min(...v), hi = Math.max(...v); return lo === hi ? pctTxt(lo) : `${pctTxt(lo)}–${pctTxt(hi)}`; };
  const feed = r.src === "AllThePlaces" || r.src === "DAC", checked = r.hc ? " It's also on our hand-checked list, confirmed open with a 2025–26 source." : "";
  if (r.src === "research") return "This place isn't in the map listings as a place to eat (it's listed as a hotel, lodge or ski area, or not at all). It's on our hand-checked list, confirmed open with a 2025–26 source, and placed on its street address.";
  if (r.tier === 2) return (r.src === "official" ? `This place comes straight from the ${esc(JUR[r.jur])} list. The map listings we use didn't have it, so its location comes from the record's address.` : `Matched to an active ${esc(JUR[r.jur])}, so it's confirmed as a licensed business.`) + checked;
  const via = feed ? (r.tier === 1 ? "brand feed + Google 2021" : "brand feed only") : r.src === "meta" ? (r.tier === 1 ? "Meta + open in Google 2021" : "Meta only") : null;
  const rate = via ? range(via) : null, kind = feed ? "chain store-list listings" : "listings";
  if (!via) return "Kept because it's on our hand-checked list, confirmed open with a 2025–26 source, even though its only map listing comes from a source that's usually unreliable.";
  if (r.tier === 1) return `Found in two independent sources: a map listing and Google's 2021 data. Checked against Denver's licenses and Boulder County's inspected facilities, ${kind} like this matched a licensed business ${rate || "most"} of the time.` + checked;
  return `Found in one map source only. Checked against Denver's licenses and Boulder County's inspected facilities, single-source ${kind} like this matched a licensed business ${rate || "less than half"} of the time, so this one may be closed or misfiled.` + checked;
}
''' + s[b:]
R('''  const gq = encodeURIComponent(`${r.name} ${r.addr || ""} ${r.city || ""} WI`);''', '''  const gq = encodeURIComponent(`${r.name} ${r.addr || ""} ${r.city || ""} CO`);''')
R('''  const heroLbl = r.score == null ? (weightTotal ? "No WI Score: not enough data" : "WI Score recipe is empty")
    : ri >= 0 ? `WI Score · #${fmtN(ri+1)} of ${fmtN(L.length)} with your filters (ignoring search)` : "WI Score · outside your current filters";''',
  '''  const heroLbl = r.score == null ? (weightTotal ? "No CO Score: not enough data" : "CO Score recipe is empty")
    : ri >= 0 ? `CO Score · #${fmtN(ri+1)} of ${fmtN(L.length)} with your filters (ignoring search)` : "CO Score · outside your current filters";''')
R('''  const cats = `<div class="dsec"><h3>Category scores (percentile vs. all Wisconsin places)</h3>''', '''  const cats = `<div class="dsec"><h3>Category scores (percentile vs. all Colorado places)</h3>''')
a = s.index('  const sig = [sigCard('); b = s.index('  const moneyNote = {')
s = s[:a] + s[b:]
R('''This location isn't in the 2021 review snapshot, so this uses 85% of the chain's published U.S. average sales per location." : "Based on the chain's published U.S. average sales per location, scaled up or down by how busy this location was (2021 reviews) compared with the chain's other Wisconsin locations.",''',
  '''This location isn't in the 2021 review snapshot, so this uses 85% of the chain's published U.S. average sales per location." : "Based on the chain's published U.S. average sales per location, scaled up or down by how busy this location was (2021 reviews) compared with the chain's other Colorado locations.",''')
R('''scaled by 2021 review volume relative to similar Wisconsin places''', '''scaled by 2021 review volume relative to similar Colorado places''')
a = s.index('  const honorsList = ['); b = s.index('  $("#drawer").innerHTML = `${dhead(')
s = s[:a] + r'''  const honorsList = [...(r.mi ? [MI_TXT[r.mi] + " · MICHELIN Guide Colorado 2026"] : []), ...(x.jbf ? x.jbf.split(/;\s(?![^()]*\))/).map(v => "James Beard: " + v) : [])];
  const tagsTxt = TAGS.filter(([, , bit]) => r.tags & bit).map(([, l]) => l);
  const facts = (x.note || x.dishes || x.founded_note || x.seasonal) ? `<div class="dsec"><h3>Hand-checked facts</h3>${x.note ? `<p style="margin:0 0 8px;color:var(--ink-2);font-size:14px">${esc(x.note)}</p>` : ""}
      ${kv([x.dishes ? ["On the menu", esc(x.dishes.split("; ").join(", "))] : null, x.founded ? ["Open here since", esc(x.founded)] : null, x.seasonal ? ["Season", esc(x.seasonal)] : null])}
      ${x.founded_note ? `<p class="note">${esc(x.founded_note)}</p>` : ""}${x.web ? `<p class="note">Source: <a href="${esc(x.web)}" target="_blank" rel="noopener">${esc(x.web.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, ""))}</a>, checked Sep–Oct 2026.</p>` : ""}</div>` : "";
  const lic = (x.lic || []).map(l => [esc(l.src), esc(l.type || "") + " · " + esc(l.id) + (l.exp ? ` · expires ${esc(l.exp)}` : "")]);
  const insp = r.in_r != null ? `<div class="dsec"><h3>Health inspections · Boulder County Public Health</h3>
      <div class="hero" style="margin:0 0 10px">${resPill(r)}<span class="lbl">Official result at the latest inspection, ${esc(r.in_d)} · ${plural(r.in_p, "risk point", "risk points")}</span></div>
      ${x.insp ? `<ul class="lines">${x.insp.map(([d, res, p, t]) => `<li>${esc(d)} · ${esc(t)} · ${esc(res === "Reinspection Required" ? "Re-Inspection Required" : res)} · ${plural(p, "point", "points")}</li>`).join("")}</ul>` : (DETAIL ? "" : `<p class="note">${detailFailed ? "Couldn't load the inspection list. Check your connection and reopen this place." : "Loading the inspection list…"}</p>`)}
      ${x.items && x.items.length ? `<p class="note" style="margin-top:10px">Cited at the latest inspection: ${esc(x.items.slice(0, 8).join("; "))}${x.items.length > 8 ? "…" : ""}</p>` : ""}
      <p class="note">Colorado's inspection rating: Pass 0–49 risk points, Re-Inspection Required 50–109, Closure 110+ (lower is better); a Closure can also follow an imminent health hazard at any score. Source: Boulder County Public Health on data.colorado.gov, inspections through ${esc(META.inspections_through || "")}, published ${esc(META.inspections_published || "")}.</p></div>` : "";
''' + s[b:]
R('''  $("#drawer").innerHTML = `${dhead(esc(r.city || "Wisconsin"), random)}''', '''  $("#drawer").innerHTML = `${dhead(esc(r.city || "Colorado"), random)}''')
R('''    <div class="addr">${r.addr ? esc(r.addr) + ", " : ""}${esc(r.city || "Wisconsin")}''', '''    <div class="addr">${r.addr ? esc(r.addr) + ", " : ""}${esc(r.city || "Colorado")}''')
R('''    ${sig ? `<div class="dsec"><h3>Wisconsin classics · from Google reviews through Sep 2021</h3><div class="wisig">${sig}</div><p class="note">Average star rating of just the reviews that mention it. Reviews rate the whole visit, so read these as a lean, not a verdict.</p></div>` : ""}
    ${(honorsList.length || x.icon || x.founded) ? `<div class="dsec"><h3>Honors &amp; history</h3>${x.icon?`<p style="margin:0 0 8px;color:var(--ink-2);font-size:14px">${esc(x.icon)}</p>`:""}${honorsList.length?`<ul class="lines">${honorsList.map(v=>`<li>${esc(v)}</li>`).join("")}</ul>`:""}${x.founded ? `<p class="note">Open since ${esc(x.founded)} (verified).</p>` : ""}</div>`
      : (r.hon && !DETAIL ? `<div class="dsec"><h3>Honors &amp; history</h3><p class="note">${detailFailed ? "Couldn't load the honors. Check your connection and reopen this place." : "Loading…"}</p></div>` : "")}
    ${insp}''',
  '''    ${honorsList.length ? `<div class="dsec"><h3>Honors</h3><ul class="lines">${honorsList.map(v=>`<li>${esc(v)}</li>`).join("")}</ul><p class="note">MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation awards are the Foundation's. Honors are facts, not ratings.</p></div>`
      : ((r.hon & 15) && !DETAIL ? `<div class="dsec"><h3>Honors</h3><p class="note">${detailFailed ? "Couldn't load the honors. Check your connection and reopen this place." : "Loading…"}</p></div>` : "")}
    ${facts}
    ${insp}''')
R('''      x.lic ? ["License number", esc(x.lic.replace(/^(MKE|PHMDC)-/, ""))] : null,
      tagsTxt.length ? ["Wisconsin tags", esc(tagsTxt.join(", "))] : null,
      ["Listed as a bar or tavern", r.bar ? "Yes" : "No"], ["Locations in Wisconsin", r.chain_n >= 2 ? fmtN(r.chain_n) : "This one only"],''',
  '''      ...lic, r.liq ? ["Serves alcohol", "Yes · " + esc(META.liqt[r.liq]) + " license"] : ["Serves alcohol", "— (no on-premises liquor license matched)"],
      tagsTxt.length ? ["Colorado guides", esc(tagsTxt.join(", "))] : null,
      r.county ? ["County", esc(r.county)] : null,
      ["Listed as a bar or tavern", r.bar ? "Yes" : "No"], ["Locations in Colorado", r.chain_n >= 2 ? fmtN(r.chain_n) : "This one only"],''')
R('''  detailPending = fetchJSON("wi_detail.json").then(j => {''', '''  detailPending = fetchJSON("co_detail.json").then(j => {''')

# ---------------- method cards
a = s.index('function methodCards() {'); b = s.index('// ---------------- boot ----------------')
s = s[:a] + r'''function methodCards() {
  const m = META, c = (m.calibration || {}).areas || {};
  const dv = ["Foursquare only", "BrightQuery only", "Microsoft only", "Foursquare/BrightQuery/Microsoft + Google 2021"].flatMap(k => [c["Denver"]?.groups?.[k], c["Boulder County"]?.groups?.[k]]).filter(Boolean).map(g => g.official);
  const dropRange = dv.length ? `${Math.round(Math.min(...dv) * 100)}–${Math.round(Math.max(...dv) * 100)}%` : "a small share";
  const cols = [
    ["m", "Official records", [
      ["Boulder County inspections", `Boulder County Public Health's inspections (data.colorado.gov, public domain), the only bulk inspection results in Colorado. Each place shows the official result at its latest inspection: Colorado's rating of Pass (0–49 risk points), Re-Inspection Required (50–109) or Closure (110+, or an imminent health hazard), set by the state health department's Interpretive Memo 19-09 under C.R.S. 25-4-1607.7. We show the result as recorded and never compute a grade of our own. Inspections Sep 2025 through ${esc(m.inspections_through || "Jul 2026")}, published ${esc(m.inspections_published || "Aug 2026")}.`],
      ["Denver business licenses", `The City and County of Denver's open list of active business licenses (Retail Food, Combined and Liquor), updated daily. A listing that matches a license is marked confirmed, and licensed places that are plainly restaurants are added from the list. Denver's inspection results are search-only, so they aren't here.`],
      ["State liquor licenses", `The Colorado Department of Revenue's list of active liquor licenses (data.colorado.gov, public domain, monthly; ${esc(m.liquor_updated || "Sep 2026")}). On-premises licenses (Hotel & Restaurant, Tavern, Brew Pub, Beer & Wine and similar) confirm a place statewide and say it serves alcohol. No license matched means unknown, not "no".`],
      ["The rest of the state", "Every other county health department publishes inspections one search at a time (or not at all), and some of those sites block automated access, so we don't collect them. Outside Denver, Boulder County and the liquor list, places come from map listings."]]],
    ["s", "Map listings & 2021 snapshot", [
      ["Places statewide", `Overture Maps' open map listings (${esc(m.overture_release || "Sep 2026")} release, which merges Meta, Foursquare, chain store lists and other sources). We keep listings from Meta and from chains' own store lists, and drop Foursquare, BrightQuery and Microsoft listings: in Denver and Boulder County only ${dropRange} of those matched a licensed business. Anything Google already showed as closed in 2021 is dropped, unless an official record or our research confirms it.`],
      ["Ratings, reviews & price level", "Google Maps ratings from the UCSD Google Local research dataset, frozen in September 2021. Each Google listing is matched to one place at most, on a shared distinctive name word nearby. Places that opened later aren't in it, and the rating boards leave them out rather than guess."],
      ["Honors & guides", "Hand-checked in Sep–Oct 2026: the MICHELIN Guide Colorado 2026 selection (63 restaurants), James Beard awards and nominations 2023–26 and America's Classics, plus green chile spots, game and steakhouses, ski-town dining rooms and the oldest places, each with a 2025–26 source. Places our research found closed are removed."]]],
    ["e", "Estimated", [
      ["Sales & profit", `Chains use their published U.S. average sales per store (QSR 50, Technomic, company filings and franchise disclosures; ${m.model?.n_chains ?? "80+"} brands found here), scaled by how busy the location is. Independents start from a typical figure for their price level ($600K for $ up to $3.5M for $$$$) and scale with 2021 review volume relative to similar Colorado places, with an exponent of ${m.model?.b ?? 0.76} fit on published Chicago sales. Places without reviews get a rough placeholder. Profit = sales × a typical segment margin.`],
      ["Price, cuisine & food cost", "Missing price levels are filled in from the chain's or cuisine's usual Colorado level and marked est. Cuisine comes from the listing's category, the business name and Google categories, so a few will be off. Food cost is the typical share for that cuisine × estimated sales, a benchmark rather than the restaurant's own invoices."]]],
  ];
  $("#srcgrid").innerHTML = cols.map(([t, h, cards]) => `<div class="srccol"><span class="tag ${t}">${h}</span>${cards.map(([h,p]) => `<div class="src"><h3>${h}</h3><p>${p}</p></div>`).join("")}</div>`).join("");
  const G = [["Meta + open in Google 2021","Meta listing, open in Google's 2021 data","kept · two sources"],["Meta only","Meta listing only","kept · listing only"],
    ["brand feed + Google 2021","Chain store list + Google 2021","kept · two sources"],["brand feed only","Chain store list only","kept · listing only"],
    ["Foursquare/BrightQuery/Microsoft + Google 2021","Foursquare / BrightQuery / Microsoft + Google 2021","dropped"],["Foursquare only","Foursquare only","dropped"],
    ["BrightQuery only","BrightQuery only","dropped"],["Microsoft only","Microsoft only","dropped"],["Google 2021 says closed","Google showed it closed in 2021","dropped"]];
  const cell = (j, k) => { const g = c[j]?.groups?.[k]; return g ? `${Math.round(g.official * 100)}% <span style="color:var(--muted)">of ${fmtN(g.n)}</span>` : "—"; };
  const pc = (m.calibration || {}).per_county || {};
  const ctyRows = Object.entries(pc).sort((a, b) => b[1].listings - a[1].listings);
  const BULK = {"Boulder County": "Bulk (data.colorado.gov)"}, SEARCH = new Set(["Denver","El Paso County","Arapahoe County","Jefferson County","Adams County","Larimer County","Douglas County","Weld County","Pueblo County","Mesa County","Eagle County","Summit County","Broomfield","Pitkin County","Grand County","Clear Creek County","Moffat County","Ouray County","Park County","Logan County","Morgan County","Phillips County","Sedgwick County","Washington County","Yuma County"]);
  $("#calib").innerHTML = c["Denver"] ? `<div class="src" style="display:grid;gap:10px"><h3>How the map listings were checked</h3>
    <p>In Denver (which licenses every food business) and Boulder County (where every inspected facility is public), each map listing was checked against the official records: same business name nearby, or the same street address with a distinctive name word in common. The share that matched decides what's kept. Coverage runs the other way too: the open map listings held ${Math.round((c["Denver"].coverage||0)*100)}% of Denver's licensed food businesses and ${Math.round((c["Boulder County"].coverage||0)*100)}% of Boulder County's inspected restaurants; the rest were added from the records.</p>
    <div class="calib"><table><thead><tr><th scope="col">Kind of listing</th><th scope="col" class="r">Denver</th><th scope="col" class="r">Boulder County</th><th scope="col">Here</th></tr></thead><tbody>
    ${G.map(([k, l, what]) => `<tr><td>${esc(l)}</td><td class="r num">${cell("Denver", k)}</td><td class="r num">${cell("Boulder County", k)}</td><td>${what}</td></tr>`).join("")}</tbody></table></div>
    <p class="note">Matched = on an active Denver license, a Boulder County inspection record or a state liquor license. These are lower bounds: a real place under a different name on its license counts as a miss. Hand-checked places are kept whatever their source.</p></div>
    <div class="src" style="display:grid;gap:10px"><h3>Coverage by county</h3>
    <p>Every county has the statewide liquor list; only Boulder County has inspection results in bulk. “Liquor licensees found” is the share of each county's on-premises liquor licensees that the open map listings already held (the rest were added from the list).</p>
    <div class="calib" style="max-height:420px;overflow:auto"><table><thead><tr><th scope="col">County</th><th scope="col" class="r">Map listings</th><th scope="col" class="r">On-premises liquor licenses</th><th scope="col" class="r">Liquor licensees found</th><th scope="col">Inspection results</th></tr></thead><tbody>
    ${ctyRows.map(([n, v]) => `<tr><td>${esc(n)}</td><td class="r num">${fmtN(v.listings)}</td><td class="r num">${fmtN(v.liq_onprem_records || 0)}</td><td class="r num">${v.liq_found == null ? "—" : Math.round(v.liq_found * 100) + "%"}</td><td>${BULK[n] || (SEARCH.has(n) ? "Search-only portal" : "None found online")}</td></tr>`).join("")}</tbody></table></div></div>` : "";
}

''' + s[b:]

# ---------------- build
R('''  // Wisconsin signals: Bayes-shrink each place's average toward the statewide average for that dish (5 reviews' worth)
  for (const [key, n, r, out] of [["ff","ff_n","ff_r","ff"],["cc","cc_n","cc_r","cc"],["cs","cs_n","cs_r","cs"]]) {
    let sw = 0, sn = 0; for (const [i, nn, rr] of sp[key] || []) if (rr != null) { sw += nn * rr / 100; sn += nn; }
    const mu = sn ? sw / sn : 4.2;
    for (const [i, nn, rr] of sp[key] || []) { const o = rows[i]; if (!o) continue; o[n] = nn; o[r] = rr == null ? null : rr / 100; o[out] = rr == null ? null : (nn * rr / 100 + 5 * mu) / (nn + 5); }
  }
  for (const [i, nn] of sp.sc || []) if (rows[i]) rows[i].sc_n = nn;
  for (const [i, s, f] of sp.hon || []) if (rows[i]) { rows[i].s_icon = s / 10; rows[i].hon = f; }
  for (const [i, cl, g, ni, nr] of sp.insp || []) if (rows[i]) Object.assign(rows[i], {clean: cl, grade: g, n_insp: ni, n_reinsp: nr});''',
  '''  for (const [i, s, f, mi, gs] of sp.hon || []) if (rows[i]) { rows[i].s_icon = s / 10; rows[i].hon = f; rows[i].mi = mi; rows[i].gs = gs; }
  for (const [i, res, p, d, n, rr, cl] of sp.insp || []) if (rows[i]) Object.assign(rows[i], {in_r: res, in_p: p, in_d: d, in_n: n, in_rr: rr, in_cl: cl});''')
R('''    o.src = (m.srcs || [])[C.src[i]] || null;''', '''    o.src = (m.srcs || [])[C.src[i]] || null; o.liq = C.liq[i] || 0; o.hc = C.hc[i] || 0; o.county = C.county[i] == null ? null : m.counties[C.county[i]];''')
R('''    o._s = " " + normRaw([o.name, o.city, o.zip, o.cuisine, o.brand].join(" ")) + " " + norm(o.addr) + " ";''', '''    o._s = " " + normRaw([o.name, o.city, o.zip, o.cuisine, o.brand, o.county].join(" ")) + " " + norm(o.addr) + " ";''')
R('''  CITY_N = new Map();   // "st germain", "saint germain" and "St. Germain" are one town''', '''  CITY_N = new Map();   // "canon city", "cañon city" and "Cañon City" are one town''')
R('''             "fish", "fry", "custard", "curds", "cheese", "supper", "club", "brats", "tavern", "tap", "brewery", "kringle"]));''',
  '''             "green", "chile", "chili", "slopper", "sloppers", "smothered", "burrito", "burritos", "brewpub", "brewpubs", "tavern", "tap", "brewery", "bison", "elk", "steak", "ski"]));''')
R('''  $("#h1").innerHTML = `<span class="count num">${fmtN(n)}</span> Wisconsin restaurants, ranked`;''', '''  $("#h1").innerHTML = `<span class="count num">${fmtN(n)}</span> Colorado restaurants, ranked`;''')
R('''  fetchJSON("wisconsin.json").then(j => {''', '''  fetchJSON("colorado.json").then(j => {''')
for word in ("Wisconsin", "Milwaukee", "Dane County", "fish fry", "supper club", "custard", "WI Score", "wi_"):
    hits = [m.start() for m in re.finditer(re.escape(word), s)]
    if hits:
        print(f"note: {len(hits)} '{word}' left, e.g. {s[max(0, hits[0]-60):hits[0]+40]!r}")
open(os.path.join(ROOT, "site", "index.html"), "w").write(s)
print("wrote site/index.html", len(s) // 1024, "KB")
