"""Offline backup deck from the exported notebook: `uv run marimo export html fingerprints_marimo.py -o docs/fingerprints_demo.html` then `uv run python scripts/build_deck.py scratchpad/deck` and copy the PDF into docs/. Needs kaleido and Google Chrome."""
import re, html, json, sys, subprocess
from pathlib import Path
import plotly.io as pio
src = Path("docs/fingerprints_demo.html"); out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); img = out / "img"; img.mkdir(exist_ok=True)
s = src.read_text()
j = s.find('"session": {"cells"'); start = s.find('{', j); depth = 0
for k in range(start, len(s)):
    if s[k] == '{': depth += 1
    elif s[k] == '}':
        depth -= 1
        if depth == 0: end = k + 1; break
sess = json.loads(s[start:end])
def text_of(h):
    t = re.sub(r"<[^>]+>", " ", h); return re.sub(r"\s+", " ", html.unescape(t)).strip()
def attr(v):  # marimo attributes are html-escaped JSON literals
    try: return json.loads(html.unescape(v))
    except Exception: return None
pages, n_fig = [], 0
for i, c in enumerate(sess["cells"]):
    for o in c.get("outputs") or []:
        raw = o.get("data")
        h = raw.get("text/html") or raw.get("text/markdown") or "" if isinstance(raw, dict) else str(raw)
        if not h: continue
        heads = [text_of(m) for m in re.findall(r"<h[123][^>]*>(.*?)</h[123]>", h, re.S)]
        takes = [text_of(attr(m) or "") for m in re.findall(r"<marimo-callout-output data-html='([^']*)'", h)]
        stats = []
        for m in re.finditer(r"<marimo-stat ([^>]*)>", h):
            a = dict(re.findall(r"data-([a-z-]+)='([^']*)'", m.group(1)))
            lab, val, cap = (attr(a.get(k, '""')) for k in ("label", "value", "caption"))
            if val is not None: stats.append((text_of(str(lab or "")), text_of(str(val)), text_of(str(cap or ""))))
        tables = []
        for m in re.finditer(r"<marimo-table [^>]*data-data='([^']*)'", h):
            rows = attr(m.group(1))
            if isinstance(rows, str):
                try: rows = json.loads(rows)
                except Exception: rows = None
            if rows and isinstance(rows, list) and isinstance(rows[0], dict): tables.append(rows[:10])
        # plain prose outside callouts/headings
        body_h = re.sub(r"<marimo-[a-z-]+.*?</marimo-[a-z-]+>", " ", h, flags=re.S)
        paras = [text_of(p) for p in re.findall(r"<span class=\"paragraph\">(.*?)</span>|<p[^>]*>(.*?)</p>", body_h, re.S) for p in p if p]
        paras = [p for p in paras if p and p not in heads and p not in takes]
        figs = []
        for m in re.finditer(r"<marimo-plotly[^>]*data-figure='([^']*)'", h):
            n_fig += 1
            png = img / f"fig{n_fig:02d}.png"
            if not png.exists():
                fig = json.loads(html.unescape(m.group(1)))
                hgt = (fig.get("layout") or {}).get("height") or 500
                try: pio.write_image(fig, str(png), width=1100, height=int(hgt), scale=1); print("rendered", png.name, flush=True)
                except Exception as e: sys.exit(f"FAILED {png.name}: {str(e)[:200]}\n(kaleido is a dev dependency: uv sync)")
            figs.append(png.name)
        if heads or figs or takes or stats or tables:
            page = {"heads": heads, "takes": takes, "stats": stats, "tables": tables, "paras": paras[:4], "figs": figs}
            if pages and not (figs or stats or tables) and not (pages[-1]["figs"] or pages[-1]["stats"] or pages[-1]["tables"]):
                for k in ("heads", "takes", "paras"): pages[-1][k] += page[k]   # text-only screens share a page
            else:
                pages.append(page)
css = ("@page{size:11in 8.5in;margin:0.35in} body{font:15px/1.4 system-ui;margin:0;color:#1b1b3a} "
       ".page{page-break-after:always;break-after:page;padding:12px 26px;height:7.7in;box-sizing:border-box;display:flex;flex-direction:column;overflow:hidden} "
       ".page:last-child{page-break-after:auto;break-after:auto} h1{font-size:34px;margin:0 0 6px} h2{font-size:23px;margin:0 0 4px} h3{font-size:16px;color:#444;margin:0 0 4px} "
       ".take{border-left:4px solid #54a24b;background:#f2f8f2;padding:6px 12px;margin:4px 0 8px;font-size:13.5px} "
       ".stats{display:flex;gap:18px;margin:4px 0 8px} .stat{border:1px solid #ddd;border-radius:6px;padding:6px 12px;min-width:120px} .stat b{font-size:20px;display:block} .stat small{color:#666} "
       ".figs{flex:1 1 0;min-height:0;display:flex;flex-direction:column;gap:4px} img{flex:1 1 0;min-height:0;width:100%;object-fit:contain;object-position:left top;display:block} "
       "table{border-collapse:collapse;font-size:11px;margin:4px 0} th,td{border:1px solid #ddd;padding:2px 6px;text-align:left} th{background:#f4f4f8} p{margin:3px 0;color:#333;font-size:12.5px}")
body = ['<div class="page"><h1>A number without its ground</h1><p style="font-size:17px">Fingerprints for the OSPD mangrove workflow. Offline render of <code>fingerprints_marimo.py</code>, Sundarbans, resolution 9, OGC API-DGGS Annex B rHEALPix profile.</p><p>Pages follow the twelve screens of the live notebook. Interactive controls are omitted; every figure is the state the notebook opens in.</p></div>']
for p in pages:
    parts = ["".join(f"<h2>{html.escape(x)}</h2>" if len(x) > 3 and x[0].isdigit() else f"<h3>{html.escape(x)}</h3>" for x in p["heads"])]
    parts += [f'<div class="take">{html.escape(t)}</div>' for t in p["takes"]]
    if p["stats"]: parts.append('<div class="stats">' + "".join(f'<div class="stat"><small>{html.escape(l)}</small><b>{html.escape(v)}</b><small>{html.escape(c)}</small></div>' for l, v, c in p["stats"]) + "</div>")
    if p["figs"]: parts.append('<div class="figs">' + "".join(f'<img src="img/{f}">' for f in p["figs"]) + "</div>")
    for rows in p["tables"]:
        cols = list(rows[0]); parts.append("<table><tr>" + "".join(f"<th>{html.escape(str(c))}</th>" for c in cols) + "</tr>" + "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>" for r in rows) + "</table>")
    parts += [f"<p>{html.escape(x)}</p>" for x in p["paras"]]
    body.append('<div class="page">' + "".join(parts) + "</div>")
(out / "deck.html").write_text("<!doctype html><meta charset='utf-8'><title>Fingerprints deck</title><style>" + css + "</style>" + "".join(body))
print("pages", len(pages), "figures", n_fig, "takes", sum(len(p["takes"]) for p in pages), "stats", sum(len(p["stats"]) for p in pages), "tables", sum(len(p["tables"]) for p in pages))
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out / 'fingerprints_deck.pdf'}", str((out / 'deck.html').resolve().as_uri())], check=False, timeout=180, capture_output=True)
print("pdf", (out / "fingerprints_deck.pdf").stat().st_size)
