import hashlib, json, re, shutil, subprocess, unicodedata
from pathlib import Path
from PIL import ImageStat
from PIL import Image, ImageOps
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "fotky", ROOT / "_site"
SITE_FILES = ["index.html", "style.css", "app.js", "profil.jpg", "og.jpg", "hero.jpg", "hero-m.jpg", "fonts/Zodiak-Variable.woff2", "fonts/Satoshi-Variable.woff2"]
KNOWN = {  # pořadí tady = pořadí kategorií na webu
    "portrety": ("Portréty a lidé", "Fotografie"),
    "produkt": ("Produkty a značky", "Fotografie"),
    "architektura": ("Architektura a prostor", "Fotografie"),
    "priroda": ("Příroda", "Fotografie"),
    "volna-tvorba": ("Volná tvorba", "Fotografie"),
    "design": ("Design", "Design"),
    "video": ("Video", "Video"),
    "reportaz": ("Reportáž", "Fotografie"),
    "ostatni": ("Ostatní", "Fotografie"),
}
VIDEO_EXT = {".mp4", ".webm"}
EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff"}
CAMERA = re.compile(r"^(img|dsc|dscf|dscn|_mg|_dsc|_dsf|dsf|pxl|mvimg|photo|image|gopr|dji|screenshot|snimek|whatsapp|\d|[_a-z]{1,5}\d{3,})", re.I)

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"

def nice(name):
    s = re.sub(r"[-_]+", " ", name).strip()
    return s[:1].upper() + s[1:]

def folder_title(folder, fallback):
    f = folder / "nazev.txt"
    if f.exists():
        text = f.read_text("utf-8").strip()
        if text:
            return text.splitlines()[0].strip()
    return fallback

YEAR = re.compile(r"^(?:19|20)\d{2}(?:\s*[–-]\s*(?:(?:19|20)?\d{2}|současnost|dosud))?$", re.I)

def name_meta(value):
    """„Název | 2024 | Popis“ -> (název, rok, popis).
    Rok i popis jsou nepovinné a nezáleží na pořadí: rok se pozná podle čísla (2024, 2023–2024),
    všechno ostatní za názvem je popis. Prázdná pole a mezery navíc nevadí."""
    parts = [x.strip() for x in (value or "").split("|")]
    title = parts[0] if parts else ""
    year, desc = "", []
    for p in parts[1:]:
        if not p:
            continue
        if not year and YEAR.match(p):
            year = p
        else:
            desc.append(p)
    return title, year, ", ".join(desc)

def norm(s):
    """Porovnání názvů souborů bez ohledu na velká písmena, diakritiku, koncovku,
    číslo pořadí na začátku, „(1)“ na konci a mezery/podtržítka/pomlčky."""
    s = Path(str(s).strip()).name
    s = re.sub(r"\.(jpe?g|png|webp|heic|heif|tiff?|mp4|webm)$", "", s, flags=re.I)
    s = re.sub(r"^\d{1,4}[ _.\-]+", "", s)
    s = re.sub(r"\s*\(\d+\)$", "", s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[\s_.\-]+", " ", s).strip()

def load_names(folder):
    """nazvy.txt: na každém řádku  soubor.jpg = Název | rok | popis  (rok a popis nepovinné).
    Řádek se najde i podle názvu, když soubor mezitím přejmenuješ přímo na ten název."""
    names, f = {}, folder / "nazvy.txt"
    if f.exists():
        for line in f.read_text("utf-8-sig").splitlines():
            if line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k and v:
                names.setdefault(norm(k), v)
                t = name_meta(v)[0]
                if t:
                    names.setdefault("title:" + norm(t), v)
    return names

def find_name(names, path):
    key = norm(path.name)
    return names.get(key) or names.get("title:" + key)

def yt_or_vimeo(url):
    """Vrátí (typ, id, na_výšku) pro odkaz z YouTube nebo Vimea."""
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/))([\w-]{11})", url)
    if m:
        return "yt", m.group(1), "/shorts/" in url
    m = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
    if m:
        return "vimeo", m.group(1), False
    return None

def load_videos(folder, cat):
    """videa.txt: na každém řádku  Název | odkaz na YouTube nebo Vimeo. Nahoře = nejnovější."""
    f, out = folder / "videa.txt", []
    if not f.exists():
        return out
    lines = [l.strip() for l in f.read_text("utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
    base = added_time(f)
    for i, line in enumerate(lines):
        title, _, url = line.rpartition("|") if "|" in line else ("", "", line)
        found = yt_or_vimeo(url.strip())
        if not found:
            continue
        kind, vid, tall = found
        w, h = (900, 1600) if tall else (1600, 900)
        thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if kind == "yt" else ""
        out.append({"full": thumb, "thumb": thumb, "w": w, "h": h, "tw": w, "th": h, "cat": cat,
                    "title": title.strip(), "proj": None, "t": base + len(lines) - i, "name": f"~video{i:03d}", "vid": {"type": kind, "id": vid}})
    return out

def video_file(path, cat, out_dir, names):
    """Krátké video (.mp4/.webm) přímo na webu – do 25 MB."""
    key = hashlib.sha1(str(path.relative_to(ROOT)).encode()).hexdigest()[:12]
    out_dir.mkdir(exist_ok=True)
    dest = out_dir / f"{key}{path.suffix.lower()}"
    shutil.copy2(path, dest)
    order, clean = split_order(path.stem)
    own_title, year, desc = name_meta(find_name(names, path))
    title = own_title or ("" if CAMERA.match(clean) else nice(clean))
    return {"full": "", "thumb": "", "w": 1600, "h": 900, "tw": 1600, "th": 900, "cat": cat, "title": title,
            "proj": None, "t": added_time(path), "o": order, "y": year, "d": desc, "name": path.stem.lower(), "vid": {"type": "file", "src": f"video/{dest.name}"}}

def load_reviews():
    """recenze.txt: jedna recenze na řádek ve tvaru  Jméno | Text
    (starší tvar s hvězdičkami „Jméno | 5 | Text“ funguje taky, hvězdičky se ignorují)"""
    f, out = ROOT / "recenze.txt", []
    if f.exists():
        for line in f.read_text("utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            parts = [x.strip() for x in line.split("|")]
            name = parts[0]
            rest = parts[1:]
            if len(rest) >= 2 and (rest[0].isdigit() or rest[0] == ""):
                rest = rest[1:]  # starý sloupec s hvězdičkami
            text = " | ".join(rest).strip(' "„“”')
            if name and text:
                out.append({"name": name, "text": text})
    return out

def added_time(path):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ct", "--", str(path.relative_to(ROOT))],
                             cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if out:
            return int(out)
    except Exception:
        pass
    return int(path.stat().st_mtime)

def save(im, dest, max_px, quality):
    im = im.copy()
    im.thumbnail((max_px, max_px), Image.LANCZOS)
    im.save(dest, "JPEG", quality=quality, optimize=True, progressive=True)
    return im.size

BIG = 10**6
ORDER = re.compile(r"^(\d{1,4})[ _.\-]+(.+)$")
def split_order(stem):
    """„03_dsf0368“ -> (3, „dsf0368“). Bez čísla na začátku -> (BIG, stem)."""
    m = ORDER.match(stem)
    return (int(m.group(1)), m.group(2)) if m else (BIG, stem)

def process(path, cat, proj, proj_title, img_dir, names=None):
    key = hashlib.sha1(str(path.relative_to(ROOT)).encode()).hexdigest()[:12]
    full, thumb = img_dir / f"{key}.jpg", img_dir / f"{key}-n.jpg"
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", im.size, "white")
            bg.paste(rgba, mask=rgba.split()[-1])
            im = bg
        im = im.convert("RGB")
        w, h = save(im, full, 2400, 86)
        tw, th = save(im, thumb, 900, 80)
    stem = path.stem
    names = names or {}
    order, clean = split_order(stem)
    own_title, year, desc = name_meta(find_name(names, path))
    title = own_title or proj_title or ("" if CAMERA.match(clean) else nice(clean))
    return {"o": order, "y": year, "d": desc, "full": f"img/{full.name}", "thumb": f"img/{thumb.name}", "w": w, "h": h, "tw": tw, "th": th,
            "cat": cat, "title": title, "proj": proj, "t": added_time(path), "name": stem.lower()}

# ---------- Projekty: složka projekty/<nazev>/ s projekt.txt a fotkami -> podstránka /projekty/<nazev>/ ----------
PROJ_SRC = ROOT / "projekty"
SITE_URL = "https://atelierzajicek.cz"
FIELDS = {"nazev": "title", "název": "title", "podtitul": "sub", "rok": "year", "klient": "client",
          "obor": "field", "role": "role", "obal": "cover", "popis": "desc"}

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))

ONE = re.compile(r"(^|[\s(„\"'])([AaIiKkOoSsUuVvZz])\s+(?=\S)")
def nb(s):
    """Jednopísmenná slova (a, i, k, o, s, u, v, z) spojí s dalším slovem nezlomitelnou mezerou."""
    s = esc(s)
    return ONE.sub(lambda m: m.group(1) + m.group(2) + "&nbsp;", ONE.sub(lambda m: m.group(1) + m.group(2) + "&nbsp;", s))

def read_project(folder):
    f = folder / "projekt.txt"
    meta, body = {}, []
    if f.exists():
        lines = f.read_text("utf-8-sig").splitlines()
        in_body = False
        for line in lines:
            if line.strip().startswith("#") and not line.strip().startswith("##"):
                continue
            if not in_body:
                if line.strip() == "---":
                    in_body = True
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    key = FIELDS.get(k.strip().lower())
                    if key and v.strip():
                        meta[key] = v.strip()
            else:
                body.append(line)
    meta.setdefault("title", nice(split_order(folder.name)[1]))
    return meta, "\n".join(body).strip()

def body_html(text):
    out = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if lines[0].startswith("## "):
            out.append(f"<h2>{nb(lines[0][3:].strip())}</h2>")
            lines = lines[1:]
        if lines:
            out.append("<p>" + "<br>".join(nb(l.strip()) for l in lines) + "</p>")
    return "\n".join(out)

def page_head(title, desc, image, url, css):
    return f"""<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)} – Jakub Zajíček</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)} – Jakub Zajíček">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
{f'<meta property="og:image" content="{image}">' if image else ''}
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%2336492E'/%3E%3Ctext x='16' y='22' font-family='Arial' font-weight='700' font-size='16' fill='white' text-anchor='middle'%3EZ%3C/text%3E%3C/svg%3E">

<link rel="stylesheet" href="/{css}">
</head>
<body class="proj-page">
<header class="site-head">
  <div class="wrap">
    <a class="brand" href="/" aria-label="Jakub Zajíček – hlavní stránka"><span>Jakub</span> <b>Zajíček</b></a>
    <nav class="nav" aria-label="Hlavní navigace">
      <a href="/#portfolio">Portfolio</a>
      <a class="nav-proj" href="/#projekty">Projekty</a>
      <a href="/#o-mne">O mně</a>
      <a href="/#kontakt">Kontakt</a>
    </nav>
  </div>
</header>
"""

def video_size(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                              "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip()
        w, h = (int(x) for x in out.split(",")[:2])
        return w, h
    except Exception:
        return 16, 9

def build_projects(img_dir, css):
    projects, failed = [], []
    if not PROJ_SRC.exists():
        return projects, failed
    folders = sorted((p for p in PROJ_SRC.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))),
                     key=lambda p: (split_order(p.name)[0], p.name))
    for folder in folders:
        meta, text = read_project(folder)
        pid = slug(split_order(folder.name)[1])
        names = load_names(folder)
        imgs, files = [], []
        for f in sorted(folder.iterdir(), key=lambda f: (split_order(f.stem)[0], f.name.lower())):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            key = hashlib.sha1(str(f.relative_to(ROOT)).encode()).hexdigest()[:12]
            t, y, d = name_meta(find_name(names, f))
            cap = ", ".join(x for x in (t, d, y) if x)
            if ext == ".pdf":
                # PDF (např. manuál identity) -> tlačítko ke stažení
                dest = OUT / "files" / f"{slug(split_order(f.stem)[1])}-{key[:6]}.pdf"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                files.append({"href": "files/" + dest.name, "label": t or nice(split_order(f.stem)[1]),
                              "size": f"{f.stat().st_size / 1e6:.0f} MB" if f.stat().st_size >= 1e6 else f"{f.stat().st_size // 1000} kB"})
                continue
            if ext == ".gif" or ext in VIDEO_EXT:
                # animovaný GIF a video se kopírují beze změny, aby zůstal pohyb
                sub = "img" if ext == ".gif" else "video"
                dest = OUT / sub / f"{key}{ext}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                if ext == ".gif":
                    with Image.open(f) as im:
                        w, h = im.size
                else:
                    w, h = video_size(f)
                imgs.append({"full": f"{sub}/{dest.name}", "thumb": f"{sub}/{dest.name}", "w": w, "h": h, "tw": w, "th": h,
                             "cap": cap, "file": f.name.lower(), "kind": "video" if ext in VIDEO_EXT else "gif"})
                continue
            if ext in EXT:
                try:
                    p = process(f, "projekt", pid, None, img_dir, names)
                    p["cap"] = cap
                    p["file"] = f.name.lower()
                    imgs.append(p)
                except Exception as e:
                    failed.append(f"{f.relative_to(ROOT)}: {e}")
        if not imgs:
            continue
        cover = next((p for p in imgs if p.get("kind") != "video"), imgs[0])
        if meta.get("cover"):
            want = norm(meta["cover"])
            cover = next((p for p in imgs if norm(p["file"]) == want), cover)
        projects.append({"id": pid, "meta": meta, "text": text, "imgs": imgs, "cover": cover, "files": files})

    for i, pr in enumerate(projects):
        m, cover = pr["meta"], pr["cover"]
        nxt = projects[(i + 1) % len(projects)] if len(projects) > 1 else None
        sub = m.get("sub", "")
        desc = m.get("desc") or sub or f"Projekt {m['title']} – Jakub Zajíček, fotograf, videomaker a grafik."
        rows = [(k, m[v]) for k, v in (("Klient", "client"), ("Obor", "field"), ("Role", "role"), ("Rok", "year")) if m.get(v)]
        # Rozložení „zarovnané řady“: fotky v jedné řadě mají vždy stejnou výšku a dohromady vyplní celou šířku.
        # Výrazně široké fotky a videa mají řadu samy pro sebe, ostatní se skládají po 2–3,
        # dokud řada nemá rozumnou výšku (součet poměrů stran aspoň ~1,6). Poslední neúplná řada se zmenší a vycentruje.
        rest = [p for p in pr["imgs"] if p is not cover]
        grows, cur = [], []
        def ar(p):
            return max(0.3, p["w"] / p["h"])
        for p in rest:
            solo = p.get("kind") == "video" or (ar(p) >= 1.6 and p["w"] >= 1400)
            if solo:
                if cur: grows.append(cur); cur = []
                grows.append([p]); continue
            cur.append(p)
            if sum(ar(x) for x in cur) >= 1.6 or len(cur) == 3:
                grows.append(cur); cur = []
        if cur: grows.append(cur)
        figs = []
        for row in grows:
            total = sum(ar(p) for p in row)
            cells = []
            for p in row:
                cap = f"<figcaption>{nb(p['cap'])}</figcaption>" if p["cap"] else ""
                if p.get("kind") == "video":
                    media = f'<video src="/{p["full"]}" width="{p["w"]}" height="{p["h"]}" controls playsinline preload="metadata"></video>'
                else:
                    media = f'<img src="/{p["full"]}" width="{p["w"]}" height="{p["h"]}" loading="lazy" decoding="async" alt="{esc(p["cap"] or m["title"])}">'
                cells.append(f'<figure class="pj-img" style="flex:{ar(p):.4f} 1 0%">{media}{cap}</figure>')
            style = f' style="max-width:{total * 620:.0f}px"' if total < 1.4 else ""
            figs.append(f'<div class="pj-row"{style}>{"".join(cells)}</div>')
        dl = "".join(f'<a class="pj-file" href="/{x["href"]}" download><svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M9 2.5v9M5 8l4 4 4-4M3 15.5h12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><span><b>{nb(x["label"])}</b><small>PDF · {x["size"]}</small></span></a>' for x in pr["files"])
        html = page_head(m["title"], desc, f"{SITE_URL}/{cover['full']}", f"{SITE_URL}/projekty/{pr['id']}/", css)
        html += f"""
<main class="pj">
  <div class="wrap">
    <a class="pj-back" href="/#projekty"><svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M11 7H3M6.5 3.5 3 7l3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>Všechny projekty</a>
    <header class="pj-head">
      <h1>{nb(m['title'])}</h1>
      {f'<p class="pj-sub">{nb(sub)}</p>' if sub else ''}
      {('<dl class="pj-meta">' + ''.join(f'<div><dt>{k}</dt><dd>{nb(v)}</dd></div>' for k, v in rows) + '</dl>') if rows else ''}
    </header>
  </div>
  <figure class="pj-cover"><img src="/{cover['full']}" width="{cover['w']}" height="{cover['h']}" alt="{esc(m['title'])}" fetchpriority="high"></figure>
  {f'<div class="wrap pj-text">{body_html(pr["text"])}</div>' if pr["text"] else ''}
  {f'<div class="wrap pj-files">{dl}</div>' if dl else ''}
  {f'<div class="wrap pj-grid">{"".join(figs)}</div>' if figs else ''}
  <div class="wrap pj-end">
    <div class="pj-cta">
      <h2>Máte podobný projekt?</h2>
      <p>Napište mi, co máte v plánu, a domluvíme se.</p>
      <a class="btn btn-primary" href="/#kontakt">Napsat mi</a>
    </div>
    {f'<a class="pj-next" href="/projekty/{nxt["id"]}/"><span>Další projekt</span><b>{nb(nxt["meta"]["title"])}</b></a>' if nxt else ''}
  </div>
</main>
<footer class="foot"><div class="wrap"><a class="brand" href="/"><span>Jakub</span> <b>Zajíček</b></a><span>Fotograf, videomaker a grafik</span><span>© 2026 Jakub Zajíček</span></div></footer>
</body>
</html>
"""
        d = OUT / "projekty" / pr["id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(html, "utf-8")

    cards = [{"id": pr["id"], "title": pr["meta"]["title"], "sub": pr["meta"].get("sub", ""),
              "field": pr["meta"].get("field", ""), "year": pr["meta"].get("year", ""),
              "thumb": pr["cover"]["thumb"], "tw": pr["cover"]["tw"], "th": pr["cover"]["th"]} for pr in projects]
    return cards, failed

def find_photo(spec):
    """Najde fotku podle cesty (fotky/…/soubor.jpg) nebo podle názvu z nazvy.txt či názvu souboru."""
    spec = spec.strip()
    p = ROOT / spec
    if "/" in spec and p.exists():
        return p
    want = norm(spec)
    if not SRC.exists():
        return None
    for folder in sorted(SRC.iterdir()):
        if not folder.is_dir():
            continue
        names = load_names(folder)
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix.lower() in EXT:
                if norm(f.name) == want or norm(name_meta(find_name(names, f))[0]) == want:
                    return f
    return None

def build_hero_slides():
    """uvod.txt -> prezentace fotek v úvodu. Vrací True, když vznikla."""
    cfg, idx = ROOT / "uvod.txt", OUT / "index.html"
    if not (cfg.exists() and idx.exists()):
        return False
    items = []
    for line in cfg.read_text("utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split("|")]
        spec, opts = parts[0], [x.lower() for x in parts[1:] if x]
        f = find_photo(spec)
        if not f:
            print(f"Úvod: fotku „{spec}“ jsem nenašel, přeskakuji.")
            continue
        xpos, side = 50, False
        for o in opts:
            if o.isdigit():
                xpos = max(0, min(100, int(o)))
            elif o in ("vpravo", "celá", "cela", "bokem"):
                side = True  # celá fotka vpravo, vlevo navazuje barva jejího pozadí
        items.append((f, xpos, side))
    if not items:
        return False
    out = OUT / "hero"
    out.mkdir(parents=True, exist_ok=True)
    slides, dots = [], []
    for i, (f, xpos, side) in enumerate(items[:8]):
        with Image.open(f) as im0:
            im = ImageOps.exif_transpose(im0).convert("RGB")
        w, h = im.size
        big = im.copy()
        if side:
            # u snímku „vpravo“ ořízneme prázdné pozadí po stranách, aby motiv mohl být větší
            g0 = im.convert("L")
            sm = g0.resize((200, max(1, round(200 * h / w))))
            bgL = ImageStat.Stat(g0.crop((0, 0, max(1, w // 40), h))).mean[0]
            cols = [x for x in range(sm.width) if any(abs(sm.getpixel((x, y)) - bgL) > 28 for y in range(sm.height))]
            if cols:
                pad = 0.03 * w
                x0 = max(0, int(cols[0] / sm.width * w - pad)); x1 = min(w, int((cols[-1] + 1) / sm.width * w + pad))
                big = im.crop((x0, 0, x1, h))
        big.thumbnail((2400, 2400), Image.LANCZOS)
        key = hashlib.sha1(f"{f.relative_to(ROOT)}{xpos}".encode()).hexdigest()[:8]
        big.save(out / f"{key}.jpg", "JPEG", quality=84, optimize=True, progressive=True)
        # výřez na mobil 4:5
        cw = min(w, int(h * 4 / 5)); ch = min(h, int(w * 5 / 4))
        left = int((w - cw) * xpos / 100); top = (h - ch) // 2
        im.crop((left, top, left + cw, top + ch)).resize((1080, 1350), Image.LANCZOS).save(out / f"{key}-m.jpg", "JPEG", quality=82, optimize=True, progressive=True)
        # jas v místě textu (dole vlevo) -> barva textu
        g = im.convert("L")
        light = ImageStat.Stat(g.crop((0, int(h * 0.5), int(w * 0.5), h))).mean[0] / 255 > 0.55
        extra = ""
        if side:
            edge = ImageStat.Stat(im.crop((0, 0, max(1, w // 40), h))).mean
            extra = ' style="--slide-bg:#%02x%02x%02x"' % tuple(round(v) for v in edge[:3])
            light = sum(edge[:3]) / 3 / 255 > 0.55
        tone = "light" if light else "dark"
        title = name_meta(find_name(load_names(f.parent), f))[0] or nice(split_order(f.stem)[1])
        first = i == 0
        load_attr = ' fetchpriority="high"' if first else ' loading="lazy"'
        pos_attr = "" if side else f' style="object-position:{xpos}% 50%"'
        slides.append(
            f'<figure class="hp-slide{" is-active" if first else ""}{" is-side" if side else ""}" data-tone="{tone}"{extra}>'
            f'<picture><source media="(max-width: 700px)" srcset="hero/{key}-m.jpg" width="1080" height="1350">'
            f'<img src="hero/{key}.jpg" width="{big.width}" height="{big.height}" alt="{esc(title)}"{pos_attr}'
            f'{load_attr} decoding="async"></picture></figure>')
        dots.append(f'<button type="button" class="hp-dot{" is-active" if first else ""}" aria-label="Fotka {i + 1}: {esc(title)}"><span></span></button>')
    first_tone = "tone-light" if 'data-tone="light"' in slides[0] else "tone-dark"
    media = (f'<div class="hp-slides">{"".join(slides)}'
             f'<div class="hp-dots">{"".join(dots) if len(slides) > 1 else ""}</div></div>')
    s = idx.read_text("utf-8")
    m = re.search(r'<picture class="hp-media">.*?</picture>', s, re.S)
    if not m:
        return False
    s = s[:m.start()] + media + s[m.end():]
    s = s.replace('class="hero-photo"', f'class="hero-photo has-slides {first_tone}"', 1)
    idx.write_text(s, "utf-8")
    return True

def hero_tone():
    """Podle jasu hero.jpg v místě textu (dole vlevo) nastaví světlý nebo tmavý text v úvodu."""
    f, idx = ROOT / "hero.jpg", OUT / "index.html"
    if not (f.exists() and idx.exists()):
        return
    try:
        with Image.open(f) as im:
            g = im.convert("L")
            w, h = g.size
            r = g.crop((0, int(h * 0.45), int(w * 0.5), h))
            light = ImageStat.Stat(r).mean[0] / 255 > 0.55
        with Image.open(f) as im:
            rgb = im.convert("RGB")
            w, h = rgb.size
            edge = ImageStat.Stat(rgb.crop((0, 0, max(1, w // 40), h))).mean  # barva levého okraje fotky
        bg = "#%02x%02x%02x" % tuple(round(v) for v in edge[:3])
        s = idx.read_text("utf-8")
        s = s.replace('class="hero-photo"', f'class="hero-photo {"tone-light" if light else "tone-dark"}" style="--hero-bg:{bg}"', 1)
        idx.write_text(s, "utf-8")
    except Exception:
        pass

def bust_cache():
    """style.css a app.js dostanou v názvu otisk obsahu, aby prohlížeče vždy načetly novou verzi."""
    names = {}
    for f in ("style.css", "app.js"):
        src = OUT / f
        if src.exists():
            h = hashlib.sha1(src.read_bytes()).hexdigest()[:8]
            new = f"{src.stem}.{h}{src.suffix}"
            src.rename(OUT / new)
            names[f] = new
    idx = OUT / "index.html"
    if idx.exists():
        s = idx.read_text("utf-8")
        for old, new in names.items():
            s = s.replace(f'"{old}"', f'"{new}"')
        idx.write_text(s, "utf-8")
    return names

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    img_dir = OUT / "img"
    img_dir.mkdir(parents=True)
    for f in SITE_FILES:
        if (ROOT / f).exists():
            (OUT / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / f, OUT / f)
    categories, photos, failed = [], [], []
    if SRC.exists():
        order = list(KNOWN)
        rank = lambda p: (order.index(slug(p.name)) if slug(p.name) in order else len(order), p.name)
        for cat_dir in sorted((p for p in SRC.iterdir() if p.is_dir() and not p.name.startswith(".")), key=rank):
            cid = slug(cat_dir.name)
            label, kind = KNOWN.get(cid, (nice(cat_dir.name), "Fotografie"))
            label = folder_title(cat_dir, label)
            categories.append({"id": cid, "label": label, "kind": kind})
            cat_names = load_names(cat_dir)
            photos.extend(load_videos(cat_dir, cid))
            for item in sorted(cat_dir.iterdir()):
                try:
                    if item.is_file() and item.suffix.lower() in VIDEO_EXT:
                        photos.append(video_file(item, cid, OUT / "video", cat_names))
                    elif item.is_file() and item.suffix.lower() in EXT:
                        photos.append(process(item, cid, None, None, img_dir, cat_names))
                    elif item.is_dir():
                        pid = cid + "/" + slug(item.name)
                        ptitle = folder_title(item, nice(item.name))
                        pnames = load_names(item)
                        for f in sorted(item.iterdir()):
                            if f.is_file() and f.suffix.lower() in EXT:
                                try:
                                    photos.append(process(f, cid, pid, ptitle, img_dir, pnames))
                                except Exception as e:
                                    failed.append(f"{f.relative_to(ROOT)}: {e}")
                except Exception as e:
                    failed.append(f"{item.relative_to(ROOT)}: {e}")
    order = list(KNOWN)
    categories.sort(key=lambda c: (order.index(c["id"]) if c["id"] in order else 99, c["label"]))
    # Fotky s číslem na začátku názvu (01_…, 02_…) jdou první v tomto pořadí, ostatní za nimi od nejnovější.
    photos.sort(key=lambda p: (p.get("o", BIG), -p["t"], p["proj"] or "", p["name"]))
    for p in photos:
        p.pop("name")
    if not build_hero_slides():
        hero_tone()
    assets = bust_cache()
    projects, pfail = build_projects(img_dir, assets.get("style.css", "style.css"))
    failed += pfail
    (OUT / "gallery.json").write_text(json.dumps({"categories": categories, "photos": photos, "projects": projects, "reviews": load_reviews()}, ensure_ascii=False), "utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"Hotovo: {len(photos)} fotek v {len(categories)} kategoriích, {len(projects)} projektů.")
    for f in failed:
        print("Nepodařilo se zpracovat:", f)

if __name__ == "__main__":
    main()
