(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var PAGE = 24;
  var DATA = { categories: [], photos: [] };
  var CAT = {};
  var state = { view: "grid", filter: "vse", shown: PAGE, lbList: [], lbIndex: -1, lastFocus: null };

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function catOf(p) { return CAT[p.cat] || { label: p.cat, kind: "Fotografie" }; }
  function titleOf(p) { return p.title || catOf(p).label; }
  function toast(msg) { var t = $("toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(function () { t.classList.remove("show"); }, 3200); }

  /* ---------- filmstrip ---------- */
  function renderFilm() {
    var sec = $("filmSec"), film = $("film"), list = DATA.photos;
    if (list.length < 3) { sec.hidden = true; return; }
    var pick = list.slice(0, 14);
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
  var PAT_D = [[{ c: 1, s: 2 }, { c: 6, s: 2, a: "end" }, { c: 11, s: 2, a: "center" }], [{ c: 3, s: 3 }, { c: 8, s: 3, a: "center" }], [{ c: 1, s: 2, a: "center" }, { c: 5, s: 3 }, { c: 10, s: 2, a: "end" }], [{ c: 2, s: 3, a: "end" }, { c: 7, s: 2 }, { c: 11, s: 2, a: "center" }]];
  var PAT_M = [[{ c: 1, s: 2 }, { c: 4, s: 2, a: "center" }, { c: 7, s: 2 }], [{ c: 2, s: 2 }, { c: 5, s: 3, a: "center" }], [{ c: 1, s: 3, a: "center" }, { c: 6, s: 3 }], [{ c: 2, s: 3 }, { c: 6, s: 2, a: "end" }]];
  function scatterHTML(vis) {
    var mob = MQ.matches, P = mob ? PAT_M : PAT_D, cols = mob ? 8 : 12, out = "", i = 0, r = 0;
    while (i < vis.length) {
      var pat = P[r % P.length], row = "";
      pat.forEach(function (slot, k) {
        if (i >= vis.length) return;
        var p = vis[i], sp = slot.s, nextC = (pat[k + 1] || { c: cols + 1 }).c;
        if (p.tw > p.th * 1.15 && slot.c + sp + 1 <= nextC) sp++;
        row += '<button type="button" class="j" data-open="' + i + '" style="grid-column:' + slot.c + " / span " + sp + ";align-self:" + (slot.a || "start") + '" aria-label="Otevřít: ' + esc(titleOf(p)) + '">' +
          '<img src="' + p.thumb + '" alt="' + esc(titleOf(p)) + '" width="' + p.tw + '" height="' + p.th + '" loading="lazy" decoding="async"></button>';
        i++;
      });
      out += '<div class="srow" style="grid-template-columns:repeat(' + cols + ',minmax(0,1fr))">' + row + "</div>"; r++;
    }
    return out;
  }
  function renderGrid() {
    var g = $("grid"), m = $("more");
    if (!DATA.photos.length) { g.className = ""; g.innerHTML = '<div class="empty">Galerie se právě připravuje. Ukázky práce rád pošlu e-mailem.</div>'; m.innerHTML = ""; return; }
    if (state.view === "list") {
      var c = counts(); g.className = "catlist"; m.innerHTML = "";
      g.innerHTML = DATA.categories.filter(function (x) { return c[x.id]; }).map(function (x) {
        var cover = DATA.photos.filter(function (p) { return p.cat === x.id; })[0];
        return '<button type="button" class="cat-row" data-cat="' + x.id + '"><span class="cat-name">' + esc(x.label) + '</span><span class="cat-n">' + c[x.id] + '</span><img class="cat-cover" src="' + cover.thumb + '" alt="" loading="lazy"></button>';
      }).join("");
      return;
    }
    var list = filtered(), vis = list.slice(0, state.shown);
    g.className = "scatter"; g.innerHTML = scatterHTML(vis);
    m.innerHTML = '<span>Zobrazeno ' + vis.length + " z " + list.length + "</span>" + (vis.length < list.length ? '<button type="button" class="btn btn-ghost btn-small" id="moreBtn">Načíst další</button>' : "");
    var mb = $("moreBtn"); if (mb) mb.onclick = function () { state.shown += PAGE; renderGrid(); };
  }
  function syncView() { Array.prototype.forEach.call($("viewtog").children, function (b) { b.setAttribute("aria-pressed", String(b.dataset.v === state.view)); }); }
  $("viewtog").addEventListener("click", function (e) { var b = e.target.closest("[data-v]"); if (!b) return; state.view = b.dataset.v; if (state.view === "list") state.filter = "vse"; syncView(); renderFilters(); renderGrid(); });
  $("filters").addEventListener("click", function (e) { var b = e.target.closest("[data-f]"); if (!b) return; state.filter = b.dataset.f; state.shown = PAGE; renderFilters(); renderGrid(); });
  $("grid").addEventListener("click", function (e) {
    var cr = e.target.closest("[data-cat]");
    if (cr) { state.filter = cr.dataset.cat; state.view = "grid"; state.shown = PAGE; syncView(); renderFilters(); renderGrid(); $("portfolio").scrollIntoView(); return; }
    var o = e.target.closest("[data-open]"); if (o) openFrom(filtered(), +o.dataset.open);
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
    st.innerHTML = l.length < 2 ? "" : l.map(function (p, k) { return '<button type="button" class="lb-th" data-i="' + k + '" aria-label="Fotka ' + (k + 1) + ": " + esc(titleOf(p)) + '"><img src="' + p.thumb + '" alt="" width="' + p.tw + '" height="' + p.th + '" loading="lazy"></button>'; }).join("");
  }
  function openLb(list, i) { state.lbList = list; state.lbIndex = i; renderStrip(); state.lastFocus = document.activeElement; $("lb").classList.add("open"); document.body.style.overflow = "hidden"; showLb(); $("lbClose").focus(); }
  function showLb() {
    var l = state.lbList, i = state.lbIndex, p = l[i]; if (!p) return; var c = catOf(p);
    var img = $("lbImg"); img.classList.add("loading"); img.onload = function () { img.classList.remove("loading"); }; img.src = p.thumb; img.alt = titleOf(p);
    var full = new Image(); full.onload = function () { if (state.lbList[state.lbIndex] === p) img.src = full.src; }; full.src = p.full;
    $("lbTitle").textContent = titleOf(p); $("lbMeta").textContent = p.title ? c.kind + ", " + c.label : c.kind;
    var st = $("lbStrip"), cur = null;
    Array.prototype.forEach.call(st.children, function (b, k) { var on = k === i; b.setAttribute("aria-current", String(on)); if (on) cur = b; });
    if (cur) requestAnimationFrame(function () { st.scrollLeft = cur.offsetLeft - st.clientWidth / 2 + cur.clientWidth / 2; });
    $("lbCount").textContent = l.length > 1 ? (p.proj && l.every(function (x) { return x.proj === p.proj; }) ? "Projekt, " : "") + (i + 1) + " / " + l.length : "";
    $("lbPrev").style.visibility = $("lbNext").style.visibility = l.length > 1 ? "visible" : "hidden";
    if (l[i + 1]) { var n = new Image(); n.src = l[i + 1].thumb; }
  }
  function stepLb(d) { var n = state.lbList.length; if (n < 2) return; state.lbIndex = (state.lbIndex + d + n) % n; showLb(); }
  function closeLb() { $("lb").classList.remove("open"); document.body.style.overflow = ""; if (state.lastFocus && state.lastFocus.focus) state.lastFocus.focus(); }
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
  var topic = "";
  $("topics").addEventListener("click", function (e) { var b = e.target.closest(".chip"); if (!b) return; var on = b.getAttribute("aria-pressed") !== "true"; Array.prototype.forEach.call(this.children, function (x) { x.setAttribute("aria-pressed", "false"); }); b.setAttribute("aria-pressed", String(on)); topic = on ? b.textContent : ""; });
  function mailBody() { return "Dobrý den,\n\n" + $("fMsg").value.trim() + "\n\n" + $("fName").value.trim() + "\n" + $("fEmail").value.trim(); }
  $("fSend").onclick = function () {
    var err = $("fErr"), name = $("fName").value.trim(), mail = $("fEmail").value.trim(), msg = $("fMsg").value.trim(), bad = null;
    if (!name) bad = ["Vyplňte prosím své jméno.", "fName"];
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) bad = ["Zkontrolujte prosím e-mailovou adresu.", "fEmail"];
    else if (!msg) bad = ["Napište prosím pár slov o tom, co potřebujete.", "fMsg"];
    if (bad) { err.textContent = bad[0]; err.classList.add("show"); $(bad[1]).focus(); return; }
    err.classList.remove("show");
    var subj = "Poptávka" + (topic ? ": " + topic : "") + " – " + name;
    $("fMail").href = "mailto:zajicekkuba@seznam.cz?subject=" + encodeURIComponent(subj) + "&body=" + encodeURIComponent(mailBody());
    $("form").classList.add("sent"); $("fMail").focus();
  };
  $("fBack").onclick = function () { $("form").classList.remove("sent"); $("fMsg").focus(); };
  $("fCopy").onclick = function () { if (navigator.clipboard) navigator.clipboard.writeText(mailBody()).then(function () { toast("Text zprávy je zkopírovaný."); }, function () { toast("Kopírování se nepovedlo, označte text ručně."); }); };

  /* ---------- start ---------- */
  function renderAll() { renderFilm(); renderFilters(); renderGrid(); }
  renderAll();
  fetch("gallery.json", { cache: "no-cache" }).then(function (r) { return r.json(); }).then(function (d) {
    DATA = d; CAT = {}; d.categories.forEach(function (c) { CAT[c.id] = c; }); renderAll();
  }).catch(function () { renderAll(); });
})();
