import hashlib, json, re, shutil, subprocess, unicodedata
from pathlib import Path
from PIL import Image, ImageOps
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "fotky", ROOT / "_site"
SITE_FILES = ["index.html", "style.css", "app.js", "profil.jpg"]
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

def load_names(folder):
    """nazvy.txt: na každém řádku  soubor.jpg = Hezký název"""
    names, f = {}, folder / "nazvy.txt"
    if f.exists():
        for line in f.read_text("utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k and v:
                    names[k.lower()] = v
                    names[Path(k).stem.lower()] = v
    return names

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
    key = hashlib.sha1(str(path.relative_to(SRC)).encode()).hexdigest()[:12]
    out_dir.mkdir(exist_ok=True)
    dest = out_dir / f"{key}{path.suffix.lower()}"
    shutil.copy2(path, dest)
    order, clean = split_order(path.stem)
    title = names.get(path.name.lower()) or names.get(path.stem.lower()) or names.get(clean.lower()) or ("" if CAMERA.match(clean) else nice(clean))
    return {"full": "", "thumb": "", "w": 1600, "h": 900, "tw": 1600, "th": 900, "cat": cat, "title": title,
            "proj": None, "t": added_time(path), "o": order, "name": path.stem.lower(), "vid": {"type": "file", "src": f"video/{dest.name}"}}

def load_reviews():
    """recenze.txt: jedna recenze na řádek ve tvaru  Jméno | Hvězdičky 1–5 | Text"""
    f, out = ROOT / "recenze.txt", []
    if f.exists():
        for line in f.read_text("utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [x.strip() for x in line.split("|")]
            if len(parts) < 3:
                continue
            if len(parts) >= 4 and not parts[1].isdigit():  # starší tvar s typem focení
                parts = [parts[0], parts[2], "|".join(parts[3:])]
            name, stars, text = parts[0], parts[1], " | ".join(parts[2:])
            try:
                stars = max(1, min(5, int(stars)))
            except ValueError:
                stars = 5
            text = text.strip(' "„“”')
            if name and text:
                out.append({"name": name, "stars": stars, "text": text})
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
    key = hashlib.sha1(str(path.relative_to(SRC)).encode()).hexdigest()[:12]
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
    own = names.get(path.name.lower()) or names.get(stem.lower()) or names.get(clean.lower())
    title = own or proj_title or ("" if CAMERA.match(clean) else nice(clean))
    return {"o": order, "full": f"img/{full.name}", "thumb": f"img/{thumb.name}", "w": w, "h": h, "tw": tw, "th": th,
            "cat": cat, "title": title, "proj": proj, "t": added_time(path), "name": stem.lower()}

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    img_dir = OUT / "img"
    img_dir.mkdir(parents=True)
    for f in SITE_FILES:
        if (ROOT / f).exists():
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
    (OUT / "gallery.json").write_text(json.dumps({"categories": categories, "photos": photos, "reviews": load_reviews()}, ensure_ascii=False), "utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"Hotovo: {len(photos)} fotek v {len(categories)} kategoriích.")
    for f in failed:
        print("Nepodařilo se zpracovat:", f)

if __name__ == "__main__":
    main()
