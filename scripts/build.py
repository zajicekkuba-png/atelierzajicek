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
KNOWN = {
    "produkt": ("Produkt", "Fotografie"),
    "portrety": ("Portréty a lidé", "Fotografie"),
    "reportaz": ("Reportáž", "Fotografie"),
    "architektura": ("Architektura", "Fotografie"),
    "priroda": ("Příroda", "Fotografie"),
    "design": ("Grafický design", "Design"),
    "ostatni": ("Ostatní", "Fotografie"),
}
EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff"}
CAMERA = re.compile(r"^(img|dsc|dscf|dscn|_mg|_dsc|pxl|mvimg|photo|image|gopr|dji|screenshot|snimek|whatsapp|\d)", re.I)

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

def process(path, cat, proj, proj_title, img_dir):
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
    title = proj_title or ("" if CAMERA.match(stem) else nice(stem))
    return {"full": f"img/{full.name}", "thumb": f"img/{thumb.name}", "w": w, "h": h, "tw": tw, "th": th,
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
        for cat_dir in sorted(p for p in SRC.iterdir() if p.is_dir() and not p.name.startswith(".")):
            cid = slug(cat_dir.name)
            label, kind = KNOWN.get(cid, (nice(cat_dir.name), "Fotografie"))
            label = folder_title(cat_dir, label)
            categories.append({"id": cid, "label": label, "kind": kind})
            for item in sorted(cat_dir.iterdir()):
                try:
                    if item.is_file() and item.suffix.lower() in EXT:
                        photos.append(process(item, cid, None, None, img_dir))
                    elif item.is_dir():
                        pid = cid + "/" + slug(item.name)
                        ptitle = folder_title(item, nice(item.name))
                        for f in sorted(item.iterdir()):
                            if f.is_file() and f.suffix.lower() in EXT:
                                try:
                                    photos.append(process(f, cid, pid, ptitle, img_dir))
                                except Exception as e:
                                    failed.append(f"{f.relative_to(ROOT)}: {e}")
                except Exception as e:
                    failed.append(f"{item.relative_to(ROOT)}: {e}")
    order = list(KNOWN)
    categories.sort(key=lambda c: (order.index(c["id"]) if c["id"] in order else 99, c["label"]))
    photos.sort(key=lambda p: (-p["t"], p["proj"] or "", p["name"]))
    for p in photos:
        p.pop("name")
    (OUT / "gallery.json").write_text(json.dumps({"categories": categories, "photos": photos}, ensure_ascii=False), "utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"Hotovo: {len(photos)} fotek v {len(categories)} kategoriích.")
    for f in failed:
        print("Nepodařilo se zpracovat:", f)

if __name__ == "__main__":
    main()
