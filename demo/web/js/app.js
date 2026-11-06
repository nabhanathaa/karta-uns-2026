/* SORA · Dashboard pemangku kebijakan (DLH Kota Surakarta, PLTSa Putri Cempo).
   Rumus, ambang, dan nama mengikuti aplikasi petugas (karta-mobile: lib/triage.ts, lib/karta)
   dan lampiran laporan Bab 3. Setiap halaman dirancang muat dalam satu layar. */
(() => {
'use strict';

// ------------------------------------------------------------------ konstanta (sama dengan aplikasi HP)
const RUTE = {
  U: { nama: 'Gasifikasi', lengkap: 'Umpan gasifikasi langsung', tujuan: 'Reaktor gasifikasi (Zona U)', warna: '#2865e8' },
  B: { nama: 'Bio-drying', lengkap: 'Pengeringan dengan serbuk kayu', tujuan: 'Bak bio-drying (Zona B)', warna: '#b56308' },
  M: { nama: 'Maggot & kompos', lengkap: 'Biokonversi organik basah', tujuan: 'Unit maggot BSF & kompos (Zona M)', warna: '#078879' },
  R: { nama: 'Residu', lengkap: 'Ditahan atau residu', tujuan: 'Area residu (Zona R)', warna: '#5b6577' },
};
const RK = ['U', 'B', 'M', 'R'];
const FR = [
  { k: 'org', n: 'Organik basah', c: '#11a792' }, { k: 'pla', n: 'Plastik', c: '#527df0' },
  { k: 'ker', n: 'Kertas dan kardus', c: '#e7b34b' }, { k: 'tek', n: 'Tekstil', c: '#b09be8' },
  { k: 'kay', n: 'Kayu dan ranting', c: '#b88963' }, { k: 'ine', n: 'Inert', c: '#9ba8ba' },
];
const JENIS = { pasar: 'Pasar', permukiman: 'Permukiman', ruang_publik: 'Ruang publik', lainnya: 'Lainnya' };
const AMBANG = { inert: 20, airUmpan: 20, airMaggot: 60, organikMaggot: 60, plastikMaggot: 5, airBioDrying: 65 };
const EFISIENSI_LISTRIK = 0.2;
const AKUN = [
  { u: 'kepala.dlh', nama: 'Kepala DLH', peran: 'DLH Kota Surakarta', av: 'KD' },
  { u: 'direksi.pltsa', nama: 'Direksi PLTSa', peran: 'PLTSa Putri Cempo', av: 'DP' },
  { u: 'analis', nama: 'Analis Data', peran: 'Bidang Pengelolaan Sampah', av: 'AD' },
];
const SANDI_DEMO = 'sora2026';
const FONT = "'Plus Jakarta Sans',system-ui,sans-serif";
const INK = '#2a3654', MUTED = '#5f6c86', GRID = '#eef1f7';

// ------------------------------------------------------------------ util
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const nf = (d = 0) => new Intl.NumberFormat('id-ID', { minimumFractionDigits: d, maximumFractionDigits: d });
const f0 = v => nf(0).format(v), f1 = v => nf(1).format(v), f2 = v => nf(2).format(v);
const sum = (a, g = x => x) => a.reduce((s, x) => s + (+g(x) || 0), 0);
const wavg = (a, g, w = x => x.ton) => { const W = sum(a, w); return W ? sum(a, x => g(x) * w(x)) / W : 0; };
const groupBy = (a, g) => a.reduce((m, x) => ((m[g(x)] ||= []).push(x), m), {});
const tgl = t => t.slice(0, 10);
const hariID = d => new Date(d + 'T12:00').toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
const tglPanjang = d => new Date(d + 'T12:00').toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' });
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ico = (id, cls = 'ico') => `<svg class="${cls}"><use href="#i-${id}"/></svg>`;
const rb = r => `<span class="rb" style="--c:${RUTE[r].warna}"><i>${r}</i>${RUTE[r].nama}</span>`;
const store = {
  get(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch { return def; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* penyimpanan tidak tersedia */ } },
};
const sesi = {
  get() { try { return JSON.parse(sessionStorage.getItem('sora-sesi') || 'null'); } catch { return null; } },
  set(v) { try { v ? sessionStorage.setItem('sora-sesi', JSON.stringify(v)) : sessionStorage.removeItem('sora-sesi'); } catch { /* abaikan */ } },
};
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.remove('show'), 2600); }
function countUp(root = document) {
  $$('[data-count]', root).forEach(el => {
    const end = +el.dataset.count, d = +(el.dataset.dec || 0), t0 = performance.now(), dur = 850;
    const step = now => { const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3); el.textContent = nf(d).format(end * e); if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  });
}
function geserHari(d, n) { const x = new Date(d + 'T12:00'); x.setDate(x.getDate() + n); return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`; }
function rentangHari(dari, sampai) { const out = []; for (let d = dari; d <= sampai; d = geserHari(d, 1)) out.push(d); return out; }
// Waktu dari HP berformat ISO UTC (akhiran Z). Ditampilkan dalam WIB, apa pun zona waktu peramban.
function waktuWIB(s) {
  s = String(s || '').trim();
  const m = s.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/);
  if (m && !/(Z|[+-]\d{2}:?\d{2})$/i.test(s)) return `${m[1]}T${m[2]}`;
  const t = new Date(s);
  return isNaN(t) ? null : new Date(t.getTime() + 7 * 3600e3).toISOString().slice(0, 16);
}

// ------------------------------------------------------------------ data
const S = { data: null, semua: [], tps: [], tpsBy: {}, impor: store.get('sora-impor', []), charts: [], maps: [], timers: [], obs: [] };
const G = { hari: 30, jenis: 'semua' };

function siapkanData(d) { S.data = d; gabungImpor(); }
function gabungImpor() {
  S.tps = S.data.tps.slice();
  S.tpsBy = Object.fromEntries(S.tps.map(t => [t.kode, t]));
  S.impor.forEach(m => { if (!S.tpsBy[m.tps]) { const t = { kode: m.tps, nama: m.tpsNama || m.tps, kecamatan: '-', tipe: m.tipe || 'lainnya', lat: null, lon: null }; S.tps.push(t); S.tpsBy[t.kode] = t; } });
  S.semua = S.data.muatan.concat(S.impor).sort((a, b) => a.t < b.t ? -1 : 1);
  const b = $('#navImport'); if (b) { b.hidden = !S.impor.length; b.textContent = S.impor.length; }
}
const tanggalAkhir = () => tgl(S.semua[S.semua.length - 1].t);
const tanggalAwal = () => tgl(S.semua[0].t);
const periode = () => { const akhir = tanggalAkhir(); return { dari: geserHari(akhir, -(G.hari - 1)), sampai: akhir }; };
function saring(f = {}) {
  return S.semua.filter(m => (!f.tps || f.tps === 'semua' || m.tps === f.tps)
    && (!f.jenis || f.jenis === 'semua' || (S.tpsBy[m.tps]?.tipe === f.jenis))
    && (!f.rute || f.rute === 'semua' || m.rute === f.rute)
    && (!f.dari || tgl(m.t) >= f.dari) && (!f.sampai || tgl(m.t) <= f.sampai)
    && (!f.q || (m.id + ' ' + m.pelat + ' ' + (S.tpsBy[m.tps]?.nama || '')).toLowerCase().includes(f.q.toLowerCase())));
}
const dataGlobal = (extra = {}) => saring(Object.assign({}, periode(), { jenis: G.jenis }, extra));
function ringkas(a) {
  const ton = sum(a, x => x.ton), byR = Object.fromEntries(RK.map(r => [r, sum(a.filter(x => x.rute === r), x => x.ton)]));
  const nR = Object.fromEntries(RK.map(r => [r, a.filter(x => x.rute === r).length]));
  const pct = r => ton ? byR[r] / ton * 100 : 0;
  return { n: new Set(a.map(x => x.muatan || x.id)).size, baris: a.length, ton, w: wavg(a, x => x.w), lhv: wavg(a, x => x.lhv), byR, nR,
    pU: pct('U'), pB: pct('B'), pM: pct('M'), pR: pct('R'), cek: a.filter(x => x.cek).length, ...Object.fromEntries(FR.map(x => [x.k, wavg(a, m => m[x.k])])) };
}
function perTps(a) {
  const g = groupBy(a, x => x.tps);
  return Object.entries(g).map(([k, v]) => ({ t: S.tpsBy[k], ...ringkas(v), rows: v })).sort((x, y) => y.ton - x.ton);
}
// Aturan mana yang menentukan rute (urutan sama dengan recommend() di aplikasi HP).
function aturanKe(m) {
  if (m.ine >= AMBANG.inert) return 1;
  if (m.wa <= AMBANG.airUmpan) return 2;
  if (m.w >= AMBANG.airMaggot && m.org >= AMBANG.organikMaggot && m.pla <= AMBANG.plastikMaggot) return 3;
  if (m.w < AMBANG.airBioDrying) return 4;
  return 5;
}
const serbukKayu = a => sum(a.filter(m => m.rute === 'B'), m => m.ton * m.dosis / 100);
const airDiuapkan = a => sum(a.filter(m => m.rute === 'B' && m.w > 20), m => m.ton * (m.w - 20) / 80);
const listrikU = a => sum(a.filter(m => m.rute === 'U'), m => m.ton * Math.max(0, m.lhv) * 1000 * EFISIENSI_LISTRIK / 3.6) / 1000;

// ------------------------------------------------------------------ grafik
const TT = { backgroundColor: '#0c1d45', borderWidth: 0, padding: [9, 12], textStyle: { color: '#fff', fontFamily: FONT, fontSize: 12.5 }, extraCssText: 'border-radius:10px;box-shadow:0 10px 30px #0c1d4540' };
function chart(el, opt) {
  const c = echarts.init(el, null, { renderer: 'canvas' });
  c.setOption(Object.assign({
    textStyle: { fontFamily: FONT, color: INK }, animationDuration: 800, animationEasing: 'cubicOut',
    tooltip: Object.assign({ trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: '#2762e80d' } } }, TT),
    grid: { left: 6, right: 14, top: 36, bottom: 4, containLabel: true },
    legend: { top: 0, left: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10, itemGap: 12, textStyle: { fontSize: 12, color: MUTED } },
  }, opt));
  S.charts.push(c);
  const ro = new ResizeObserver(() => c.resize()); ro.observe(el); S.obs.push(ro);
  return c;
}
const axisCat = (data, extra = {}) => Object.assign({ type: 'category', data, axisLine: { lineStyle: { color: '#d7deeb' } }, axisTick: { show: false }, axisLabel: { color: MUTED, fontSize: 11.5 } }, extra);
const axisVal = (name, extra = {}) => Object.assign({ type: 'value', name, nameGap: 8, nameTextStyle: { color: '#8a96ad', fontSize: 11, align: 'left' }, splitLine: { lineStyle: { color: GRID } }, axisLabel: { color: MUTED, fontSize: 11.5 } }, extra);
function bersihkan() {
  S.charts.forEach(c => c.dispose()); S.charts = [];
  S.obs.forEach(o => o.disconnect()); S.obs = [];
  S.maps.forEach(m => { try { m.stop(); m.off(); m.remove(); } catch (e) { /* peta sudah dilepas */ } }); S.maps = [];
  S.timers.forEach(clearInterval); S.timers = [];
}

// ------------------------------------------------------------------ potongan tampilan
const ph = (judul, sub = '', tags = []) => `<div class="ph"><div><h3>${judul}</h3>${sub ? `<p>${sub}</p>` : ''}</div>${tags.length ? `<div class="tags">${tags.map(t => `<span class="tag${t.startsWith('!') ? ' gold' : ''}">${t.replace('!', '')}</span>`).join('')}</div>` : ''}</div>`;
function kpi({ k, icon, v, dec = 0, unit = '', f = '', accent = 'var(--blue)', title = '' }) {
  return `<div class="kpi" style="--accent:${accent}"${title ? ` title="${esc(title)}"` : ''}><div class="k">${ico(icon)}${k}</div>
    <div class="v num"><span data-count="${v}" data-dec="${dec}">0</span>${unit ? `<small>${unit}</small>` : ''}</div><div class="f">${f}</div></div>`;
}
const komposisiStack = m => `<span class="stack">${FR.map(x => `<i style="width:${m[x.k]}%;background:${x.c}" title="${x.n} ${f1(m[x.k])}%"></i>`).join('')}</span>`;
const pilihanTps = (pilih = 'semua', semua = 'Semua TPS') => `<option value="semua">${semua}</option>` + S.tps.slice().sort((a, b) => a.nama.localeCompare(b.nama)).map(t => `<option value="${t.kode}"${t.kode === pilih ? ' selected' : ''}>${esc(t.nama)}</option>`).join('');
const pilihanRute = (pilih = 'semua') => `<option value="semua">Semua rute</option>` + RK.map(r => `<option value="${r}"${r === pilih ? ' selected' : ''}>${r} · ${RUTE[r].nama}</option>`).join('');
const labelPeriode = () => { const p = periode(); return `${hariID(p.dari)} – ${hariID(p.sampai)} ${p.sampai.slice(0, 4)}`; };
const labelJenis = () => G.jenis === 'semua' ? 'semua jenis TPS' : `TPS ${JENIS[G.jenis].toLowerCase()}`;

// ------------------------------------------------------------------ peta
const IND = {
  w: { nama: 'Kadar air rata-rata', unit: '%', batas: [45, 52, 58], warna: ['#1f9d74', '#8cc152', '#f0a43a', '#d0473f'], g: r => r.w, dec: 1, arah: 'buruk', ket: 'Merah = paling basah, perlu pengeringan atau maggot.' },
  pR: { nama: 'Porsi ke Rute R', unit: '%', batas: [8, 15, 25], warna: ['#1f9d74', '#8cc152', '#f0a43a', '#d0473f'], g: r => r.pR, dec: 1, arah: 'buruk', ket: 'Merah = banyak inert atau campuran, perlu pembinaan pemilahan.' },
  lhv: { nama: 'Nilai kalor (LHV)', unit: 'MJ/kg', batas: [5, 6, 7], warna: ['#d0473f', '#f0a43a', '#8cc152', '#1f9d74'], g: r => r.lhv, dec: 2, arah: 'baik', ket: 'Hijau = energi per kg paling tinggi.' },
  org: { nama: 'Porsi organik basah', unit: '%', batas: [50, 60, 70], warna: ['#cdeee6', '#7fd3bf', '#2fae92', '#0b7a66'], g: r => r.org, dec: 1, arah: 'netral', ket: 'Makin gelap, makin cocok untuk maggot dan kompos.' },
  ton: { nama: 'Tonase', unit: 'ton', batas: null, warna: ['#c9d8fb', '#88a8f2', '#4777e6', '#1f3f9a'], g: r => r.ton, dec: 0, arah: 'netral', ket: 'Makin gelap, makin banyak sampah dikirim.' },
};
function batasInd(I, rows) {
  if (I.batas) return I.batas;
  const v = rows.map(I.g).sort((x, y) => x - y), q = p => v[Math.floor((v.length - 1) * p)] || 0;
  return [q(.25), q(.5), q(.75)];
}
const fmtInd = (I, v) => (I.dec === 2 ? f2(v) : I.dec === 1 ? f1(v) : f0(v)) + (I.unit === '%' ? '%' : ' ' + I.unit);
function legendaInd(I, batas) {
  return batas.map((b, i) => i === 0 ? `< ${f0(b)}` : `${f0(batas[i - 1])}–${f0(b)}`).concat([`≥ ${f0(batas[2])}`]).map(s => s + (I.unit === '%' ? '%' : ' ' + I.unit));
}
function buatPeta(el) {
  const map = L.map(el, { zoomControl: false, attributionControl: true, scrollWheelZoom: true, zoomSnap: .25 });
  S.maps.push(map);
  L.control.zoom({ position: 'topleft' }).addTo(map);
  const esriAbu = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', { maxNativeZoom: 16, maxZoom: 19, attribution: 'Peta dasar © Esri' });
  const esriLabel = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', { maxNativeZoom: 16, maxZoom: 19 });
  const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap kontributor' });
  const citra = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19, attribution: 'Citra © Esri, Maxar' });
  const abu = L.layerGroup([esriAbu, esriLabel]).addTo(map);
  // Bila ubin Esri gagal dimuat, beralih otomatis ke OpenStreetMap.
  let gagal = 0, ada = false;
  esriAbu.on('tileload', () => { ada = true; });
  esriAbu.on('tileerror', () => { if (!ada && ++gagal === 6 && map.hasLayer(abu)) { map.removeLayer(abu); osm.addTo(map); } });
  L.control.layers({ 'Peta abu-abu': abu, 'OpenStreetMap': osm, 'Citra satelit': citra }, null, { position: 'topleft' }).addTo(map);
  map.attributionControl.setPrefix(false);
  const P = S.data.pltsa;
  L.marker([P.lat, P.lon], { icon: L.divIcon({ className: '', html: '<div class="pltsa-pin">PLTSa</div>', iconSize: [46, 46], iconAnchor: [23, 23] }), zIndexOffset: 1000 })
    .addTo(map).bindPopup(`<div class="pop"><h4>${esc(P.nama)}</h4><div class="meta">${esc(P.alamat)}</div>Titik penerimaan semua muatan. Reaktor gasifikasi menerima umpan dengan batas atas kadar air paling tinggi 20%.</div>`);
  const ro = new ResizeObserver(() => map.invalidateSize()); ro.observe(el); S.obs.push(ro);
  return map;
}
function pasPeta(map, kecil) {
  if (!S.maps.includes(map)) return;
  const P = S.data.pltsa, titik = S.data.tps.map(t => [t.lat, t.lon]).concat([[P.lat, P.lon]]);
  map.invalidateSize();
  map.fitBounds(L.latLngBounds(titik), { paddingTopLeft: kecil ? [50, 30] : [60, 40], paddingBottomRight: kecil ? [30, 30] : [230, 40], maxZoom: 14 });
}
function lapisTps(map, layer, rows, I, { alur = true, label = false, pilih } = {}) {
  layer.clearLayers();
  const P = S.data.pltsa, batas = batasInd(I, rows), kelas = v => v < batas[0] ? 0 : v < batas[1] ? 1 : v < batas[2] ? 2 : 3;
  const maxTon = Math.max(1, ...rows.map(r => r.ton)), marker = {};
  rows.filter(r => r.t && r.t.lat != null).forEach(r => {
    const c = I.warna[kelas(I.g(r))], rad = 7 + 12 * Math.sqrt(r.ton / maxTon);
    if (alur) L.polyline([[r.t.lat, r.t.lon], [P.lat, P.lon]], { color: c, weight: 2.2, opacity: .7, className: 'flow', interactive: false }).addTo(layer);
    L.circleMarker([r.t.lat, r.t.lon], { radius: rad + 6, stroke: false, fillColor: c, fillOpacity: .18, interactive: false }).addTo(layer);
    const mk = L.circleMarker([r.t.lat, r.t.lon], { radius: rad, color: '#fff', weight: 2.5, fillColor: c, fillOpacity: .95 }).addTo(layer);
    mk.bindPopup(`<div class="pop"><h4>${esc(r.t.nama)}</h4><div class="meta">${JENIS[r.t.tipe] || ''} · Kec. ${esc(r.t.kecamatan)} · ${f1(r.t.jarak_km)} km ke PLTSa</div>
      <div class="kv"><span>Muatan</span><b>${f0(r.n)}</b><span>Tonase</span><b>${f1(r.ton)} ton</b><span>Kadar air rata-rata</span><b>${f1(r.w)}%</b><span>Nilai kalor</span><b>${f2(r.lhv)} MJ/kg</b><span>Ke Rute R</span><b>${f1(r.pR)}%</b></div>
      ${komposisiStack(r)}<div class="legend-inline">${FR.map(x => `<span><i style="background:${x.c}"></i>${x.n} ${f0(r[x.k])}%</span>`).join('')}</div></div>`, { maxWidth: 300 });
    mk.bindTooltip(r.t.nama.replace('TPS ', ''), { permanent: label, direction: 'top', offset: [0, -rad], className: 'tlabel' });
    if (pilih) mk.on('click', () => pilih(r.t.kode));
    marker[r.t.kode] = mk;
  });
  return { marker, batas };
}

// ------------------------------------------------------------------ halaman
const PAGES = {};
const JUDUL = { ringkasan: 'Ringkasan', peta: 'Peta TPS', muatan: 'Muatan masuk', komposisi: 'Komposisi', rute: 'Rute dan neraca', model: 'Model dan validasi', laporan: 'Laporan' };

// ----- Ringkasan
PAGES.ringkasan = el => {
  const a = dataGlobal(), r = ringkas(a);
  el.innerHTML = `
  <div class="kpis" style="--i:0">
    ${kpi({ k: 'Muatan dianalisis', icon: 'truck', v: r.n, f: `<b>${f0(r.ton)} ton</b> dari ${perTps(a).length} TPS` })}
    ${kpi({ k: 'Kadar air rata-rata', icon: 'drop', v: r.w, dec: 1, unit: '%', accent: '#078879', f: 'Batas umpan reaktor <b>≤ 20%</b>' })}
    ${kpi({ k: 'Nilai kalor (LHV)', icon: 'zap', v: r.lhv, dec: 2, unit: 'MJ/kg', accent: '#c9973f', f: `Setara <b>${f0(r.lhv * 1000 * EFISIENSI_LISTRIK / 3.6)} kWh</b> listrik per ton` })}
    ${kpi({ k: 'Langsung jadi umpan', icon: 'check', v: r.pU, dec: 1, unit: '%', accent: RUTE.U.warna, f: `Rute U · <b>${f1(r.byR.U)} ton</b>` })}
    ${kpi({ k: 'Ditahan (Rute R)', icon: 'alert', v: r.pR, dec: 1, unit: '%', accent: RUTE.R.warna, f: `<b>${f0(r.byR.R)} ton</b> · ${f0(r.nR.R)} muatan` })}
  </div>
  <div class="main" style="--i:1">
    <div class="panel">${ph('Asal muatan dan kadar air per TPS', 'Warna = kadar air rata-rata, ukuran = tonase, garis = alur ke PLTSa. Klik titik untuk rincian.', ['Geospasial'])}
      <div class="mapbox"><div class="lmap" id="rMap"></div><div class="mfloat mlegend" id="rLeg"></div></div></div>
    <div class="col right">
      <div class="panel" style="--i:2">${ph('Temuan utama', `${labelPeriode()} · ${labelJenis()}`, ['!Cerita data'])}<div class="findings scroll" id="rFind"></div>
        <div class="howto"><b>Cara membaca.</b> Data simulasi 12 TPS dengan rumus dan aturan rute yang sama dengan aplikasi petugas. Ganti periode dan jenis TPS di bagian atas.</div></div>
      <div class="panel" style="--i:3">${ph('Ke mana sampah pergi', 'Tonase dan porsi setiap rute pengolahan', ['Keputusan'])}<div class="routes" id="rRute"></div></div>
    </div>
  </div>`;
  countUp(el);
  const jenis = groupBy(a, m => S.tpsBy[m.tps]?.tipe || 'lainnya'), wJ = Object.fromEntries(Object.entries(jenis).map(([k, v]) => [k, ringkas(v)]));
  const tpsR = perTps(a).filter(x => x.n >= 3).sort((x, y) => y.pR - x.pR)[0];
  const hujan = a.filter(m => m.r24 >= 10), kering = a.filter(m => m.r24 < 1);
  const temuan = [
    `<b>Sebagian besar sampah terlalu basah untuk reaktor.</b> Hanya <span class="hl-b">${f1(r.pU)}%</span> tonase yang batas atas kadar airnya ≤ 20%. Sebanyak <span class="hl-a">${f1(r.pB)}%</span> perlu bio-drying dengan serbuk kayu sekitar <b>${f0(serbukKayu(a))} ton</b>.`,
  ];
  if (wJ.pasar && wJ.permukiman) temuan.push(`<b>Sampah pasar paling basah.</b> Rata-rata <b>${f1(wJ.pasar.w)}%</b> air, ${f1(wJ.pasar.w - wJ.permukiman.w)} poin di atas permukiman. <span class="hl-g">${f1(wJ.pasar.pM)}%</span> tonase pasar cocok untuk maggot dan kompos.`);
  if (tpsR) temuan.push(`<b>${esc(tpsR.t.nama)}</b> paling banyak ditahan: <span class="hl-r">${f1(tpsR.pR)}%</span> tonasenya masuk Rute R. Prioritas pembinaan pemilahan di sumber.`);
  if (hujan.length >= 5 && kering.length >= 5) temuan.push(`<b>Hujan menaikkan kadar air.</b> Muatan pada hari hujan ≥ 10 mm rata-rata <b>${f1(wavg(hujan, m => m.w))}%</b> air, dibanding <b>${f1(wavg(kering, m => m.w))}%</b> pada hari tanpa hujan.`);
  const mB = a.filter(m => m.rute === 'B' && m.w < 100);
  if (mB.length >= 5) {
    // LHV kering diturunkan dari LHV basah: LHV_k = (LHV + 2,443 w) / (1 − w), lalu dihitung ulang pada w = 20%.
    const lhv20 = wavg(mB, m => { const w = m.w / 100; return 0.8 * (m.lhv + 2.443 * w) / (1 - w) - 2.443 * 0.2; });
    temuan.push(`<b>Pengeringan menaikkan nilai kalor.</b> Muatan Rute B kini rata-rata <b>${f2(wavg(mB, m => m.lhv))} MJ/kg</b>. Bila kadar airnya turun ke 20%, nilainya naik menjadi sekitar <span class="hl-b">${f2(lhv20)} MJ/kg</span>.`);
  }
  const cek = a.filter(m => m.cek);
  if (cek.length) { const top = Object.entries(groupBy(cek, m => m.tps)).sort((x, y) => y[1].length - x[1].length)[0];
    temuan.push(`<b>${f0(cek.length)} muatan perlu cek manual</b> karena hasil pindaian kurang meyakinkan, misalnya gambar sulit dikenali atau komposisi antarframe berubah besar. Terbanyak dari <b>${esc(S.tpsBy[top[0]]?.nama || top[0])}</b> (${f0(top[1].length)} muatan).`); }
  $('#rFind').innerHTML = temuan.slice(0, 6).map((t, i) => `<div class="finding"><span class="n">${i + 1}</span><p>${t}</p></div>`).join('');
  const map = buatPeta($('#rMap')), lyr = L.layerGroup().addTo(map), I = IND.w;
  const { batas } = lapisTps(map, lyr, perTps(a), I);
  $('#rLeg').innerHTML = `<h5>Kadar air rata-rata</h5>${legendaInd(I, batas).map((l, i) => `<div class="row"><span class="sw" style="background:${I.warna[i]}"></span>${l}</div>`).join('')}`;
  setTimeout(() => pasPeta(map, true), 60);
  $('#rRute').innerHTML = RK.map(k => { const pc = r.ton ? r.byR[k] / r.ton * 100 : 0; return `<div class="route-row" style="--c:${RUTE[k].warna}" title="${RUTE[k].lengkap} · ${RUTE[k].tujuan}">
    <span class="L">${k}</span><div class="rr-main"><div class="rr-top"><b>${RUTE[k].nama}</b><span class="num"><b>${f0(r.byR[k])} t</b> · ${f0(r.nR[k])} muatan</span><em class="num">${f1(pc)}%</em></div>
    <div class="rr-bar"><i data-w="${pc}"></i></div></div></div>`; }).join('');
  requestAnimationFrame(() => setTimeout(() => $$('#rRute .rr-bar i').forEach(i => { i.style.width = Math.max(.6, +i.dataset.w) + '%'; }), 120));
};

// ----- Peta TPS
const FP = { ind: 'w', alur: true, label: innerWidth >= 1280, pilih: null };
PAGES.peta = el => {
  el.innerHTML = `
  <div class="panel" style="--i:0"><div class="ph"><div><h3 id="pJudul"></h3><p>Warna mengikuti indikator, ukuran lingkaran sebanding tonase. Garis bergerak menunjukkan alur muatan ke PLTSa.</p></div><div class="tags"><span class="tag">Geospasial</span><span class="tag">Interaktif</span></div></div>
    <div class="mapbox"><div class="lmap" id="pMap"></div><div class="mfloat mlegend" id="pLeg"></div><div class="mfloat mstat" id="pStat"></div></div></div>
  <div class="col side">
    <div class="panel" style="--i:1">${ph('Pengaturan peta', '', ['Kontrol'])}
      <div class="fgrid"><label>Indikator warna<select class="select" id="pInd">${Object.entries(IND).map(([k, v]) => `<option value="${k}">${v.nama}</option>`).join('')}</select></label>
        <div class="two"><label class="swl">Alur ke PLTSa <input type="checkbox" class="switch" id="pAlur" ${FP.alur ? 'checked' : ''}></label><label class="swl">Nama TPS <input type="checkbox" class="switch" id="pLabel" ${FP.label ? 'checked' : ''}></label></div></div></div>
    <div class="panel" style="--i:2">${ph('Peringkat TPS', 'Klik untuk terbang ke lokasi dan melihat profil')}<div class="scroll rank" id="pRank"></div></div>
    <div class="panel profile" style="--i:3" id="pProf"></div>
  </div>`;
  $('#pInd').value = FP.ind;
  const map = buatPeta($('#pMap')), lyr = L.layerGroup().addTo(map);
  let rows = [], marker = {};
  const profil = kode => {
    const r = rows.find(x => x.t.kode === kode) || rows[0]; if (!r) { $('#pProf').innerHTML = ''; return; }
    FP.pilih = r.t.kode;
    $$('#pRank button').forEach(b => b.classList.toggle('on', b.dataset.k === r.t.kode));
    const top = RK.slice().sort((x, y) => r.byR[y] - r.byR[x])[0];
    $('#pProf').innerHTML = `<div class="ph"><div><h3>${esc(r.t.nama)}</h3><p>${JENIS[r.t.tipe] || ''} · Kec. ${esc(r.t.kecamatan)}${r.t.jarak_km ? ` · ${f1(r.t.jarak_km)} km ke PLTSa` : ''}</p></div><div class="tags"><span class="tag gold">Profil</span></div></div>
      <div class="kv"><div><span>Tonase</span><b class="num">${f1(r.ton)} t</b></div><div><span>Kadar air</span><b class="num">${f1(r.w)}%</b></div><div><span>LHV</span><b class="num">${f2(r.lhv)} MJ/kg</b></div><div><span>Rute terbanyak</span><b>${rb(top)}</b></div></div>
      ${komposisiStack(r)}<div class="legend-inline">${FR.map(x => `<span><i style="background:${x.c}"></i>${x.n.split(' ')[0]} ${f0(r[x.k])}%</span>`).join('')}</div>`;
  };
  const gambar = () => {
    const a = dataGlobal(), I = IND[FP.ind];
    rows = perTps(a).filter(r => r.t && r.t.lat != null);
    const res = lapisTps(map, lyr, rows, I, { alur: FP.alur, label: FP.label, pilih: k => profil(k) });
    marker = res.marker;
    $('#pJudul').textContent = `${I.nama} per TPS · ${labelPeriode()}`;
    $('#pLeg').innerHTML = `<h5>${I.nama}</h5>${legendaInd(I, res.batas).map((l, i) => `<div class="row"><span class="sw" style="background:${I.warna[i]}"></span>${l}</div>`).join('')}<div class="note">${I.ket}</div>`;
    const rr = ringkas(a);
    $('#pStat').innerHTML = `<div class="k">${labelJenis()}</div><div class="v num">${f0(rr.ton)} ton</div><div class="s">${f0(rr.n)} muatan · kadar air ${f1(rr.w)}%<br>${f1(rr.pR)}% tonase ke Rute R</div>`;
    const urut = rows.slice().sort((x, y) => I.arah === 'baik' ? I.g(x) - I.g(y) : I.g(y) - I.g(x));
    const batas = res.batas, kelas = v => v < batas[0] ? 0 : v < batas[1] ? 1 : v < batas[2] ? 2 : 3, maks = Math.max(...rows.map(I.g), 1);
    $('#pRank').innerHTML = urut.map((r, i) => { const c = I.warna[kelas(I.g(r))], terang = c === '#cdeee6' || c === '#c9d8fb'; return `<button data-k="${r.t.kode}"><span class="no" style="background:${c}${terang ? '' : '26'};color:${terang ? INK : c}">${i + 1}</span><span><b>${esc(r.t.nama)}</b><small>${JENIS[r.t.tipe] || ''} · ${f0(r.ton)} ton</small></span><span class="val num">${fmtInd(I, I.g(r))}</span><span class="barx"><i style="width:${I.g(r) / maks * 100}%;background:${c}"></i></span></button>`; }).join('');
    $$('#pRank button').forEach(b => b.onclick = () => { const m = marker[b.dataset.k]; profil(b.dataset.k); if (m) { map.flyTo(m.getLatLng(), 15, { duration: .8 }); setTimeout(() => S.maps.includes(map) && m.openPopup(), 850); } });
    profil(FP.pilih && rows.some(r => r.t.kode === FP.pilih) ? FP.pilih : urut[0]?.t.kode);
  };
  $('#pInd').onchange = e => { FP.ind = e.target.value; gambar(); };
  $('#pAlur').onchange = e => { FP.alur = e.target.checked; gambar(); };
  $('#pLabel').onchange = e => { FP.label = e.target.checked; gambar(); };
  gambar();
  setTimeout(() => pasPeta(map, innerWidth < 1024), 60);
};

// ----- Muatan masuk
const FM = { tps: 'semua', rute: 'semua', q: '' };
PAGES.muatan = el => {
  el.innerHTML = `
  <div class="panel no-print" style="--i:0;padding:10px 14px"><div class="toolbar">
    <select class="select" id="mTps" aria-label="TPS asal">${pilihanTps(FM.tps)}</select>
    <select class="select" id="mRute" aria-label="Rute">${pilihanRute(FM.rute)}</select>
    <label class="searchbox">${ico('search')}<input class="text" id="mQ" placeholder="Cari ID, pelat, atau TPS" value="${esc(FM.q)}"></label>
    <span class="count" id="mCount"></span><span class="grow"></span>
    <button class="btn btn-ghost btn-sm" id="mCsv">${ico('down')} Unduh CSV</button></div></div>
  <div class="top" style="--i:1">
    <div class="panel">${ph('Tonase harian per rute dan kadar air', 'Batang = tonase per rute (ton). Garis = kadar air rata-rata tertimbang tonase (%).', ['Tren'])}<div class="chart" id="mC1"></div></div>
    <div class="panel">${ph('Curah hujan dan kadar air', 'Hujan 24 jam sebelum muatan tiba ikut menaikkan kadar air sampah di TPS terbuka.', ['Cuaca'])}<div class="chart" id="mC2"></div></div>
  </div>
  <div class="panel" style="--i:2">${ph('Daftar muatan', 'Terbaru di atas. Rentang = batas bawah sampai batas atas taksiran kadar air (lebar bawaan ±10 poin sebelum kalibrasi uji oven).', ['Log gerbang'])}<div class="tbl-wrap" id="mTab"></div></div>`;
  const gambar = () => {
    S.charts.forEach(c => c.dispose()); S.charts = []; S.obs.forEach(o => o.disconnect()); S.obs = [];
    const a = dataGlobal(FM), r = ringkas(a), p = periode(), hari = rentangHari(p.dari, p.sampai), g = groupBy(a, m => tgl(m.t));
    $('#mCount').innerHTML = `<b>${f0(r.n)}</b> muatan · <b>${f1(r.ton)}</b> ton · kadar air <b>${f1(r.w)}%</b>`;
    chart($('#mC1'), {
      legend: { data: RK.map(k => `${k} · ${RUTE[k].nama}`).concat(['Kadar air']) },
      tooltip: Object.assign({ trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: v => v == null ? '–' : f1(v) }, TT),
      xAxis: axisCat(hari.map(hariID)), yAxis: [axisVal('ton'), axisVal('air %', { min: 0, max: 100, splitLine: { show: false }, nameTextStyle: { color: '#8a96ad', fontSize: 11, align: 'right' } })],
      series: RK.map(k => ({ name: `${k} · ${RUTE[k].nama}`, type: 'bar', stack: 't', barWidth: '62%', itemStyle: { color: RUTE[k].warna }, emphasis: { focus: 'series' }, data: hari.map(d => +sum((g[d] || []).filter(x => x.rute === k), x => x.ton).toFixed(1)) }))
        .concat([{ name: 'Kadar air', type: 'line', yAxisIndex: 1, smooth: .3, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2.5, color: '#0c1d45' }, itemStyle: { color: '#0c1d45' }, data: hari.map(d => g[d] ? +wavg(g[d], x => x.w).toFixed(1) : null),
          markLine: { symbol: 'none', silent: true, label: { formatter: 'Batas umpan reaktor 20%', position: 'insideEndTop', backgroundColor: '#fff', padding: [2, 5], borderRadius: 4, color: '#c2413a', fontWeight: 700, fontSize: 11 }, lineStyle: { color: '#c2413a', type: 'dashed' }, data: [{ yAxis: 20 }] } }]),
    });
    const hujan = Object.fromEntries(S.data.hujan.map(h => [h.tanggal, h.mm]));
    chart($('#mC2'), {
      legend: { data: ['Curah hujan', 'Kadar air'] },
      tooltip: Object.assign({ trigger: 'axis', valueFormatter: v => v == null ? '–' : f1(v) }, TT),
      xAxis: axisCat(hari.map(hariID)), yAxis: [axisVal('hujan mm'), axisVal('air %', { min: 30, max: 75, splitLine: { show: false }, nameTextStyle: { color: '#8a96ad', fontSize: 11, align: 'right' } })],
      series: [{ name: 'Curah hujan', type: 'bar', barWidth: '55%', itemStyle: { color: '#8fb4ff', borderRadius: [5, 5, 0, 0] }, data: hari.map(d => hujan[d] ?? 0) },
        { name: 'Kadar air', type: 'line', yAxisIndex: 1, smooth: .3, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2.5, color: '#078879' }, itemStyle: { color: '#078879' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#07887930' }, { offset: 1, color: '#07887900' }]) }, data: hari.map(d => g[d] ? +wavg(g[d], x => x.w).toFixed(1) : null) }],
    });
    const baris = a.slice().reverse(), maks = 500;
    $('#mTab').innerHTML = `<table><thead><tr><th>Waktu</th><th>ID muatan</th><th>TPS asal</th><th>Pelat</th><th class="r">Berat</th><th class="r">Kadar air</th><th class="r">Rentang</th><th class="r">LHV MJ/kg</th><th>Komposisi berat</th><th class="r">Hujan 24 j</th><th>Rute</th><th>Catatan</th></tr></thead><tbody>${baris.slice(0, maks).map(m => `<tr>
      <td class="num">${hariID(tgl(m.t))} ${m.t.slice(11, 16)}</td><td><b>${esc(m.id)}</b></td><td>${esc(S.tpsBy[m.tps]?.nama || m.tps)}</td><td>${esc(m.pelat)}</td>
      <td class="r num">${f2(m.ton)} t</td><td class="r num"><b>${f1(m.w)}%</b></td><td class="r num">${f0(m.wb)}–${f0(m.wa)}%</td><td class="r num">${f2(m.lhv)}</td>
      <td>${komposisiStack(m)}</td><td class="r num">${f1(m.r24)} mm</td><td>${rb(m.rute)}</td><td>${m.cek ? '<span class="flag">Cek manual</span> ' : ''}${m.sumber === 'aplikasi' ? '<span class="src">Dari HP</span>' : ''}</td></tr>`).join('')}</tbody></table>
      ${baris.length > maks ? `<p class="count" style="padding:10px">Menampilkan ${maks} muatan terbaru dari ${f0(baris.length)}. Unduh CSV untuk daftar lengkap.</p>` : ''}${!baris.length ? '<p class="count" style="padding:14px">Tidak ada muatan yang cocok dengan saringan.</p>' : ''}`;
  };
  $('#mTps').onchange = e => { FM.tps = e.target.value; gambar(); };
  $('#mRute').onchange = e => { FM.rute = e.target.value; gambar(); };
  let h; $('#mQ').oninput = e => { clearTimeout(h); h = setTimeout(() => { FM.q = e.target.value.trim(); gambar(); }, 250); };
  $('#mCsv').onclick = () => { const p = periode(); unduhCsv(dataGlobal(FM), `SORA-muatan-${p.dari}_${p.sampai}`); };
  gambar();
};

// ----- Komposisi
PAGES.komposisi = el => {
  const a = dataGlobal(), r = ringkas(a);
  el.innerHTML = `
  <div class="panel" style="--i:0">${ph('Komposisi keseluruhan', 'Persen berat, tertimbang tonase', ['Komposisi'])}<div class="chart" id="kC1"></div></div>
  <div class="panel" style="--i:1">${ph('Komposisi per TPS', 'Diurutkan dari porsi organik terbesar. Arahkan kursor untuk rincian.', ['Perbandingan'])}<div class="chart" id="kC2"></div></div>
  <div class="panel" style="--i:2">${ph('Organik dan kadar air', 'Satu titik = satu muatan. Makin banyak organik, makin basah.', ['Relasi'])}<div class="chart" id="kC3"></div></div>
  <div class="panel" style="--i:3">${ph('Sebaran nilai kalor', 'Jumlah muatan per kelas LHV (MJ/kg), menurut rute', ['Distribusi'])}<div class="chart" id="kC4"></div></div>`;
  const komp = FR.map(x => +wavg(a, m => m[x.k]).toFixed(1)), tk = sum(komp, v => v) || 1;
  chart($('#kC1'), {
    tooltip: Object.assign({ trigger: 'item', valueFormatter: v => f1(v) + '%' }, TT),
    legend: { bottom: 0, top: 'auto', left: 'center' },
    title: { text: f1(komp[0] / tk * 100) + '%', subtext: 'organik basah', left: 'center', top: '35%', textStyle: { fontSize: 24, fontWeight: 800, color: INK, fontFamily: FONT }, subtextStyle: { fontSize: 12, color: MUTED, fontFamily: FONT }, itemGap: 2 },
    series: [{ type: 'pie', radius: ['47%', '68%'], center: ['50%', '43%'], minShowLabelAngle: 3, itemStyle: { borderColor: '#fff', borderWidth: 3, borderRadius: 6 },
      label: { formatter: p => f1(p.percent) + '%', fontWeight: 800, fontSize: 12.5, overflow: 'none' }, labelLine: { length: 8, length2: 6 },
      data: FR.map((x, i) => ({ name: x.n, value: komp[i], itemStyle: { color: x.c } })) }],
  });
  const rows = perTps(a).sort((x, y) => x.org - y.org);
  chart($('#kC2'), {
    tooltip: Object.assign({ trigger: 'axis', valueFormatter: v => f1(v) + '%' }, TT),
    xAxis: axisVal('', { max: 100, axisLabel: { formatter: '{value}%', color: MUTED, fontSize: 11 } }), yAxis: axisCat(rows.map(x => x.t.nama.replace('TPS ', '')), { axisLabel: { color: INK, fontSize: 11, interval: 0 } }),
    series: FR.map(x => ({ name: x.n, type: 'bar', stack: 'k', barWidth: '64%', itemStyle: { color: x.c }, emphasis: { focus: 'series' }, data: rows.map(t => +wavg(t.rows, m => m[x.k]).toFixed(1)) })),
  });
  chart($('#kC3'), {
    grid: { left: 6, right: 14, top: 36, bottom: 22, containLabel: true },
    legend: { data: RK.map(k => `${k} · ${RUTE[k].nama}`) },
    tooltip: Object.assign({ trigger: 'item', formatter: p => `<b>${p.data[2]}</b><br>Organik ${f1(p.data[0])}% · kadar air ${f1(p.data[1])}%` }, TT),
    xAxis: axisVal('organik %', { min: 0, max: 100, nameLocation: 'middle', nameGap: 22, nameTextStyle: { color: '#8a96ad', fontSize: 11 } }), yAxis: axisVal('kadar air %', { min: 0, max: 90 }),
    series: RK.map(k => ({ name: `${k} · ${RUTE[k].nama}`, type: 'scatter', symbolSize: 6, itemStyle: { color: RUTE[k].warna, opacity: .65 }, data: a.filter(m => m.rute === k).map(m => [m.org, m.w, m.id]) })),
  });
  const kelas = [-2, 2, 4, 6, 8, 10, 12, 14, 30], lab = ['< 2', '2–4', '4–6', '6–8', '8–10', '10–12', '12–14', '≥ 14'];
  chart($('#kC4'), {
    legend: { data: RK.map(k => `${k} · ${RUTE[k].nama}`) },
    xAxis: axisCat(lab), yAxis: axisVal('muatan'),
    series: RK.map(k => ({ name: `${k} · ${RUTE[k].nama}`, type: 'bar', stack: 'h', barWidth: '64%', itemStyle: { color: RUTE[k].warna }, data: lab.map((_, i) => a.filter(m => m.rute === k && m.lhv >= kelas[i] && m.lhv < kelas[i + 1]).length) })),
  });
};

// ----- Rute dan neraca
PAGES.rute = el => {
  const a = dataGlobal(), r = ringkas(a), p = periode(), hari = rentangHari(p.dari, p.sampai), g = groupBy(a, m => tgl(m.t));
  const hit = groupBy(a, aturanKe), nHit = i => (hit[i] || []).length;
  const aturan = [
    [1, 'R', `Inert ≥ ${AMBANG.inert}%`, 'Batu, kaca, dan logam merusak reaktor dan tidak bisa dimakan maggot.'],
    [2, 'U', `Batas atas kadar air ≤ ${AMBANG.airUmpan}%`, 'Memakai batas atas rentang, bukan taksiran tengah, agar muatan basah tidak lolos.'],
    [3, 'M', `Kadar air ≥ ${AMBANG.airMaggot}%, organik ≥ ${AMBANG.organikMaggot}%, plastik ≤ ${AMBANG.plastikMaggot}%`, 'Organik basah dan bersih, cocok untuk larva BSF dan kompos.'],
    [4, 'B', `Kadar air < ${AMBANG.airBioDrying}%`, 'Dikeringkan di bak bio-drying dengan serbuk kayu 10–20%.'],
    [5, 'R', 'Selain itu', 'Sangat basah dan tercampur: ditahan, lalu dilaporkan ke TPS asal.'],
  ];
  el.innerHTML = `
  <div class="rcards" style="--i:0">${RK.map(k => `<div class="rcard" style="--c:${RUTE[k].warna}" title="${RUTE[k].tujuan}">
    <span class="L">${k}</span><span class="nm">Rute ${k} · ${RUTE[k].nama}</span><span class="to">${RUTE[k].lengkap}. ${RUTE[k].tujuan}</span>
    <div class="nums"><b class="num"><span data-count="${r.byR[k]}">0</span></b><span>ton · ${f0(r.nR[k])} muatan · air ${f1(wavg(a.filter(m => m.rute === k), m => m.w))}%</span><span class="pct num">${f1(r.ton ? r.byR[k] / r.ton * 100 : 0)}%</span></div>
    <div class="bar"><i data-w="${r.ton ? r.byR[k] / r.ton * 100 : 0}"></i></div></div>`).join('')}</div>
  <div class="mid" style="--i:1">
    <div class="panel">${ph('Tonase harian per rute', `${labelPeriode()} · ${labelJenis()}`, ['Tren'])}<div class="chart" id="uC1"></div></div>
    <div class="panel">${ph('Aturan rute', 'Diperiksa berurutan. Aturan pertama yang terpenuhi menjadi rekomendasi. Angka di kanan = muatan yang ditentukan aturan itu.', ['!Logika'])}
      <div class="scroll ladder">${aturan.map(([n, k, j, ket]) => `<div class="step-r"><span class="n">${n}</span><div><b>${j}</b><small>${ket}</small></div><div style="text-align:right">${rb(k)}<small class="num" style="margin-top:3px">${f0(nHit(n))} muatan</small></div></div>`).join('')}</div>
      <div class="howto">Petugas boleh mengganti rute di aplikasi HP dengan alasan tertulis minimal 10 karakter. Rekomendasi awal tetap tercatat.</div></div>
  </div>
  <div class="kpis k4" style="--i:2">
    ${kpi({ k: 'Serbuk kayu dibutuhkan', icon: 'leaf', v: serbukKayu(a), unit: 'ton', accent: RUTE.B.warna, f: 'Dosis 10–20% untuk muatan Rute B', title: 'd = (w − 0,50) ÷ (0,50 − 0,12), dibatasi 10–20%' })}
    ${kpi({ k: 'Air yang perlu diuapkan', icon: 'drop', v: airDiuapkan(a), unit: 'ton', accent: '#078879', f: 'Agar muatan Rute B mencapai 20%', title: 'air = berat × (w − 20%) ÷ 80%' })}
    ${kpi({ k: 'Potensi listrik Rute U', icon: 'zap', v: listrikU(a), dec: 1, unit: 'MWh', accent: RUTE.U.warna, f: 'Asumsi efisiensi listrik 20%', title: 'kWh = berat (kg) × LHV × 0,20 ÷ 3,6' })}
    ${kpi({ k: 'Ditahan di Rute R', icon: 'alert', v: r.byR.R, unit: 'ton', accent: RUTE.R.warna, f: `<b>${f0(r.nR.R)}</b> muatan dilaporkan ke TPS asal` })}
  </div>`;
  countUp(el);
  requestAnimationFrame(() => setTimeout(() => $$('.rcard .bar i', el).forEach(i => { i.style.width = i.dataset.w + '%'; }), 80));
  chart($('#uC1'), {
    legend: { data: RK.map(k => `${k} · ${RUTE[k].nama}`) },
    tooltip: Object.assign({ trigger: 'axis', valueFormatter: v => f1(v) + ' ton' }, TT),
    xAxis: axisCat(hari.map(hariID)), yAxis: axisVal('ton'),
    series: RK.map(k => ({ name: `${k} · ${RUTE[k].nama}`, type: 'bar', stack: 'a', barWidth: '64%', itemStyle: { color: RUTE[k].warna, borderRadius: k === 'R' ? [4, 4, 0, 0] : 0 }, emphasis: { focus: 'series' }, data: hari.map(d => +sum((g[d] || []).filter(x => x.rute === k), x => x.ton).toFixed(1)) })),
  });
};

// ----- Model dan validasi
PAGES.model = el => {
  const kriteria = [['Segmentasi', 'mIoU enam fraksi dan latar', '≥ 0,55'], ['Segmentasi', 'Selisih mIoU terhadap CLIPSeg tanpa pelatihan', '≥ +0,15'], ['Komposisi', 'MAE proporsi massa per unit', '≤ 3 poin persen'],
    ['Kadar air', 'MAE terhadap uji oven', '≤ 5 poin persen'], ['Rentang', 'PICP rentang 80%', '0,70–0,90'], ['Keputusan', 'Muatan basah (> 20%) yang lolos ke Rute U', '≤ 5%'],
    ['Keputusan', 'Kesesuaian rute dengan rute dari kadar air oven', '≥ 80%'], ['Kecepatan', 'Waktu inferensi di Raspberry Pi 5', '≤ 2 detik per frame'], ['Kapasitas', 'Waktu dari selesai scan sampai hasil tampil', '< 60 detik'],
    ['Ketangguhan', 'Penurunan mIoU pada gangguan cahaya, kabur, derau', '≤ 0,10'], ['Kompresi', 'Penurunan mIoU setelah INT8', '< 0,01']];
  const rujukan = ['Chen, L.-C., dkk. (2018). Encoder-decoder with atrous separable convolution for semantic image segmentation. <i>ECCV</i>.', 'Bashkirova, D., dkk. (2022). ZeroWaste dataset: Towards deformable object segmentation in cluttered scenes. <i>CVPR</i>.',
    'Proença, P. F., &amp; Simões, P. (2020). TACO: Trash annotations in context for litter detection. arXiv:2003.06975.', 'Tchobanoglous, G., Theisen, H., &amp; Vigil, S. A. (1993). <i>Integrated Solid Waste Management</i>. McGraw-Hill.',
    'Hoerl, A. E., &amp; Kennard, R. W. (1970). Ridge regression. <i>Technometrics</i>, 12(1), 55–67.', 'Barber, R. F., dkk. (2021). Predictive inference with the jackknife+. <i>The Annals of Statistics</i>, 49(1), 486–507.',
    'ASTM E790-15. Residual moisture in a refuse-derived fuel analysis sample.', 'ISO 18125:2017 dan ISO 21654:2021. Penentuan nilai kalor bahan bakar padat.'];
  el.innerHTML = `
  <div class="notice" style="--i:0">${ico('info')}<span><b>Status saat ini.</b> Model segmentasi di aplikasi masih versi uji dan kadar air belum dikalibrasi uji oven. Pengumpulan 300 foto dan 25 uji oven dijadwalkan 9–27 November 2026, pelatihan dan evaluasi 28 November–3 Desember 2026.</span></div>
  <div class="mcards" style="--i:1">
    <div class="mcard"><span class="st warn"><i></i>Versi uji</span><h4>Segmentasi komposisi</h4><p>DeepLabv3+ dengan encoder ResNet-50. Setiap piksel diberi satu dari enam fraksi atau latar, lalu luas diubah menjadi berat.</p>
      <ul><li>Pralatih: TACO dan ZeroWaste-f (sekitar 2.700 foto berlabel)</li><li>Penyesuaian: 210 foto tim dari Kudus dan Malang, uji 90 foto</li><li>Berjalan sebagai ONNX INT8 di HP dan Raspberry Pi 5</li></ul></div>
    <div class="mcard"><span class="st warn"><i></i>Belum dikalibrasi</span><h4>Kadar air</h4><p>Neraca massa per fraksi, dikoreksi hujan 24 dan 72 jam dengan regresi ridge. Rentang 80% dari Jackknife+.</p>
      <ul><li>Kalibrasi: 25 uji oven (ASTM E790-15, 110 °C)</li><li>Validasi tinggalkan-satu-sampel pada 25 unit</li><li>Sebelum kalibrasi: rentang bawaan ±10 poin</li></ul></div>
    <div class="mcard"><span class="st ok"><i></i>Rumus standar</span><h4>Nilai kalor (LHV)</h4><p>Dihitung, bukan dilatih: nilai kalor kering tiap fraksi ditimbang komposisi, lalu dikurangi efek air.</p>
      <ul><li>LHV = (1 − w) × LHV<sub>kering</sub> − 2,443 × w</li><li>ISO 18125:2017 dan ISO 21654:2021</li><li>Nilai fraksi dari Tchobanoglous dkk. (1993)</li></ul></div>
  </div>
  <div class="bottom" style="--i:2">
    <div class="panel">${ph('Rencana data tahap 1', 'Satu unit = satu sampel sampah yang difoto 5 kali', ['Data'])}
      <div class="tbl-wrap"><table><thead><tr><th>Sumber</th><th class="r">Unit</th><th class="r">Foto</th><th class="r">Oven</th><th class="r">Uji akhir</th></tr></thead><tbody>
      ${[['TPS permukiman, Kudus', 10, 50, 4, '3 / 15'], ['Pasar, Kudus', 10, 50, 4, '3 / 15'], ['TPS permukiman, Malang', 10, 50, 4, '3 / 15'], ['Pasar, Malang', 10, 50, 4, '3 / 15'], ['Campuran buatan lab', 20, 100, 9, '6 / 30']]
        .map(x => `<tr><td>${x[0]}</td>${x.slice(1).map(v => `<td class="r num">${v}</td>`).join('')}</tr>`).join('')}
      <tr style="font-weight:800;background:#f7f9fd"><td>Jumlah</td><td class="r">60</td><td class="r">300</td><td class="r">25</td><td class="r">18 / 90</td></tr></tbody></table></div>
      <p class="count" style="margin-top:8px">Uji akhir ditulis unit / foto. Sisanya, 42 unit (210 foto), menjadi data pengembangan.</p></div>
    <div class="panel">${ph('Pembagian data tanpa kebocoran', 'StratifiedGroupKFold: kelompok = unit, strata = lokasi', ['Validasi'])}
      <div class="split scroll"><div class="blk all"><span>Seluruh data tim</span><b>60 unit · 300 foto</b></div>
        <div class="two"><div class="blk dev"><span>Pengembangan</span><b>42 unit · 210 foto</b></div><div class="blk test"><span>Uji akhir, dikunci</span><b>18 unit · 90 foto</b></div></div>
        <div class="folds" id="folds">${[1, 2, 3, 4, 5].map(i => `<div>Lipatan ${i}<small>8–9 unit</small></div>`).join('')}</div>
        <p>Bergiliran, satu lipatan (emas) menjadi validasi dan empat lainnya data latih. Lima foto satu unit selalu di bagian yang sama, jadi model tidak pernah dinilai dengan foto yang mirip data latihnya. Model akhir dilatih ulang pada 42 unit, lalu dinilai sekali pada 18 unit uji.</p></div></div>
    <div class="panel"><div class="ph"><div><h3 id="kTitle">Kriteria lulus evaluasi</h3><p>Diukur pada set uji akhir, selang kepercayaan 95% bootstrap per unit</p></div><div class="segtabs" id="kTabs"><button class="on" data-t="k">Kriteria</button><button data-t="r">Rujukan</button></div></div>
      <div class="tbl-wrap" id="kBody"></div></div>
  </div>`;
  const tabK = `<table><thead><tr><th>Aspek</th><th>Ukuran</th><th>Batas lulus</th></tr></thead><tbody>${kriteria.map(x => `<tr><td><b>${x[0]}</b></td><td style="white-space:normal">${x[1]}</td><td><b>${x[2]}</b></td></tr>`).join('')}</tbody></table>`;
  const tabR = `<ol class="refs" style="padding:10px 14px 10px 30px">${rujukan.map(x => `<li>${x}</li>`).join('')}</ol>`;
  $('#kBody').innerHTML = tabK;
  $$('#kTabs button').forEach(b => b.onclick = () => { $$('#kTabs button').forEach(x => x.classList.toggle('on', x === b)); $('#kBody').innerHTML = b.dataset.t === 'k' ? tabK : tabR; $('#kTitle').textContent = b.dataset.t === 'k' ? 'Kriteria lulus evaluasi' : 'Rujukan utama'; });
  let f = 0; const putar = () => { $$('#folds div').forEach((d, i) => d.classList.toggle('val', i === f)); f = (f + 1) % 5; };
  putar(); S.timers.push(setInterval(putar, 1600));
};

// ----- Laporan
const FL = { tps: 'semua', jenis: 'semua', rute: 'semua', dari: '', sampai: '' };
const labelFilter = f => [f.tps === 'semua' ? 'Semua TPS' : (S.tpsBy[f.tps]?.nama || f.tps), f.jenis === 'semua' ? 'semua jenis' : JENIS[f.jenis], f.rute === 'semua' ? 'semua rute' : `Rute ${f.rute}`, `${tglPanjang(f.dari)} – ${tglPanjang(f.sampai)}`].join(' · ');
PAGES.laporan = el => {
  if (!FL.dari) { const p = periode(); FL.dari = p.dari; FL.sampai = p.sampai; }
  el.innerHTML = `
  <div class="col" style="--i:0;grid-template-rows:auto auto 1fr">
    <div class="panel no-print">${ph('Saring laporan', '', ['Filter'])}
      <div class="fgrid">
        <label>TPS asal<select class="select" id="lTps">${pilihanTps(FL.tps)}</select></label>
        <div class="two"><label>Jenis TPS<select class="select" id="lJenis"><option value="semua">Semua jenis</option>${Object.entries(JENIS).slice(0, 3).map(([k, v]) => `<option value="${k}"${k === FL.jenis ? ' selected' : ''}>${v}</option>`).join('')}</select></label>
        <label>Rute<select class="select" id="lRute">${pilihanRute(FL.rute)}</select></label></div>
        <div class="two"><label>Dari<input type="date" class="text" id="lDari" value="${FL.dari}" min="${tanggalAwal()}" max="${tanggalAkhir()}"></label><label>Sampai<input type="date" class="text" id="lSampai" value="${FL.sampai}" min="${tanggalAwal()}" max="${tanggalAkhir()}"></label></div>
        <button class="btn btn-ghost btn-sm" id="lReset">${ico('refresh')} Atur ulang</button>
      </div></div>
    <div class="panel no-print">${ph('Unduh laporan', 'Isi unduhan mengikuti saringan di atas')}
      <div class="actions"><button class="btn btn-primary btn-sm" id="lXlsx">${ico('down')} Excel: rekap, rincian, keterangan</button>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><button class="btn btn-ghost btn-sm" id="lCsv">${ico('file')} CSV</button><button class="btn btn-ghost btn-sm" id="lPdf">${ico('print')} Cetak / PDF</button></div></div></div>
    <div class="panel no-print">${ph('Impor dari aplikasi HP', 'CSV dari tombol Unduh laporan di aplikasi SORA')}
      <label class="drop" id="drop"><span class="di">${ico('phone')}</span><span style="flex:1;min-width:0"><b>Pilih atau seret SORA-….csv</b><small id="impInfo">${S.impor.length ? `${f0(S.impor.length)} bagian dari HP sudah diimpor.` : 'Belum ada data yang diimpor.'}</small></span><input type="file" accept=".csv,text/csv" id="impFile" hidden></label>
      ${S.impor.length ? '<button class="linkbtn" id="impHapus">Hapus data impor</button>' : ''}</div>
  </div>
  <div class="panel" id="lapPrint" style="--i:1">
    <div class="print-only"><h2>Laporan SORA · Mutu Umpan PLTSa Putri Cempo</h2><p id="lPrintSub"></p></div>
    <div class="ph"><div><h3>Rekap per TPS</h3><p id="lFilter"></p></div><div class="tags"><span class="tag">Laporan</span></div></div>
    <div class="sumrow" id="lSum"></div>
    <div class="tbl-wrap" id="lTab"></div>
  </div>`;
  const gambar = () => {
    const a = saring(FL), r = ringkas(a);
    $('#pillPeriod').textContent = `Periode laporan ${tglPanjang(FL.dari)} – ${tglPanjang(FL.sampai)}`;
    $('#lFilter').textContent = labelFilter(FL); $('#lPrintSub').textContent = `${labelFilter(FL)} · dibuat ${new Date().toLocaleString('id-ID')} · ${S.impor.length ? 'data simulasi dan impor HP' : 'data simulasi'}`;
    $('#lSum').innerHTML = [['Muatan', f0(r.n)], ['Tonase', f1(r.ton) + ' t'], ['Kadar air', f1(r.w) + '%'], ['Nilai kalor', f2(r.lhv) + ' MJ/kg'], ['Ke Rute R', f1(r.pR) + '%']].map(([k, v]) => `<div class="sum"><span>${k}</span><b class="num">${v}</b></div>`).join('');
    const rek = perTps(a);
    $('#lTab').innerHTML = rek.length ? `<table><thead><tr><th>TPS</th><th>Jenis</th><th class="r">Muatan</th><th class="r">Tonase</th><th class="r">Kadar air</th><th class="r">LHV</th>${RK.map(k => `<th class="r" title="${RUTE[k].lengkap}">${k} (t)</th>`).join('')}<th>Porsi Rute R</th></tr></thead><tbody>${rek.map(x => `<tr>
      <td><b>${esc(x.t.nama)}</b></td><td>${JENIS[x.t.tipe] || ''}</td><td class="r num">${f0(x.n)}</td><td class="r num">${f1(x.ton)} t</td><td class="r num">${f1(x.w)}%</td><td class="r num">${f2(x.lhv)}</td>
      ${RK.map(k => `<td class="r num">${f1(x.byR[k])}</td>`).join('')}<td><div class="meter"><span><i style="width:${Math.min(100, x.pR * 2)}%;background:${x.pR >= 25 ? '#d0473f' : x.pR >= 15 ? '#f0a43a' : '#1f9d74'}"></i></span><b class="num">${f0(x.pR)}%</b></div></td></tr>`).join('')}
      <tr style="font-weight:800;background:#f7f9fd"><td>Jumlah</td><td></td><td class="r num">${f0(r.n)}</td><td class="r num">${f1(r.ton)} t</td><td class="r num">${f1(r.w)}%</td><td class="r num">${f2(r.lhv)}</td>${RK.map(k => `<td class="r num">${f1(r.byR[k])}</td>`).join('')}<td class="num">${f0(r.pR)}%</td></tr></tbody></table>` : '<p class="count" style="padding:14px">Tidak ada data yang cocok dengan saringan.</p>';
  };
  const ikat = (id, k) => { $(id).onchange = e => { FL[k] = e.target.value; if (k === 'jenis') { G.jenis = FL.jenis; sinkronHeader(); } if (FL.dari > FL.sampai) { FL.sampai = FL.dari; $('#lSampai').value = FL.sampai; } gambar(); }; };
  ikat('#lTps', 'tps'); ikat('#lJenis', 'jenis'); ikat('#lRute', 'rute'); ikat('#lDari', 'dari'); ikat('#lSampai', 'sampai');
  $('#lReset').onclick = () => { const p = periode(); Object.assign(FL, { tps: 'semua', jenis: G.jenis, rute: 'semua', dari: p.dari, sampai: p.sampai }); buka('laporan'); };
  $('#lCsv').onclick = () => unduhCsv(saring(FL), `SORA-laporan-${FL.dari}_${FL.sampai}`);
  $('#lXlsx').onclick = () => {
    const a = saring(FL); if (!a.length) return toast('Tidak ada data untuk diunduh.');
    const wb = XLSX.utils.book_new(), rk = rekapEkspor(a), br = barisEkspor(a);
    const s1 = XLSX.utils.json_to_sheet(rk), s2 = XLSX.utils.json_to_sheet(br);
    s1['!cols'] = Object.keys(rk[0]).map(k => ({ wch: Math.max(10, k.length + 2) })); s2['!cols'] = Object.keys(br[0]).map(k => ({ wch: Math.max(10, k.length + 2) }));
    XLSX.utils.book_append_sheet(wb, s1, 'Rekap per TPS'); XLSX.utils.book_append_sheet(wb, s2, 'Rincian muatan');
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([['Laporan SORA · Mutu Umpan PLTSa Putri Cempo'], ['Saringan', labelFilter(FL)], ['Dibuat', new Date().toLocaleString('id-ID')], ['Sumber data', S.impor.length ? 'Simulasi dan impor aplikasi HP' : 'Simulasi (bukan data lapangan)'],
      ['Aturan rute', 'R bila inert ≥ 20%; U bila batas atas kadar air ≤ 20%; M bila kadar air ≥ 60%, organik ≥ 60%, plastik ≤ 5%; B bila kadar air < 65%; selain itu R'], ['Nilai kalor', 'LHV = (1 − w) × LHV kering − 2,443 × w']]), 'Keterangan');
    unduh(new Blob([XLSX.write(wb, { bookType: 'xlsx', type: 'array' })], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), `SORA-rekap-${FL.dari}_${FL.sampai}.xlsx`); toast('Rekap Excel diunduh.');
  };
  $('#lPdf').onclick = () => window.print();
  const inp = $('#impFile'), dz = $('#drop');
  inp.onchange = () => inp.files[0] && imporCsv(inp.files[0]);
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
  dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('drag'); e.dataTransfer.files[0] && imporCsv(e.dataTransfer.files[0]); });
  const hapus = $('#impHapus'); if (hapus) hapus.onclick = () => { S.impor = []; store.set('sora-impor', []); gabungImpor(); toast('Data impor dihapus.'); buka('laporan'); };
  gambar();
};

// ------------------------------------------------------------------ ekspor
function unduh(blob, nama) { const u = URL.createObjectURL(blob), a = document.createElement('a'); a.href = u; a.download = nama; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 1500); }
function barisEkspor(a) {
  return a.map(m => ({ 'ID muatan': m.id, 'Waktu (WIB)': m.t.replace('T', ' '), 'TPS': S.tpsBy[m.tps]?.nama || m.tps, 'Jenis TPS': JENIS[S.tpsBy[m.tps]?.tipe] || '', 'Pelat': m.pelat, 'Berat (ton)': +m.ton.toFixed(2),
    'Kadar air (%)': m.w, 'Batas bawah (%)': m.wb, 'Batas atas (%)': m.wa, 'LHV (MJ/kg)': m.lhv, ...Object.fromEntries(FR.map(x => [`${x.n} (%)`, m[x.k]])),
    'Hujan 24 jam (mm)': m.r24, 'Dosis serbuk kayu (%)': m.dosis, 'Rute': m.rute, 'Tujuan': RUTE[m.rute].tujuan, 'Cek manual': m.cek ? 'Ya' : '', 'Sumber': m.sumber === 'aplikasi' ? 'Aplikasi HP' : 'Simulasi' }));
}
function rekapEkspor(a) {
  return perTps(a).map(x => ({ 'TPS': x.t.nama, 'Jenis TPS': JENIS[x.t.tipe] || '', 'Kecamatan': x.t.kecamatan, 'Muatan': x.n, 'Tonase (ton)': +x.ton.toFixed(2), 'Kadar air rata-rata (%)': +x.w.toFixed(1), 'LHV rata-rata (MJ/kg)': +x.lhv.toFixed(2),
    'Organik basah (%)': +x.org.toFixed(1), 'Inert (%)': +x.ine.toFixed(1), ...Object.fromEntries(RK.map(k => [`Rute ${k} (ton)`, +x.byR[k].toFixed(2)])), 'Porsi Rute R (%)': +x.pR.toFixed(1) }));
}
function unduhCsv(a, nama) {
  if (!a.length) return toast('Tidak ada data untuk diunduh.');
  const rows = barisEkspor(a), kol = Object.keys(rows[0]);
  const csv = '﻿' + [kol].concat(rows.map(r => kol.map(k => r[k]))).map(r => r.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(';')).join('\r\n');
  unduh(new Blob([csv], { type: 'text/csv;charset=utf-8' }), nama + '.csv'); toast('CSV diunduh.');
}

// ------------------------------------------------------------------ impor CSV aplikasi HP
function parseCsv(teks) {
  teks = teks.replace(/^﻿/, '');
  const baris1 = teks.split('\n')[0], pemisah = (baris1.match(/;/g) || []).length >= (baris1.match(/,/g) || []).length ? ';' : ',';
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < teks.length; i++) {
    const c = teks[i];
    if (q) { if (c === '"') { if (teks[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
    else if (c === '"') q = true;
    else if (c === pemisah) { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && teks[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.some(x => x.trim()));
}
function imporCsv(file) {
  const rd = new FileReader();
  rd.onload = () => {
    try {
      const rows = parseCsv(rd.result), h = rows[0].map(x => x.trim()), ix = n => h.indexOf(n), v = (r, n) => ix(n) < 0 ? '' : (r[ix(n)] ?? '');
      const num = s => { const x = parseFloat(String(s).replace(',', '.')); return isFinite(x) ? x : 0; };
      if (ix('ID muatan') < 0 || ix('Kadar air %') < 0) throw new Error('Kolom tidak dikenali');
      const byNama = Object.fromEntries(S.tps.map(t => [t.nama.toLowerCase(), t.kode]));
      const tipeOk = t => (JENIS[t] ? t : ({ Pasar: 'pasar', Permukiman: 'permukiman', 'Ruang publik': 'ruang_publik' }[t] || 'lainnya'));
      const baru = rows.slice(1).map((r, i) => {
        const namaTps = v(r, 'TPS').trim(), kode = byNama[namaTps.toLowerCase()] || ('HP-' + namaTps.replace(/\W+/g, '-').toUpperCase());
        const rute = (v(r, 'Keputusan') || v(r, 'Rekomendasi')).trim().toUpperCase();
        const w = num(v(r, 'Kadar air %')), lhv = num(v(r, 'LHV MJ/kg')), t = waktuWIB(v(r, 'Waktu')) || waktuWIB(new Date().toISOString());
        return { id: `${v(r, 'ID muatan')}-${v(r, 'Bagian') || i + 1}`, muatan: v(r, 'ID muatan'), t,
          tps: kode, tpsNama: namaTps, tipe: tipeOk(v(r, 'Jenis TPS').trim()), pelat: v(r, 'Pelat'), ton: num(v(r, 'Berat kg')) / 1000,
          w, wb: v(r, 'Batas bawah %') !== '' ? num(v(r, 'Batas bawah %')) : Math.max(0, w - 10), wa: v(r, 'Batas atas %') !== '' ? num(v(r, 'Batas atas %')) : w + 10, lhv,
          org: num(v(r, 'Organik %')), pla: num(v(r, 'Plastik %')), ker: num(v(r, 'Kertas %')), tek: num(v(r, 'Tekstil %')), kay: num(v(r, 'Kayu %')), ine: num(v(r, 'Inert %')),
          r24: num(v(r, 'Hujan 24 jam mm')), r72: num(v(r, 'Hujan 72 jam mm')), rute: RK.includes(rute) ? rute : 'R', dosis: num(v(r, 'Dosis serbuk kayu %')),
          kwh: Math.max(0, 1000 * lhv * EFISIENSI_LISTRIK / 3.6), cek: !!v(r, 'Peringatan').trim(), sumber: 'aplikasi' };
      }).filter(m => m.ton > 0);
      const ada = new Set(S.impor.map(m => m.id)), tambah = baru.filter(m => !ada.has(m.id));
      S.impor = S.impor.concat(tambah); store.set('sora-impor', S.impor); gabungImpor();
      toast(`${tambah.length} bagian muatan dari aplikasi HP diimpor.`); buka('laporan');
    } catch (e) { toast('Berkas tidak dikenali. Gunakan CSV dari tombol unduh di aplikasi SORA.'); }
  };
  rd.readAsText(file, 'utf-8');
}

// ------------------------------------------------------------------ router dan kerangka
let halaman = 'ringkasan';
function buka(p) {
  if (!PAGES[p]) p = 'ringkasan';
  halaman = p;
  bersihkan();
  $$('#nav a').forEach(a => a.classList.toggle('on', a.dataset.p === p));
  document.title = `${JUDUL[p]} · SORA`;
  const wrap = $('#pages'); wrap.innerHTML = `<div class="page p-${p}" id="pg"></div>`;
  wrap.scrollTop = 0; window.scrollTo(0, 0);
  sinkronHeader();
  PAGES[p]($('#pg'));
}
function sinkronHeader() {
  $$('#gHari button').forEach(b => b.classList.toggle('on', +b.dataset.h === G.hari));
  $('#gJenis').value = G.jenis;
  const p = periode(); $('#pillPeriod').textContent = `Periode ${tglPanjang(p.dari)} – ${tglPanjang(p.sampai)}`;
}
function masuk(akun) {
  sesi.set(akun);
  $('#login').hidden = true; $('#app').hidden = false;
  $('#whoName').textContent = akun.nama; $('#whoRole').textContent = akun.peran; $('#whoAv').textContent = akun.av;
  sinkronHeader();
  buka((location.hash || '#ringkasan').slice(1));
}
function keluar() { sesi.set(null); bersihkan(); $('#app').hidden = true; $('#login').hidden = false; history.replaceState(null, '', '#'); }
function siapkanLogin() {
  $('#demoRow').innerHTML = AKUN.map(a => `<button type="button" class="chip-btn" data-u="${a.u}"><b>${a.nama}</b><small>${a.u}</small></button>`).join('');
  $$('#demoRow button').forEach(b => b.onclick = () => { $('#lgUser').value = b.dataset.u; $('#lgPass').value = SANDI_DEMO; $('#lgErr').textContent = ''; $('#loginForm').requestSubmit(); });
  $('#lgEye').onclick = () => { const p = $('#lgPass'); p.type = p.type === 'password' ? 'text' : 'password'; };
  $('#loginForm').addEventListener('submit', e => {
    e.preventDefault();
    const u = $('#lgUser').value.trim().toLowerCase(), p = $('#lgPass').value, akun = AKUN.find(a => a.u === u);
    if (!u || !p) { $('#lgErr').textContent = 'Isi nama pengguna dan kata sandi.'; return; }
    if (!akun || p !== SANDI_DEMO) { $('#lgErr').textContent = 'Nama pengguna atau kata sandi salah.'; return; }
    masuk(akun);
  });
}
async function mulai() {
  // Komponen Streamlit: beri tahu bahwa komponen siap.
  if (window.parent !== window) {
    const kirim = (type, extra = {}) => window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, extra), '*');
    kirim('streamlit:componentReady', { apiVersion: 1 });
    window.addEventListener('message', e => { if (e.data && e.data.type === 'streamlit:render') kirim('streamlit:setFrameHeight', { height: window.innerHeight }); });
  }
  siapkanLogin();
  try {
    const res = await fetch('data/sora_demo.json', { cache: 'no-cache' });
    siapkanData(await res.json());
  } catch (e) {
    document.body.innerHTML = '<p style="padding:40px;font-family:sans-serif">Data dashboard gagal dimuat. Muat ulang halaman.</p>'; return;
  }
  $('#gJenis').innerHTML = `<option value="semua">Semua jenis TPS</option>${Object.entries(JENIS).slice(0, 3).map(([k, v]) => `<option value="${k}">TPS ${v.toLowerCase()}</option>`).join('')}`;
  $$('#gHari button').forEach(b => b.onclick = () => { G.hari = +b.dataset.h; FL.dari = ''; sinkronHeader(); buka(halaman); });
  $('#gJenis').onchange = e => { G.jenis = e.target.value; FL.jenis = G.jenis; sinkronHeader(); buka(halaman); };
  $('#btnOut').onclick = keluar;
  window.addEventListener('hashchange', () => { if (!$('#app').hidden) buka(location.hash.slice(1)); });
  const s = sesi.get();
  if (s && AKUN.some(a => a.u === s.u)) masuk(s); else { $('#login').hidden = false; }
}
mulai();
})();
