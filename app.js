(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var PAGE = 24;
  var DATA = { categories: [], photos: [], reviews: [] };
  var CAT = {};
  var state = { view: "grid", filter: "vse", shown: PAGE, lbList: [], lbIndex: -1, lastFocus: null };

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function catOf(p) { return CAT[p.cat] || { label: p.cat, kind: "Fotografie" }; }
  function titleOf(p) { return p.title || catOf(p).label; }
  function toast(msg) { var t = $("toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(function () { t.classList.remove("show"); }, 3200); }

  /* ---------- filmstrip ---------- */
  function renderFilm() {
    var sec = $("filmSec"), film = $("film"), list = DATA.photos.filter(function (p) { return !p.vid; });
    if (list.length < 3) { sec.hidden = true; return; }
    /* Náhodné pořadí při každém načtení stránky (Fisher–Yates) */
    var mix = list.slice();
    for (var k = mix.length - 1; k > 0; k--) { var r = Math.floor(Math.random() * (k + 1)), t = mix[k]; mix[k] = mix[r]; mix[r] = t; }
    var pick = mix.slice(0, 14);
    var item = function (p, i, dup) {
      return '<button type="button" class="film-item" data-film="' + i + '"' + (dup ? ' aria-hidden="true" tabindex="-1"' : ' aria-label="Otevřít: ' + esc(titleOf(p)) + '"') + '>' +
        '<img src="' + p.thumb + '" alt="" width="' + p.tw + '" height="' + p.th + '"' + (i < 4 && !dup ? "" : ' loading="lazy"') + '>' +
        '<span>' + (p.title ? "<b>" + esc(p.title) + "</b> · " : "") + esc(catOf(p).label) + "</span></button>";
    };
    film.innerHTML = '<div class="film-track" style="--dur:' + (pick.length * 6) + 's">' +
      pick.map(function (p, i) { return item(p, i, false); }).join("") +
      pick.map(function (p, i) { return item(p, i, true); }).join("") + "</div>";
    film._list = pick; sec.hidden = false;
  }
  $("film").addEventListener("click", function (e) { var b = e.target.closest("[data-film]"); if (b) openFrom(this._list, +b.dataset.film); });

  /* ---------- gallery ---------- */
  function counts() { var c = {}; DATA.photos.forEach(function (p) { c[p.cat] = (c[p.cat] || 0) + 1; }); return c; }
  function filtered() { return state.filter === "vse" ? DATA.photos : DATA.photos.filter(function (p) { return p.cat === state.filter; }); }
  function renderFilters() {
    var c = counts(), f = $("filters");
    var defs = [{ id: "vse", label: "Všechny práce", n: DATA.photos.length }].concat(
      DATA.categories.filter(function (x) { return c[x.id]; }).map(function (x) { return { id: x.id, label: x.label, n: c[x.id] }; }));
    f.hidden = !DATA.photos.length || state.view === "list";
    $("viewtog").hidden = !DATA.photos.length;
    f.innerHTML = defs.map(function (d) { return '<button type="button" class="chip" data-f="' + d.id + '" aria-pressed="' + (d.id === state.filter) + '">' + esc(d.label) + " <small>" + d.n + "</small></button>"; }).join("");
  }
  var MQ = window.matchMedia("(max-width:700px)");
  /* Fotky z projektu se v galerii ukáží jen jednou (první fotka), po kliknutí se otevře celý projekt. */
  function items() {
    var seen = {}, src = filtered().filter(function (p) { if (!p.proj) return true; if (seen[p.proj]) return false; seen[p.proj] = 1; return true; });
    if (state.filter !== "vse") return src;
    var order = {}; DATA.categories.forEach(function (c, k) { order[c.id] = k; });
    var rank = function (p) { return order.hasOwnProperty(p.cat) ? order[p.cat] : 999; };
    return src.map(function (p, k) { return [p, k]; }).sort(function (a, b) { return (rank(a[0]) - rank(b[0])) || (a[1] - b[1]); }).map(function (x) { return x[0]; });
  }
  var PLAY = '<span class="play" aria-hidden="true"><i><svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13l11-6.5z"></path></svg></i></span>';
  function media(p, sizes) {
    if (p.vid) {
      var inner = p.thumb ? '<img src="' + p.thumb + '" alt="' + esc(titleOf(p)) + '" loading="lazy" decoding="async">'
        : p.vid.type === "file" ? '<video src="' + p.vid.src + '#t=0.1" muted playsinline preload="metadata" aria-hidden="true"></video>' : '<span class="vid-ph" aria-hidden="true"></span>';
      return inner + PLAY;
    }
    return '<img src="' + p.thumb + '" srcset="' + p.thumb + " " + p.tw + "w, " + p.full + " " + p.w + 'w" sizes="' + sizes + '" alt="' + esc(titleOf(p)) + '" loading="lazy" decoding="async">';
  }
  function isWide(p) { return p.tw > p.th * 1.15; }
  function tile(x, wide, mob) {
    var p = x.p, c = catOf(p), y = new Date(p.t * 1000).getFullYear();
    /* Na šířku: PC ořízne lehce na 16:9, panoramata a skoro čtvercové fotky neořezává (čtvercové jsou užší a na střed). */
    var nat = p.tw / p.th, ratio = "2 / 3", fig = "";
    if (wide && mob) ratio = p.tw + " / " + p.th;
    else if (wide) { var R = 16 / 9; ratio = nat < R ? (nat < 1.4 ? p.tw + " / " + p.th : "16 / 9") : p.tw + " / " + p.th; if (nat < 1.4) fig = ' style="flex-basis:' + (nat / R * 100).toFixed(1) + '%"'; }
    var sizes = wide ? "(max-width:700px) 100vw, 1184px" : (mob ? "50vw" : "(max-width:1232px) 33vw, 390px");
    return '<figure class="e-item"' + fig + '><button type="button" class="j" data-open="' + x.i + '" style="aspect-ratio:' + ratio + '" aria-label="Otevřít: ' + esc(titleOf(p)) + '">' +
      media(p, sizes) + "</button>" +
      "<figcaption><b>" + esc(titleOf(p)) + "</b><span>" + esc([p.d || c.kind, p.y].filter(Boolean).join(", ")) + "</span></figcaption>" + "</figure>";
  }
  /* Rytmus podle návrhu: fotka na šířku přes celou šířku, pak řada fotek na výšku (3 na PC, 2 na mobilu). */
  function groupHTML(arr, mob) {
    var n = mob ? 2 : 3, L = arr.filter(function (x) { return isWide(x.p); }), P = arr.filter(function (x) { return !isWide(x.p); }), out = "", turn = 0;
    while (L.length || P.length) {
      if ((turn % 2 === 0 && L.length) || !P.length) out += '<div class="e-row">' + tile(L.shift(), true, mob) + "</div>";
      else out += '<div class="e-row" style="--n:' + n + '">' + P.splice(0, n).map(function (x) { return tile(x, false, mob); }).join("") + "</div>";
      turn++;
    }
    return out;
  }
  function editorialHTML(vis) {
    var mob = MQ.matches, all = vis.map(function (p, i) { return { p: p, i: i }; });
    if (state.filter !== "vse") return groupHTML(all, mob);
    var out = "", k = 0;
    while (k < all.length) {
      var cat = all[k].p.cat, grp = [];
      while (k < all.length && all[k].p.cat === cat) grp.push(all[k++]);
      out += '<h3 class="e-cat">' + esc(catOf(grp[0].p).label) + "</h3>" + groupHTML(grp, mob);
    }
    return out;
  }
  function renderGrid() {
    var g = $("grid"), m = $("more");
    if (!DATA.photos.length) { g.className = ""; g.innerHTML = '<div class="empty">Galerie se právě připravuje. Ukázky práce rád pošlu e-mailem.</div>'; m.innerHTML = ""; return; }
    if (state.view === "list") {
      var c = counts(); g.className = "catlist"; m.innerHTML = "";
      g.innerHTML = DATA.categories.filter(function (x) { return c[x.id]; }).map(function (x) {
        var cover = DATA.photos.filter(function (p) { return p.cat === x.id && p.thumb; })[0];
        return '<button type="button" class="cat-row" data-cat="' + x.id + '"><span class="cat-name">' + esc(x.label) + '</span><span class="cat-n">' + c[x.id] + '</span>' + (cover ? '<img class="cat-cover" src="' + cover.thumb + '" alt="" loading="lazy">' : "") + "</button>";
      }).join("");
      return;
    }
    var list = items(), vis = list.slice(0, state.shown);
    g.className = "editorial"; g.innerHTML = editorialHTML(vis);
    m.innerHTML = vis.length < list.length ? '<button type="button" class="btn btn-ghost btn-small" id="moreBtn">Načíst další</button>' : "";
    var mb = $("moreBtn"); if (mb) mb.onclick = function () { state.shown += PAGE; renderGrid(); nbsp($("grid")); };
  }
  function syncView() { Array.prototype.forEach.call($("viewtog").children, function (b) { b.setAttribute("aria-pressed", String(b.dataset.v === state.view)); }); }
  $("viewtog").addEventListener("click", function (e) { var b = e.target.closest("[data-v]"); if (!b) return; state.view = b.dataset.v; if (state.view === "list") state.filter = "vse"; syncView(); renderFilters(); renderGrid(); });
  $("filters").addEventListener("click", function (e) { var b = e.target.closest("[data-f]"); if (!b) return; state.filter = b.dataset.f; state.shown = PAGE; renderFilters(); renderGrid(); });
  $("grid").addEventListener("click", function (e) {
    var cr = e.target.closest("[data-cat]");
    if (cr) { state.filter = cr.dataset.cat; state.view = "grid"; state.shown = PAGE; syncView(); renderFilters(); renderGrid(); $("portfolio").scrollIntoView(); return; }
    var o = e.target.closest("[data-open]"); if (o) openFrom(items(), +o.dataset.open);
  });
  if (MQ.addEventListener) MQ.addEventListener("change", function () { if (state.view === "grid") renderGrid(); });

  /* ---------- focus view ---------- */
  function openFrom(list, i) {
    var p = list[i];
    if (p && p.proj) { var proj = DATA.photos.filter(function (x) { return x.proj === p.proj; }); if (proj.length > 1) { openLb(proj, proj.indexOf(p)); return; } }
    openLb(list, i);
  }
  function renderStrip() {
    var st = $("lbStrip"), l = state.lbList; st.hidden = l.length < 2;
    st.innerHTML = l.length < 2 ? "" : l.map(function (p, k) { return '<button type="button" class="lb-th" data-i="' + k + '" aria-label="Fotka ' + (k + 1) + ": " + esc(titleOf(p)) + '">' + (p.thumb ? '<img src="' + p.thumb + '" alt="" width="' + p.tw + '" height="' + p.th + '" loading="lazy">' : '<span class="vid-ph"></span>') + "</button>"; }).join("");
  }
  function openLb(list, i) { state.lbList = list; state.lbIndex = i; renderStrip(); state.lastFocus = document.activeElement; $("lb").classList.add("open"); document.body.style.overflow = "hidden"; showLb(); $("lbClose").focus(); }
  function showLb() {
    var l = state.lbList, i = state.lbIndex, p = l[i]; if (!p) return; var c = catOf(p);
    var img = $("lbImg"), box = $("lbVid");
    if (!box) { box = document.createElement("div"); box.className = "lb-vid"; box.id = "lbVid"; box.hidden = true; img.after(box); }
    box.innerHTML = ""; box.hidden = !p.vid; img.hidden = !!p.vid;
    if (p.vid) {
      var v = p.vid, tall = p.h > p.w;
      box.classList.toggle("tall", tall);
      box.innerHTML = v.type === "file" ? '<video src="' + v.src + '" controls autoplay playsinline></video>'
        : '<iframe src="' + (v.type === "yt" ? "https://www.youtube-nocookie.com/embed/" + v.id + "?autoplay=1&rel=0&playsinline=1" : "https://player.vimeo.com/video/" + v.id + "?autoplay=1") +
          '" title="' + esc(titleOf(p)) + '" allow="autoplay; fullscreen; picture-in-picture; encrypted-media" allowfullscreen></iframe>';
    } else { img.classList.add("loading"); img.onload = function () { img.classList.remove("loading"); }; img.src = p.thumb; img.alt = titleOf(p);
    var full = new Image(); full.onload = function () { if (state.lbList[state.lbIndex] === p) img.src = full.src; }; full.src = p.full; }
    $("lbTitle").textContent = titleOf(p); $("lbMeta").textContent = [p.d || c.kind, p.y || (p.title ? c.label : "")].filter(Boolean).join(", ");
    var st = $("lbStrip"), cur = null;
    Array.prototype.forEach.call(st.children, function (b, k) { var on = k === i; b.setAttribute("aria-current", String(on)); if (on) cur = b; });
    if (cur) requestAnimationFrame(function () { st.scrollLeft = cur.offsetLeft - st.clientWidth / 2 + cur.clientWidth / 2; });
    $("lbCount").textContent = l.length > 1 ? (p.proj && l.every(function (x) { return x.proj === p.proj; }) ? "Projekt, " : "") + (i + 1) + " / " + l.length : "";
    $("lbPrev").style.visibility = $("lbNext").style.visibility = l.length > 1 ? "visible" : "hidden";
    if (l[i + 1] && l[i + 1].thumb) { var n = new Image(); n.src = l[i + 1].thumb; }
  }
  function stepLb(d) { var n = state.lbList.length; if (n < 2) return; state.lbIndex = (state.lbIndex + d + n) % n; showLb(); }
  function closeLb() { $("lbVid").innerHTML = ""; $("lb").classList.remove("open"); document.body.style.overflow = ""; if (state.lastFocus && state.lastFocus.focus) state.lastFocus.focus(); }
  $("lbStrip").addEventListener("click", function (e) { var b = e.target.closest("[data-i]"); if (!b) return; state.lbIndex = +b.dataset.i; showLb(); });
  $("lbClose").onclick = closeLb; $("lbPrev").onclick = function () { stepLb(-1); }; $("lbNext").onclick = function () { stepLb(1); };
  $("lb").addEventListener("click", function (e) { if (e.target.id === "lbStage") closeLb(); });
  document.addEventListener("keydown", function (e) {
    if (!$("lb").classList.contains("open")) return;
    if (e.key === "Escape") closeLb(); else if (e.key === "ArrowLeft") stepLb(-1); else if (e.key === "ArrowRight") stepLb(1);
    else if (e.key === "Tab") { var f = Array.prototype.filter.call($("lb").querySelectorAll("button"), function (x) { return x.offsetParent && x.style.visibility !== "hidden"; }); var k = f.indexOf(document.activeElement); e.preventDefault(); f[(k + (e.shiftKey ? -1 : 1) + f.length) % f.length].focus(); }
  });
  (function () {
    var x0 = null, y0 = 0, s = $("lbStage");
    s.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    s.addEventListener("touchend", function (e) { if (x0 === null) return; var dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0; if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) stepLb(dx < 0 ? 1 : -1); x0 = null; }, { passive: true });
  })();

  /* ---------- contact ---------- */
  function mailBody() { return "Dobrý den,\n\n" + $("fMsg").value.trim() + "\n\n" + $("fName").value.trim() + "\n" + $("fEmail").value.trim(); }
  $("fSend").onclick = function () {
    var err = $("fErr"), name = $("fName").value.trim(), mail = $("fEmail").value.trim(), msg = $("fMsg").value.trim(), bad = null;
    if (!name) bad = ["Vyplňte prosím své jméno.", "fName"];
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) bad = ["Zkontrolujte prosím e-mailovou adresu.", "fEmail"];
    else if (!msg) bad = ["Napište prosím pár slov o tom, co potřebujete.", "fMsg"];
    if (bad) { err.textContent = bad[0]; err.classList.add("show"); $(bad[1]).focus(); return; }
    err.classList.remove("show");
    var topic = $("fSubj").value.trim(), subj = (topic || "Poptávka") + " – " + name;
    $("fMail").href = "mailto:zajicekkuba@seznam.cz?subject=" + encodeURIComponent(subj) + "&body=" + encodeURIComponent(mailBody());
    $("form").classList.add("sent"); $("fMail").focus();
  };
  $("fBack").onclick = function () { $("form").classList.remove("sent"); $("fMsg").focus(); };
  $("fCopy").onclick = function () { if (navigator.clipboard) navigator.clipboard.writeText(mailBody()).then(function () { toast("Text zprávy je zkopírovaný."); }, function () { toast("Kopírování se nepovedlo, označte text ručně."); }); };

  /* ---------- reviews ---------- */
  var STAR = "M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z";
  function starsHTML(n) {
    var s = "";
    for (var i = 1; i <= 5; i++) s += '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"' + (i > n ? ' style="opacity:.2"' : "") + '><path d="' + STAR + '"></path></svg>';
    return '<span class="rev-stars" role="img" aria-label="Hodnocení ' + n + ' z 5">' + s + "</span>";
  }
  /* Jen křestní jméno a první písmeno příjmení: „Jakub Zajíček“ → „Jakub Z.“ */
  function shortName(n) { var w = String(n).trim().split(/\s+/).filter(Boolean); return w.length > 1 ? w[0] + " " + w[w.length - 1].charAt(0).toUpperCase() + "." : (w[0] || ""); }
  function initials(n) { return n.split(/\s+/).filter(Boolean).slice(0, 2).map(function (w) { return w.charAt(0).toUpperCase(); }).join(""); }
  function renderReviews() {
    var r = DATA.reviews || [], g = $("revGrid");
    g.hidden = !r.length;
    g.innerHTML = r.map(function (x) {
      x = { name: shortName(x.name), stars: x.stars, text: x.text };
      return '<figure class="rev"><blockquote>„' + esc(x.text) + '“</blockquote><figcaption><span class="rev-av" aria-hidden="true">' + esc(initials(x.name)) + "</span>" + starsHTML(x.stars) + "<b>" + esc(x.name) + "</b></figcaption></figure>";
    }).join("");
    $("revLead").textContent = r.length ? "Fotil jsem vás? Budu rád za pár slov." : "Zatím tu žádné recenze nejsou. Fotil jsem vás? Budete první.";
  }
  var rStars = 5;
  function paintStars() {
    $("rStars").innerHTML = [1, 2, 3, 4, 5].map(function (i) {
      return '<button type="button" role="radio" aria-checked="' + (i === rStars) + '" aria-label="' + i + " z 5" + '" data-v="' + i + '" class="' + (i <= rStars ? "on" : "") + '" tabindex="' + (i === rStars ? 0 : -1) + '"><svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="' + STAR + '"></path></svg></button>';
    }).join("");
  }
  paintStars();
  $("rStars").addEventListener("click", function (e) { var b = e.target.closest("[data-v]"); if (!b) return; rStars = +b.dataset.v; paintStars(); this.querySelector('[data-v="' + rStars + '"]').focus(); });
  $("rStars").addEventListener("keydown", function (e) {
    var d = (e.key === "ArrowRight" || e.key === "ArrowUp") ? 1 : (e.key === "ArrowLeft" || e.key === "ArrowDown") ? -1 : 0;
    if (!d) return; e.preventDefault(); rStars = Math.min(5, Math.max(1, rStars + d)); paintStars(); this.querySelector('[data-v="' + rStars + '"]').focus();
  });
  $("rOpen").onclick = function () { var f = $("rForm"), open = f.hidden; f.hidden = !open; this.setAttribute("aria-expanded", String(open)); if (open) $("rName").focus(); };
  function clean(s) { return s.replace(/\|/g, "/").replace(/\s+/g, " ").trim(); }
  function revBody() {
    var n = shortName($("rName").value), t = $("rText").value.trim();
    return "Dobrý den,\n\nposílám recenzi na web.\n\nJméno: " + n + "\nHodnocení: " + rStars + "/5\nRecenze: " + t +
      "\n\nSouhlasím se zveřejněním svého jména a recenze na webu atelierzajicek.cz.\n\n---\nŘádek pro recenze.txt:\n" + clean(n) + " | " + rStars + " | " + clean(t);
  }
  $("rSend").onclick = function () {
    var err = $("rErr"), bad = null;
    if (!$("rName").value.trim()) bad = ["Vyplňte prosím své jméno.", "rName"];
    else if ($("rText").value.trim().length < 10) bad = ["Napište prosím aspoň jednu větu.", "rText"];
    else if (!$("rOk").checked) bad = ["Pro zveřejnění je potřeba souhlas.", "rOk"];
    if (bad) { err.textContent = bad[0]; err.classList.add("show"); $(bad[1]).focus(); return; }
    err.classList.remove("show");
    $("rMail").href = "mailto:zajicekkuba@seznam.cz?subject=" + encodeURIComponent("Recenze na web – " + $("rName").value.trim()) + "&body=" + encodeURIComponent(revBody());
    $("rForm").classList.add("sent"); $("rMail").focus();
  };
  $("rBack").onclick = function () { $("rForm").classList.remove("sent"); $("rText").focus(); };
  $("rCopy").onclick = function () { if (navigator.clipboard) navigator.clipboard.writeText(revBody()).then(function () { toast("Text recenze je zkopírovaný."); }, function () { toast("Kopírování se nepovedlo, označte text ručně."); }); };

  /* ---------- typografie: jednopísmenná slova (a, i, k, o, s, u, v, z) nezůstanou na konci řádku ---------- */
  var ONE = /(^|[\s\u00A0(„"'])([AaIiKkOoSsUuVvZz])[ \t\n\r]+(?=\S)/g;
  function nbsp(root) {
    var w = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) { return n.parentNode.closest("script,style,textarea,pre,code,input") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; }
    }), n;
    while ((n = w.nextNode())) {
      var t = n.nodeValue, u = t.replace(ONE, "$1$2\u00A0").replace(ONE, "$1$2\u00A0");
      if (u !== t) n.nodeValue = u;
    }
  }

  /* ---------- start ---------- */
  /* ---------- menu: kategorie portfolia ---------- */
  function renderMenu() {
    var c = counts();
    $("ddMenu").innerHTML = '<a href="#portfolio" data-go="vse">Všechny práce</a>' + DATA.categories.filter(function (x) { return c[x.id]; }).map(function (x) {
      return '<a href="#' + x.id + '" data-go="' + x.id + '">' + esc(x.label) + "</a>";
    }).join("") + ((DATA.projects || []).length ? '<a href="#projekty" class="dd-proj">Projekty</a>' : "");
  }
  function goCat(id) {
    state.filter = id; state.view = "grid"; state.shown = PAGE;
    syncView(); renderFilters(); renderGrid(); nbsp($("grid"));
    $("portfolio").scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }
  function ddClose() { $("navDd").classList.remove("open"); $("ddBtn").setAttribute("aria-expanded", "false"); }
  $("ddBtn").onclick = function (e) { e.stopPropagation(); var open = !$("navDd").classList.contains("open"); $("navDd").classList.toggle("open", open); this.setAttribute("aria-expanded", String(open)); if (open) { var f = $("ddMenu").querySelector("a"); if (f) f.focus(); } };
  $("ddMenu").addEventListener("click", function (e) {
    if (e.target.closest(".dd-proj")) { ddClose(); return; }
    var a = e.target.closest("[data-go]"); if (!a) return;
    e.preventDefault(); ddClose(); a.blur();
    history.pushState(null, "", a.dataset.go === "vse" ? "#portfolio" : "#" + a.dataset.go);
    goCat(a.dataset.go);
  });
  document.addEventListener("click", function (e) { if (!e.target.closest("#navDd")) ddClose(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && $("navDd").classList.contains("open")) { ddClose(); $("ddBtn").focus(); } });
  function fromHash() { var h = decodeURIComponent(location.hash.slice(1)); if (h && CAT[h]) goCat(h); }
  window.addEventListener("hashchange", fromHash);

  /* ---------- tlačítko „Přeskočit portfolio“: ukáže se jen při procházení dlouhé galerie ---------- */
  var skipTick = false;
  function skipCheck() {
    skipTick = false;
    var sec = $("portfolio"), r = sec.getBoundingClientRect(), vh = window.innerHeight;
    var show = $("grid").offsetHeight > vh && r.top < vh * 0.25 && r.bottom > vh * 1.2;
    $("skipPf").classList.toggle("show", show);
    $("skipPf").tabIndex = show ? 0 : -1;
  }
  window.addEventListener("scroll", function () { if (!skipTick) { skipTick = true; requestAnimationFrame(skipCheck); } }, { passive: true });
  window.addEventListener("resize", skipCheck);

  /* ---------- projekty: karty odkazující na podstránky /projekty/<nazev>/ ---------- */
  function renderProjects() {
    var list = (DATA && DATA.projects) || [], sec = $("projekty");
    if (!sec) return;
    sec.hidden = !list.length;
    if ($("navProj")) $("navProj").hidden = !list.length;
    $("prGrid").innerHTML = list.map(function (p) {
      var meta = [p.field, p.year].filter(Boolean).join(" · ");
      return '<a class="pr-card" href="projekty/' + encodeURIComponent(p.id) + '/">' +
        '<span class="pr-img"><img src="' + esc(p.thumb) + '" width="' + p.tw + '" height="' + p.th + '" loading="lazy" decoding="async" alt=""></span>' +
        '<span class="pr-txt">' + (meta ? '<span class="pr-meta">' + esc(meta) + '</span>' : '') +
        '<b>' + esc(p.title) + '</b>' + (p.sub ? '<span class="pr-sub">' + esc(p.sub) + '</span>' : '') +
        '<span class="pr-go">Zobrazit projekt <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 7h8M7.5 3.5 11 7l-3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span></span></a>';
    }).join("");
  }

  var hashDone = false;
  function renderAll() {
    renderFilm(); renderFilters(); renderGrid(); renderReviews(); renderMenu(); renderProjects(); nbsp(document.body);
    if (!hashDone && DATA.categories.length) { hashDone = true; fromHash(); }
  }
  renderAll();
  fetch("gallery.json", { cache: "no-cache" }).then(function (r) { return r.json(); }).then(function (d) {
    DATA = d; CAT = {}; d.categories.forEach(function (c) { CAT[c.id] = c; }); renderAll();
  }).catch(function () { renderAll(); });
})();
