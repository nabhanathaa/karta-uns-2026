/* SORA · Dashboard pemangku kebijakan.
   Semua rumus dan ambang sama dengan aplikasi petugas (karta-mobile) dan lampiran Bab 3. */
(() => {
'use strict';

// ------------------------------------------------------------------ konstanta
const RUTE = {
  U: { nama: 'Gasifikasi', lengkap: 'Umpan gasifikasi langsung', tujuan: 'Reaktor gasifikasi (Zona U)', warna: '#2865e8', syarat: 'Batas atas kadar air ≤ 20%' },
  B: { nama: 'Bio-drying', lengkap: 'Pengeringan dengan serbuk kayu', tujuan: 'Bak bio-drying (Zona B)', warna: '#b56308', syarat: 'Kadar air di atas 20% dan di bawah 65%' },
  M: { nama: 'Maggot & kompos', lengkap: 'Biokonversi organik basah', tujuan: 'Unit maggot BSF & kompos (Zona M)', warna: '#078879', syarat: 'Kadar air ≥ 60%, organik ≥ 60%, plastik ≤ 5%' },
  R: { nama: 'Residu', lengkap: 'Ditahan atau residu', tujuan: 'Area residu (Zona R)', warna: '#5b6577', syarat: 'Inert ≥ 20%, atau sangat basah dan tercampur' },
};
const RK = ['U', 'B', 'M', 'R'];
const FR = [
  { k: 'org', n: 'Organik basah', c: '#11a792' }, { k: 'pla', n: 'Plastik', c: '#527df0' },
  { k: 'ker', n: 'Kertas & kardus', c: '#e7b34b' }, { k: 'tek', n: 'Tekstil', c: '#b09be8' },
  { k: 'kay', n: 'Kayu & ranting', c: '#b88963' }, { k: 'ine', n: 'Inert', c: '#9ba8ba' },
];
const JENIS = { pasar: 'Pasar', permukiman: 'Permukiman', ruang_publik: 'Ruang publik', lainnya: 'Lainnya' };
const AKUN = [
  { u: 'kepala.dlh', nama: 'Kepala DLH', peran: 'DLH Kota Surakarta', av: 'KD' },
  { u: 'direksi.pltsa', nama: 'Direksi PLTSa', peran: 'PLTSa Putri Cempo', av: 'DP' },
  { u: 'analis', nama: 'Analis Data', peran: 'Bidang Pengelolaan Sampah', av: 'AD' },
];
const SANDI_DEMO = 'sora2026';
const FONT = "'Plus Jakarta Sans',system-ui,sans-serif";

// ------------------------------------------------------------------ util
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const nf = (d = 0) => new Intl.NumberFormat('id-ID', { minimumFractionDigits: d, maximumFractionDigits: d });
const f0 = v => nf(0).format(v), f1 = v => nf(1).format(v), f2 = v => nf(2).format(v);
const sum = (a, g = x => x) => a.reduce((s, x) => s + (+g(x) || 0), 0);
const wavg = (a, g, w = x => x.ton) => { const W = sum(a, w); return W ? sum(a, x => g(x) * w(x)) / W : 0; };
const groupBy = (a, g) => a.reduce((m, x) => ((m[g(x)] ||= []).push(x), m), {});
const tgl = t => t.slice(0, 10);
const hariID = d => new Date(d + 'T00:00').toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
const tglPanjang = d => new Date(d + 'T00:00').toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' });
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ico = (id, cls = 'ico') => `<svg class="${cls}"><use href="#i-${id}"/></svg>`;
const rb = r => `<span class="rb ${r}">${r} · ${RUTE[r].nama}</span>`;
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
    const end = +el.dataset.count, d = +(el.dataset.dec || 0), t0 = performance.now(), dur = 900;
    const step = now => { const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3); el.textContent = nf(d).format(end * e); if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  });
}

// ------------------------------------------------------------------ data
const S = { data: null, semua: [], tps: [], tpsBy: {}, impor: store.get('sora-impor', []), charts: [], map: null, timer: null };

function siapkanData(d) {
  S.data = d;
  S.tps = d.tps.slice();
  S.tpsBy = Object.fromEntries(S.tps.map(t => [t.kode, t]));
  gabungImpor();
}
function gabungImpor() {
  S.impor.forEach(m => { if (!S.tpsBy[m.tps]) { const t = { kode: m.tps, nama: m.tpsNama || m.tps, kecamatan: '-', tipe: m.tipe || 'lainnya', lat: null, lon: null }; S.tps.push(t); S.tpsBy[t.kode] = t; } });
  S.semua = S.data.muatan.concat(S.impor).sort((a, b) => a.t < b.t ? -1 : 1);
  const n = S.impor.length, b = $('#navImport');
  if (b) { b.hidden = !n; b.textContent = n; }
}
const tanggalAkhir = () => tgl(S.semua[S.semua.length - 1].t);
const tanggalAwal = () => tgl(S.semua[0].t);
function geserHari(d, n) { const x = new Date(d + 'T12:00'); x.setDate(x.getDate() + n); return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`; }
// Waktu dari HP berformat ISO UTC (akhiran Z). Tampilkan selalu dalam WIB, apa pun zona waktu peramban.
function waktuWIB(s) {
  s = String(s || '').trim();
  const m = s.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/);
  if (m && !/(Z|[+-]\d{2}:?\d{2})$/i.test(s)) return `${m[1]}T${m[2]}`;
  const t = new Date(s);
  return isNaN(t) ? null : new Date(t.getTime() + 7 * 3600e3).toISOString().slice(0, 16);
}
function saring(f = {}) {
  return S.semua.filter(m => (!f.tps || f.tps === 'semua' || m.tps === f.tps)
    && (!f.jenis || f.jenis === 'semua' || (S.tpsBy[m.tps]?.tipe === f.jenis))
    && (!f.rute || f.rute === 'semua' || m.rute === f.rute)
    && (!f.dari || tgl(m.t) >= f.dari) && (!f.sampai || tgl(m.t) <= f.sampai)
    && (!f.q || (m.id + ' ' + m.pelat + ' ' + (S.tpsBy[m.tps]?.nama || '')).toLowerCase().includes(f.q.toLowerCase())));
}
function ringkas(a) {
  const ton = sum(a, x => x.ton), byR = Object.fromEntries(RK.map(r => [r, sum(a.filter(x => x.rute === r), x => x.ton)]));
  return { n: a.length, ton, w: wavg(a, x => x.w), lhv: wavg(a, x => x.lhv), byR, pR: ton ? byR.R / ton * 100 : 0, cek: a.filter(x => x.cek).length,
    org: wavg(a, x => x.org), ine: wavg(a, x => x.ine) };
}
function perTps(a) {
  const g = groupBy(a, x => x.tps);
  return Object.entries(g).map(([k, v]) => ({ t: S.tpsBy[k], ...ringkas(v), rows: v })).sort((x, y) => y.ton - x.ton);
}

// ------------------------------------------------------------------ chart helpers
function chart(el, opt) {
  const c = echarts.init(el, null, { renderer: 'canvas' });
  c.setOption(Object.assign({
    textStyle: { fontFamily: FONT, color: '#2a3654' }, animationDuration: 900, animationEasing: 'cubicOut',
    tooltip: { trigger: 'axis', backgroundColor: '#0c1d45', borderWidth: 0, padding: [10, 14], textStyle: { color: '#fff', fontFamily: FONT, fontSize: 13 }, axisPointer: { type: 'shadow', shadowStyle: { color: '#2762e80d' } } },
    grid: { left: 12, right: 18, top: 44, bottom: 10, containLabel: true },
    legend: { top: 0, left: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 12, textStyle: { fontSize: 13, color: '#5f6c86' } },
  }, opt));
  S.charts.push(c);
  return c;
}
const axisCat = data => ({ type: 'category', data, axisLine: { lineStyle: { color: '#d7deeb' } }, axisTick: { show: false }, axisLabel: { color: '#5f6c86', fontSize: 12.5 } });
const axisVal = (name, extra = {}) => Object.assign({ type: 'value', name, nameTextStyle: { color: '#8a96ad', fontSize: 12, align: 'left' }, splitLine: { lineStyle: { color: '#eef1f7' } }, axisLabel: { color: '#5f6c86', fontSize: 12.5 } }, extra);
function bersihkan() {
  S.charts.forEach(c => c.dispose()); S.charts = [];
  if (S.map) { S.map.remove(); S.map = null; }
  clearInterval(S.timer);
}
window.addEventListener('resize', () => S.charts.forEach(c => c.resize()));

// ------------------------------------------------------------------ halaman
const PAGES = {};
const JUDUL = { beranda: 'Beranda', muatan: 'Muatan masuk', peta: 'Peta TPS', komposisi: 'Komposisi sampah', rute: 'Rute dan neraca', model: 'Model dan validasi', laporan: 'Pusat laporan' };

function kpi({ label, icon, value, dec = 0, unit = '', foot = '', accent = 'var(--blue)' }) {
  return `<div class="kpi" style="--accent:${accent}"><div class="label">${label}<span class="ico-wrap">${ico(icon)}</span></div>
    <div class="value num"><span data-count="${value}" data-dec="${dec}">0</span>${unit ? `<small>${unit}</small>` : ''}</div><div class="foot">${foot}</div></div>`;
}
function catatanSimulasi() {
  return `<div class="notice">${ico('alert')}<div><b>Data simulasi.</b> Belum ada data lapangan, sehingga dashboard memakai data bangkitan komputer untuk ${S.data.tps.length} TPS selama ${hariPeriode()} hari. Rumus kadar air, nilai kalor, dan aturan rute sama dengan aplikasi petugas. Angka di sini menunjukkan cara kerja sistem, bukan kondisi sebenarnya. Data dari aplikasi HP bisa diimpor di <a href="#laporan">Pusat laporan</a>.</div></div>`;
}
const hariPeriode = () => Math.round((new Date(tanggalAkhir()) - new Date(tanggalAwal())) / 864e5) + 1;

// ---------------------------------------------------------------- Beranda
PAGES.beranda = el => {
  const akhir = tanggalAkhir(), hariIni = saring({ dari: akhir, sampai: akhir }), rh = ringkas(hariIni);
  const all = ringkas(S.semua), user = sesi.get();
  const share = RK.map(r => rh.ton ? rh.byR[r] / rh.ton * 100 : 0);
  const prioritas = perTps(saring({ dari: geserHari(akhir, -13), sampai: akhir })).sort((a, b) => b.pR - a.pR).slice(0, 5);
  el.innerHTML = `
  <section class="hero">
    <div>
      <div class="eyebrow" style="color:#f2d79e">Selamat datang, ${esc(user?.nama || 'Pengguna')}</div>
      <h1>Setiap truk terukur <em>sebelum</em> masuk reaktor.</h1>
      <p>SORA membaca komposisi sampah dari foto muatan, menaksir kadar air dan nilai kalornya, lalu merekomendasikan jalur pengolahan. Petugas tetap memegang keputusan akhir.</p>
      <div class="actions"><a class="btn btn-gold" href="#muatan">Buka muatan masuk ${ico('arrow-r')}</a><a class="btn btn-light" href="#peta">${ico('map')} Lihat peta TPS</a></div>
    </div>
    <div class="glass">
      <div class="eyebrow"><i class="dot" style="width:8px;height:8px;border-radius:50%;background:#5fe3b5;display:inline-block"></i> Muatan hari terakhir · ${tglPanjang(akhir)}</div>
      <div class="big num"><span data-count="${rh.n}">0</span><small>truk · ${f1(rh.ton)} ton</small></div>
      <div class="route-strip">${RK.map((r, i) => `<i style="width:0;background:${RUTE[r].warna}" data-w="${share[i]}"></i>`).join('')}</div>
      <div class="route-legend">${RK.map((r, i) => `<div title="${RUTE[r].nama}"><span class="rk"><i style="background:${RUTE[r].warna}"></i>Rute ${r}</span><small>${RUTE[r].nama}</small><b class="num">${f0(share[i])}%</b></div>`).join('')}</div>
    </div>
  </section>
  <div class="kpis">
    ${kpi({ label: 'Tonase dianalisis', icon: 'scale', value: all.ton, unit: 'ton', foot: `<b>${f0(all.n)}</b> muatan dari ${S.data.tps.length} TPS · ${hariPeriode()} hari` })}
    ${kpi({ label: 'Rata-rata kadar air', icon: 'drop', value: all.w, dec: 1, unit: '%', accent: '#078879', foot: 'Syarat umpan reaktor <b>≤ 20%</b>' })}
    ${kpi({ label: 'Nilai kalor (LHV)', icon: 'zap', value: all.lhv, dec: 2, unit: 'MJ/kg', accent: '#c9973f', foot: `Setara <b>${f0(all.lhv * 1000 * 0.2 / 3.6)}</b> kWh/ton (efisiensi 20%)` })}
    ${kpi({ label: 'Perlu perhatian', icon: 'alert', value: all.n ? (S.semua.filter(x => x.rute === 'R').length) : 0, unit: 'muatan', accent: '#5b6577', foot: `Rute R · <b>${f0(all.cek)}</b> perlu cek manual` })}
  </div>
  ${catatanSimulasi()}
  <div class="grid g-21 mb">
    <div class="panel"><div class="panel-head"><div><h3>Tonase harian per rute</h3><p>14 hari terakhir. Sebagian besar muatan perlu dikeringkan dulu sebelum layak menjadi umpan reaktor.</p></div></div><div class="chart" id="cTon"></div></div>
    <div class="panel"><div class="panel-head"><div><h3>TPS prioritas pembinaan</h3><p>Porsi tonase ke Rute R (residu), 14 hari terakhir</p></div></div>
      <div class="rank">${prioritas.map((p, i) => `<button onclick="location.hash='peta'"><span class="no">${i + 1}</span><span><b>${esc(p.t.nama)}</b><small>${JENIS[p.t.tipe] || ''} · ${f0(p.n)} muatan · ${f1(p.ton)} ton</small></span><span class="v num">${f0(p.pR)}%</span></button>`).join('')}</div></div>
  </div>
  <div class="section-label">Eksplorasi</div>
  <div class="section-title">Pilih modul kerja <small>06 MODUL</small></div>
  <div class="modules">
    ${[['muatan', 'truck', 'Muatan masuk', 'Log setiap truk: komposisi, kadar air dan rentangnya, nilai kalor, serta rute.'],
       ['peta', 'map', 'Peta TPS', 'Sebaran TPS asal, mutu sampahnya, dan alur muatan menuju PLTSa Putri Cempo.'],
       ['komposisi', 'pie', 'Komposisi sampah', 'Fraksi organik, plastik, kertas, tekstil, kayu, dan inert per TPS.'],
       ['rute', 'route', 'Rute dan neraca', 'Aturan rute, tonase per jalur, kebutuhan serbuk kayu, dan potensi energi.'],
       ['model', 'flask', 'Model dan validasi', 'Status model, rencana data latih dan uji, serta kriteria lulus evaluasi.'],
       ['laporan', 'file', 'Pusat laporan', 'Saring per TPS dan tanggal, unduh Excel atau PDF, impor data dari HP.']]
      .map(([h, i, j, p]) => `<a class="module" href="#${h}" style="text-decoration:none;color:inherit"><span class="m-ico">${ico(i)}</span><h4>${j}</h4><p>${p}</p><span class="arrow">${ico('arrow-ur')}</span></a>`).join('')}
  </div>
  <div class="section-label">Cara kerja</div>
  <div class="section-title">Alur SORA dari gerbang sampai laporan</div>
  <div class="steps">
    ${[['Foto muatan', 'Petugas memindai muatan di gerbang dengan kamera HP atau kamera konveyor.'],
       ['Segmentasi', 'Model DeepLabv3+ memberi label setiap piksel: organik, plastik, kertas, tekstil, kayu, inert.'],
       ['Kadar air & kalor', 'Neraca massa dan koreksi hujan memberi kadar air beserta rentangnya; nilai kalor dihitung dengan rumus ISO.'],
       ['Rekomendasi rute', 'Aturan U, B, M, R diperiksa berurutan. Petugas menyetujui atau mengganti dengan alasan.'],
       ['Laporan kebijakan', 'Data terkumpul per TPS untuk pembinaan pemilahan di sumber dan perencanaan PLTSa.']]
      .map(([j, p], i) => `<div class="step"><div class="n">LANGKAH 0${i + 1}</div><h4>${j}</h4><p>${p}</p></div>`).join('')}
  </div>`;
  countUp(el);
  requestAnimationFrame(() => $$('.route-strip i', el).forEach(i => i.style.width = i.dataset.w + '%'));
  const hari = [...Array(14)].map((_, i) => geserHari(akhir, i - 13));
  const g = groupBy(saring({ dari: hari[0], sampai: akhir }), x => tgl(x.t));
  chart($('#cTon'), {
    xAxis: axisCat(hari.map(hariID)), yAxis: axisVal('ton'),
    series: RK.map(r => ({ name: `${r} · ${RUTE[r].nama}`, type: 'bar', stack: 't', barWidth: '56%', itemStyle: { color: RUTE[r].warna, borderRadius: r === 'R' ? [5, 5, 0, 0] : 0 }, data: hari.map(d => +sum((g[d] || []).filter(x => x.rute === r), x => x.ton).toFixed(1)) })),
  });
};

// ---------------------------------------------------------------- Muatan masuk
const FM = { tps: 'semua', jenis: 'semua', rute: 'semua', dari: '', sampai: '', q: '', hal: 1 };
function filterBar(F, onChange, { cari = false } = {}) {
  const opsiTps = `<option value="semua">Semua TPS</option>` + S.tps.map(t => `<option value="${t.kode}">${esc(t.nama)}</option>`).join('');
  return `<div class="filters no-print" data-filter>
    <div class="f"><label>TPS asal</label><select class="select" data-k="tps">${opsiTps}</select></div>
    <div class="f"><label>Jenis TPS</label><select class="select" data-k="jenis"><option value="semua">Semua jenis</option>${Object.entries(JENIS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></div>
    <div class="f"><label>Rute</label><select class="select" data-k="rute"><option value="semua">Semua rute</option>${RK.map(r => `<option value="${r}">${r} · ${RUTE[r].nama}</option>`).join('')}</select></div>
    <div class="f"><label>Dari tanggal</label><input type="date" class="date" data-k="dari" min="${tanggalAwal()}" max="${tanggalAkhir()}"></div>
    <div class="f"><label>Sampai tanggal</label><input type="date" class="date" data-k="sampai" min="${tanggalAwal()}" max="${tanggalAkhir()}"></div>
    ${cari ? `<div class="f"><label>Cari</label><input class="search" data-k="q" placeholder="ID, pelat, atau TPS"></div>` : ''}
    <div class="f act"><button class="btn btn-ghost" data-reset>${ico('filter')} Atur ulang</button></div>
  </div>`;
}
function ikatFilter(el, F, onChange, def) {
  const bar = $('[data-filter]', el);
  $$('[data-k]', bar).forEach(i => { i.value = F[i.dataset.k] || (i.tagName === 'SELECT' ? 'semua' : ''); i.addEventListener(i.dataset.k === 'q' ? 'input' : 'change', () => { F[i.dataset.k] = i.value; F.hal = 1; onChange(); }); });
  $('[data-reset]', bar).addEventListener('click', () => { Object.assign(F, def()); $$('[data-k]', bar).forEach(i => i.value = F[i.dataset.k] || (i.tagName === 'SELECT' ? 'semua' : '')); onChange(); });
}
PAGES.muatan = el => {
  if (!FM.dari) { FM.dari = geserHari(tanggalAkhir(), -13); FM.sampai = tanggalAkhir(); }
  el.innerHTML = `
  <div class="banner"><div class="eyebrow">Pemantauan · log gerbang</div><h1>Muatan masuk</h1>
    <p>Setiap baris adalah satu muatan yang dianalisis: komposisi berat, kadar air beserta rentang 80%, nilai kalor bersih, dan rute yang direkomendasikan.</p>
    <div class="actions"><button class="btn btn-light" id="mCsv">${ico('down')} Unduh CSV</button></div></div>
  ${filterBar(FM, null, { cari: true })}
  <div class="kpis" id="mKpi"></div>
  <div class="grid g-21 mb">
    <div class="panel"><div class="panel-head"><div><h3>Tonase per hari dan kadar air rata-rata</h3><p>Batang: tonase per rute. Garis: kadar air rata-rata tertimbang tonase.</p></div></div><div class="chart" id="mC1"></div></div>
    <div class="panel"><div class="panel-head"><div><h3>Porsi rute</h3><p>Berdasarkan tonase</p></div></div><div class="chart" id="mC2"></div></div>
  </div>
  <div class="panel mb"><div class="panel-head"><div><h3>Kadar air dan curah hujan</h3><p>Hujan 24 jam sebelum muatan tiba ikut memengaruhi kadar air sampah di TPS terbuka.</p></div></div><div class="chart short" id="mC3"></div></div>
  <div class="panel"><div class="panel-head"><div><h3>Daftar muatan</h3><p id="mInfo"></p></div></div><div class="table-wrap" id="mTab"></div><div class="pager" id="mPager"></div></div>`;
  const def = () => ({ tps: 'semua', jenis: 'semua', rute: 'semua', dari: geserHari(tanggalAkhir(), -13), sampai: tanggalAkhir(), q: '', hal: 1 });
  const gambar = () => {
    S.charts.forEach(c => c.dispose()); S.charts = [];
    const a = saring(FM), r = ringkas(a);
    $('#mKpi').innerHTML = kpi({ label: 'Muatan', icon: 'truck', value: r.n, foot: `${f1(r.ton)} ton` })
      + kpi({ label: 'Kadar air rata-rata', icon: 'drop', value: r.w, dec: 1, unit: '%', accent: '#078879', foot: 'Tertimbang tonase' })
      + kpi({ label: 'Nilai kalor (LHV)', icon: 'zap', value: r.lhv, dec: 2, unit: 'MJ/kg', accent: '#c9973f', foot: 'LHV basis basah' })
      + kpi({ label: 'Ke Rute R', icon: 'alert', value: r.pR, dec: 1, unit: '%', accent: '#5b6577', foot: `${f1(r.byR.R)} ton ditahan` });
    countUp($('#mKpi'));
    const hari = [...new Set(a.map(x => tgl(x.t)))].sort(), g = groupBy(a, x => tgl(x.t));
    chart($('#mC1'), {
      xAxis: axisCat(hari.map(hariID)), yAxis: [axisVal('ton'), axisVal('kadar air %', { position: 'right', min: 0, max: 100, splitLine: { show: false } })],
      series: RK.map(rr => ({ name: rr, type: 'bar', stack: 't', barWidth: '58%', itemStyle: { color: RUTE[rr].warna }, data: hari.map(d => +sum((g[d] || []).filter(x => x.rute === rr), x => x.ton).toFixed(1)) }))
        .concat([{ name: 'Kadar air', type: 'line', yAxisIndex: 1, smooth: true, symbol: 'circle', symbolSize: 7, lineStyle: { width: 3, color: '#0c1d45' }, itemStyle: { color: '#0c1d45' }, data: hari.map(d => +wavg(g[d], x => x.w).toFixed(1)),
          markLine: { symbol: 'none', label: { formatter: 'Syarat reaktor 20%', position: 'insideStartTop', color: '#c2413a', fontWeight: 700 }, lineStyle: { color: '#c2413a', type: 'dashed' }, data: [{ yAxis: 20 }] } }]),
    });
    chart($('#mC2'), {
      tooltip: { trigger: 'item', backgroundColor: '#0c1d45', borderWidth: 0, textStyle: { color: '#fff', fontFamily: FONT }, valueFormatter: v => f1(v) + ' ton' }, legend: { bottom: 0, left: 'center' },
      series: [{ type: 'pie', radius: ['44%', '66%'], center: ['50%', '44%'], minShowLabelAngle: 2, labelLine: { length: 8, length2: 6 }, itemStyle: { borderColor: '#fff', borderWidth: 3, borderRadius: 6 },
        label: { formatter: p => `${p.name.split(' ')[0]}  ${f0(p.percent)}%`, fontWeight: 800, fontSize: 13, overflow: 'none' },
        data: RK.map(rr => ({ name: `${rr} · ${RUTE[rr].nama}`, value: +r.byR[rr].toFixed(1), itemStyle: { color: RUTE[rr].warna } })) }],
    });
    const hujanBy = Object.fromEntries(S.data.hujan.map(h => [h.tanggal, h.mm]));
    chart($('#mC3'), {
      xAxis: axisCat(hari.map(hariID)), yAxis: [axisVal('hujan mm'), axisVal('kadar air %', { position: 'right', min: 30, max: 75, splitLine: { show: false } })],
      series: [{ name: 'Curah hujan harian', type: 'bar', barWidth: '50%', itemStyle: { color: '#9fc0ff', borderRadius: [5, 5, 0, 0] }, data: hari.map(d => hujanBy[d] ?? 0) },
        { name: 'Kadar air rata-rata', type: 'line', yAxisIndex: 1, smooth: true, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#07887933' }, { offset: 1, color: '#07887900' }]) }, lineStyle: { width: 3, color: '#078879' }, itemStyle: { color: '#078879' }, data: hari.map(d => +wavg(g[d], x => x.w).toFixed(1)) }],
    });
    tabel(a);
  };
  const tabel = a => {
    const per = 15, tot = Math.max(1, Math.ceil(a.length / per)); FM.hal = Math.min(FM.hal, tot);
    const rows = a.slice().reverse().slice((FM.hal - 1) * per, FM.hal * per);
    $('#mInfo').textContent = `${f0(a.length)} muatan sesuai saringan, terbaru di atas`;
    $('#mTab').innerHTML = `<table><thead><tr><th>Waktu</th><th>ID muatan</th><th>TPS asal</th><th>Pelat</th><th class="r">Berat</th><th class="r">Kadar air</th><th class="r">Rentang 80%</th><th class="r">LHV</th><th>Komposisi berat</th><th>Rute</th><th>Catatan</th></tr></thead><tbody>${rows.map(m => `<tr>
      <td class="num">${hariID(tgl(m.t))} ${m.t.slice(11, 16)}</td><td class="num"><b>${esc(m.id)}</b></td><td>${esc(S.tpsBy[m.tps]?.nama || m.tps)}</td><td>${esc(m.pelat)}</td>
      <td class="r num">${f2(m.ton)} t</td><td class="r num"><b>${f1(m.w)}%</b></td><td class="r num">${f0(m.wb)}–${f0(m.wa)}%</td><td class="r num">${f2(m.lhv)}</td>
      <td><div class="mini-bar" style="width:140px;display:flex">${FR.map(x => `<i style="width:${m[x.k]}%;background:${x.c};border-radius:0"></i>`).join('')}</div></td>
      <td>${rb(m.rute)}</td><td>${m.cek ? '<span class="tag warn">Cek manual</span> ' : ''}${m.sumber === 'aplikasi' ? '<span class="tag app">Dari HP</span>' : ''}</td></tr>`).join('')}</tbody></table>`;
    $('#mPager').innerHTML = `<span>Halaman ${FM.hal} dari ${tot}</span><div class="btns"><button ${FM.hal <= 1 ? 'disabled' : ''} data-p="-1">Sebelumnya</button><button ${FM.hal >= tot ? 'disabled' : ''} data-p="1">Berikutnya</button></div>`;
    $$('#mPager button').forEach(b => b.onclick = () => { FM.hal += +b.dataset.p; tabel(a); });
  };
  ikatFilter(el, FM, gambar, def);
  $('#mCsv').onclick = () => unduhCsv(saring(FM), 'SORA-muatan');
  gambar();
};

// ---------------------------------------------------------------- Peta
const IND = {
  w: { nama: 'Rata-rata kadar air', unit: '%', g: r => r.w, batas: [45, 52, 58], warna: ['#1f9d74', '#9cc65a', '#f0a43a', '#c2413a'], label: ['< 45%', '45–52%', '52–58%', '≥ 58%'], naik: 'buruk' },
  pR: { nama: 'Porsi tonase ke Rute R', unit: '%', g: r => r.pR, batas: [8, 15, 25], warna: ['#1f9d74', '#9cc65a', '#f0a43a', '#c2413a'], label: ['< 8%', '8–15%', '15–25%', '≥ 25%'], naik: 'buruk' },
  lhv: { nama: 'Nilai kalor rata-rata', unit: ' MJ/kg', g: r => r.lhv, batas: [5, 6.5, 8], warna: ['#c9d8fb', '#7ea2f2', '#3a6ee6', '#173aab'], label: ['< 5', '5–6,5', '6,5–8', '≥ 8 MJ/kg'], naik: 'baik' },
  org: { nama: 'Porsi organik basah', unit: '%', g: r => r.org, batas: [50, 62, 72], warna: ['#d6efe6', '#8fd3bd', '#2ba98b', '#0a6e5f'], label: ['< 50%', '50–62%', '62–72%', '≥ 72%'], naik: 'netral' },
  ton: { nama: 'Tonase masuk', unit: ' ton', g: r => r.ton, batas: null, warna: ['#e9d9b8', '#d7b46d', '#b9852f', '#7f5413'], label: null, naik: 'netral' },
};
const FP = { hari: 30, ind: 'w', jenis: 'semua', alur: true, label: innerWidth >= 640 };
PAGES.peta = el => {
  el.innerHTML = `
  <div class="page-head"><div><h1>Peta TPS</h1><p>Sebaran TPS asal, mutu sampah yang dikirim, dan alur muatan menuju PLTSa Putri Cempo. Lingkaran makin besar berarti tonase makin banyak.</p></div></div>
  <div class="map-layout">
    <div class="map-side">
      <h3>${ico('filter')} Filter peta</h3>
      <div class="f"><label>Periode</label><div class="seg" id="pHari">${[7, 14, 30].map(h => `<button data-h="${h}" class="${FP.hari === h ? 'on' : ''}">${h} hari</button>`).join('')}</div></div>
      <div class="f"><label>Indikator warna</label><select class="select" id="pInd">${Object.entries(IND).map(([k, v]) => `<option value="${k}">${v.nama}</option>`).join('')}</select></div>
      <div class="f"><label>Jenis TPS</label><select class="select" id="pJenis"><option value="semua">Semua jenis</option>${Object.entries(JENIS).slice(0, 3).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></div>
      <label class="toggle">Tampilkan alur ke PLTSa<span class="switch"><input type="checkbox" id="pAlur" ${FP.alur ? 'checked' : ''}><i></i></span></label>
      <label class="toggle">Tampilkan nama TPS<span class="switch"><input type="checkbox" id="pLabel" ${FP.label ? 'checked' : ''}><i></i></span></label>
      <div><div class="section-label" style="margin:4px 0 10px">Peringkat TPS</div><div class="rank" id="pRank"></div></div>
      <p class="ref">Koordinat TPS adalah perkiraan dan perlu dicek ulang bersama DLH.</p>
    </div>
    <div class="map-wrap"><div id="map"></div>
      <div class="map-float map-title" id="pTitle"></div>
      <div class="map-float map-legend" id="pLegend"></div>
      <div class="map-float map-stat" id="pStat"></div>
    </div>
  </div>`;
  $('#pInd').value = FP.ind; $('#pJenis').value = FP.jenis;
  const map = S.map = L.map('map', { zoomControl: true, attributionControl: true, scrollWheelZoom: true }).setView([-7.558, 110.826], 13);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { subdomains: 'abcd', maxZoom: 19, attribution: '© OpenStreetMap · © CARTO' }).addTo(map);
  map.zoomControl.setPosition('bottomleft');
  const lapisan = L.layerGroup().addTo(map), marker = {};
  const P = S.data.pltsa;
  L.marker([P.lat, P.lon], { icon: L.divIcon({ className: '', html: '<div class="pltsa-pin">PLTSa</div>', iconSize: [46, 46], iconAnchor: [23, 23] }), zIndexOffset: 1000 })
    .addTo(map).bindPopup(`<div class="pop"><h4>${esc(P.nama)}</h4><div class="meta">${esc(P.alamat)}</div><p>Titik penerimaan semua muatan. Reaktor gasifikasi mensyaratkan umpan berkadar air maksimal 20%.</p></div>`);
  const gambar = () => {
    lapisan.clearLayers();
    const akhir = tanggalAkhir(), a = saring({ dari: geserHari(akhir, -(FP.hari - 1)), sampai: akhir, jenis: FP.jenis });
    const rows = perTps(a).filter(r => r.t && r.t.lat != null), I = IND[FP.ind];
    let batas = I.batas;
    if (!batas) { const v = rows.map(r => r.ton).sort((x, y) => x - y), q = p => v[Math.floor((v.length - 1) * p)] || 0; batas = [q(.25), q(.5), q(.75)]; }
    const kelas = v => v < batas[0] ? 0 : v < batas[1] ? 1 : v < batas[2] ? 2 : 3;
    const maxTon = Math.max(1, ...rows.map(r => r.ton));
    rows.forEach(r => {
      const v = I.g(r), c = I.warna[kelas(v)], rad = 7 + 13 * Math.sqrt(r.ton / maxTon);
      if (FP.alur) L.polyline([[r.t.lat, r.t.lon], [P.lat, P.lon]], { color: c, weight: 2.5, opacity: .75, className: 'flow' }).addTo(lapisan);
      L.circleMarker([r.t.lat, r.t.lon], { radius: rad + 6, stroke: false, fillColor: c, fillOpacity: .16, interactive: false }).addTo(lapisan);
      const mk = L.circleMarker([r.t.lat, r.t.lon], { radius: rad, color: '#fff', weight: 3, fillColor: c, fillOpacity: .95 }).addTo(lapisan);
      const fr = FR.map(x => `<i style="display:block;width:${wavg(r.rows, m => m[x.k])}%;background:${x.c}"></i>`).join('');
      mk.bindPopup(`<div class="pop"><h4>${esc(r.t.nama)}</h4><div class="meta">${JENIS[r.t.tipe] || ''} · Kec. ${esc(r.t.kecamatan)} · ${f1(r.t.jarak_km)} km ke PLTSa</div>
        <div class="kv"><span>Muatan</span><b>${f0(r.n)} truk</b><span>Tonase</span><b>${f1(r.ton)} ton</b><span>Kadar air rata-rata</span><b>${f1(r.w)}%</b><span>Nilai kalor rata-rata</span><b>${f2(r.lhv)} MJ/kg</b><span>Ke Rute R</span><b>${f1(r.pR)}%</b></div>
        <div class="stack">${fr}</div><small style="color:#5f6c86">Komposisi berat: organik ${f0(r.org)}%, inert ${f0(r.ine)}%</small></div>`);
      if (FP.label) mk.bindTooltip(r.t.nama.replace('TPS ', ''), { permanent: true, direction: 'top', offset: [0, -rad], className: 'tlabel' });
      marker[r.t.kode] = mk;
    });
    $('#pTitle').textContent = `${I.nama} per TPS · ${FP.hari} hari terakhir`;
    const lbl = I.label || batas.map((b, i) => i === 0 ? `< ${f0(b)} ton` : `${f0(batas[i - 1])}–${f0(b)} ton`).concat([`≥ ${f0(batas[2])} ton`]);
    $('#pLegend').innerHTML = `<h5>${I.nama}</h5>${I.warna.map((c, i) => `<div class="row"><span class="sw" style="background:${c}"></span>${lbl[i]}</div>`).join('')}<div class="row" style="margin-top:8px"><span class="sw" style="background:linear-gradient(140deg,#0c1d45,#2762e8)"></span>PLTSa Putri Cempo</div><div class="note">Ukuran lingkaran sebanding dengan tonase. ${I.naik === 'buruk' ? 'Warna merah perlu perhatian.' : ''}</div>`;
    const rr = ringkas(a);
    $('#pStat').innerHTML = `<div class="k">Ringkasan ${FP.hari} hari</div><div class="v num">${f0(rr.ton)} ton</div><div class="ref">${f0(rr.n)} muatan · kadar air ${f1(rr.w)}% · ${f1(rr.pR)}% ke Rute R</div>`;
    const urut = rows.slice().sort((x, y) => I.naik === 'baik' ? I.g(x) - I.g(y) : I.g(y) - I.g(x));
    $('#pRank').innerHTML = urut.map((r, i) => `<button data-k="${r.t.kode}"><span class="no" style="background:${I.warna[kelas(I.g(r))]}22;color:${I.warna[kelas(I.g(r))]}">${i + 1}</span><span><b>${esc(r.t.nama)}</b><small>${JENIS[r.t.tipe] || ''} · ${f1(r.ton)} ton</small></span><span class="v num">${FP.ind === 'lhv' ? f2(I.g(r)) : f1(I.g(r))}${I.unit.trim() === '%' ? '%' : ''}</span></button>`).join('');
    $$('#pRank button').forEach(b => b.onclick = () => { const m = marker[b.dataset.k]; if (m) { map.flyTo(m.getLatLng(), 15, { duration: .9 }); setTimeout(() => m.openPopup(), 900); } });
  };
  $$('#pHari button').forEach(b => b.onclick = () => { FP.hari = +b.dataset.h; $$('#pHari button').forEach(x => x.classList.toggle('on', x === b)); gambar(); });
  $('#pInd').onchange = e => { FP.ind = e.target.value; gambar(); };
  $('#pJenis').onchange = e => { FP.jenis = e.target.value; gambar(); };
  $('#pAlur').onchange = e => { FP.alur = e.target.checked; gambar(); };
  $('#pLabel').onchange = e => { FP.label = e.target.checked; gambar(); };
  gambar();
  const pas = () => {
    const kecil = innerWidth < 960;
    map.invalidateSize();
    map.fitBounds(L.latLngBounds(S.data.tps.map(t => [t.lat, t.lon]).concat([[P.lat, P.lon]])),
      { paddingTopLeft: kecil ? [24, 70] : [60, 80], paddingBottomRight: kecil ? [24, 110] : [300, 60], maxZoom: 14 });
  };
  setTimeout(pas, 200);
};

// ---------------------------------------------------------------- Komposisi
const FK = { hari: 30, jenis: 'semua' };
PAGES.komposisi = el => {
  el.innerHTML = `
  <div class="page-head"><div><h1>Komposisi sampah</h1><p>Komposisi berat hasil segmentasi foto, setelah luas di foto dikonversi menjadi berat. Plastik tampak luas di foto, tetapi ringan.</p></div>
    <div class="filters no-print" style="margin:0;padding:12px 14px">
      <div class="f" style="min-width:150px"><label>Periode</label><select class="select" id="kHari">${[7, 14, 30].map(h => `<option value="${h}">${h} hari terakhir</option>`).join('')}</select></div>
      <div class="f" style="min-width:150px"><label>Jenis TPS</label><select class="select" id="kJenis"><option value="semua">Semua jenis</option>${Object.entries(JENIS).slice(0, 3).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></div>
    </div></div>
  <div class="grid g-12 mb">
    <div class="panel"><div class="panel-head"><div><h3>Komposisi keseluruhan</h3><p>Tertimbang tonase</p></div></div><div class="chart tall" id="kC1"></div></div>
    <div class="panel"><div class="panel-head"><div><h3>Komposisi per TPS</h3><p>Persen berat, diurutkan dari porsi organik terbesar</p></div></div><div class="chart tall" id="kC2"></div></div>
  </div>
  <div class="grid g-2">
    <div class="panel"><div class="panel-head"><div><h3>Organik dan kadar air</h3><p>Setiap titik satu muatan. Makin banyak organik, makin basah.</p></div></div><div class="chart" id="kC3"></div></div>
    <div class="panel"><div class="panel-head"><div><h3>Sebaran nilai kalor</h3><p>Jumlah muatan per kelas LHV, menurut rute</p></div></div><div class="chart" id="kC4"></div></div>
  </div>`;
  $('#kHari').value = FK.hari; $('#kJenis').value = FK.jenis;
  const gambar = () => {
    S.charts.forEach(c => c.dispose()); S.charts = [];
    const akhir = tanggalAkhir(), a = saring({ dari: geserHari(akhir, -(FK.hari - 1)), sampai: akhir, jenis: FK.jenis });
    chart($('#kC1'), {
      tooltip: { trigger: 'item', backgroundColor: '#0c1d45', borderWidth: 0, textStyle: { color: '#fff', fontFamily: FONT }, valueFormatter: v => f1(v) + '%' }, legend: { bottom: 0, left: 'center' },
      series: [{ type: 'pie', radius: ['42%', '64%'], center: ['50%', '44%'], minShowLabelAngle: 2, itemStyle: { borderColor: '#fff', borderWidth: 3, borderRadius: 6 }, label: { formatter: p => f1(p.percent) + '%', fontWeight: 800, fontSize: 13, overflow: 'none' }, labelLine: { length: 10, length2: 8 },
        data: FR.map(x => ({ name: x.n, value: +wavg(a, m => m[x.k]).toFixed(1), itemStyle: { color: x.c } })) }],
    });
    const rows = perTps(a).sort((x, y) => x.org - y.org);
    chart($('#kC2'), {
      grid: { left: 12, right: 18, top: 44, bottom: 10, containLabel: true },
      xAxis: axisVal('%', { max: 100 }), yAxis: Object.assign(axisCat(rows.map(r => r.t.nama.replace('TPS ', ''))), { axisLabel: { color: '#2a3654', fontSize: 13, fontWeight: 600 } }),
      tooltip: { trigger: 'axis', backgroundColor: '#0c1d45', borderWidth: 0, textStyle: { color: '#fff', fontFamily: FONT }, valueFormatter: v => f1(v) + '%' },
      series: FR.map(x => ({ name: x.n, type: 'bar', stack: 'k', barWidth: '62%', itemStyle: { color: x.c }, data: rows.map(r => +wavg(r.rows, m => m[x.k]).toFixed(1)) })),
    });
    const sampel = a.length > 700 ? a.filter((_, i) => i % Math.ceil(a.length / 700) === 0) : a;
    chart($('#kC3'), {
      tooltip: { trigger: 'item', backgroundColor: '#0c1d45', borderWidth: 0, textStyle: { color: '#fff', fontFamily: FONT }, formatter: p => `${p.seriesName}<br>Organik ${f1(p.value[0])}% · kadar air ${f1(p.value[1])}%` },
      xAxis: axisVal('organik basah %', { min: 0, max: 100, nameLocation: 'end' }), yAxis: axisVal('kadar air %', { min: 0, max: 90 }),
      series: RK.map(r => ({ name: `${r} · ${RUTE[r].nama}`, type: 'scatter', symbolSize: 8, itemStyle: { color: RUTE[r].warna, opacity: .7 }, data: sampel.filter(m => m.rute === r).map(m => [m.org, m.w]) })),
    });
    const kelas = [0, 2, 4, 6, 8, 10, 12, 14, 16], lab = kelas.slice(0, -1).map((k, i) => `${k}–${kelas[i + 1]}`);
    chart($('#kC4'), {
      xAxis: axisCat(lab.map(x => x + ' MJ/kg')), yAxis: axisVal('muatan'),
      series: RK.map(r => ({ name: r, type: 'bar', stack: 'h', itemStyle: { color: RUTE[r].warna }, data: lab.map((_, i) => a.filter(m => m.rute === r && m.lhv >= kelas[i] && m.lhv < kelas[i + 1]).length) })),
    });
  };
  $('#kHari').onchange = e => { FK.hari = +e.target.value; gambar(); };
  $('#kJenis').onchange = e => { FK.jenis = e.target.value; gambar(); };
  gambar();
};

// ---------------------------------------------------------------- Rute & neraca
PAGES.rute = el => {
  const akhir = tanggalAkhir(), dari = geserHari(akhir, -29), a = saring({ dari, sampai: akhir }), r = ringkas(a);
  const B = a.filter(m => m.rute === 'B'), U = a.filter(m => m.rute === 'U');
  const serbuk = sum(B, m => m.ton * m.dosis / 100), airB = sum(B, m => m.ton * Math.max(0, m.w - 20) / 80), mwhU = sum(U, m => m.ton * m.kwh) / 1000;
  el.innerHTML = `
  <div class="page-head"><div><h1>Rute dan neraca</h1><p>Rekomendasi rute untuk ${f0(r.n)} muatan dalam 30 hari terakhir, beserta kebutuhan serbuk kayu dan potensi energi. Petugas dapat mengganti rute dengan alasan tertulis.</p></div></div>
  <div class="route-cards">${RK.map(k => { const ak = a.filter(m => m.rute === k); return `<div class="route-card" data-r="${k}" style="--c:${RUTE[k].warna}">
    <div class="top"><span class="letter">${k}</span><div><h4>${RUTE[k].lengkap}</h4><small>${RUTE[k].tujuan}</small></div></div>
    <div class="v num">${f0(r.byR[k])} <small>ton</small></div><div class="d">${f1(r.ton ? r.byR[k] / r.ton * 100 : 0)}% tonase · ${f0(ak.length)} muatan · kadar air ${f1(wavg(ak, m => m.w))}%</div></div>`; }).join('')}</div>
  <div class="grid g-21 mb">
    <div class="panel"><div class="panel-head"><div><h3>Tonase harian per rute</h3><p>30 hari terakhir</p></div></div><div class="chart tall" id="rC1"></div></div>
    <div class="panel"><div class="panel-head"><div><h3>Aturan rute</h3><p>Diperiksa berurutan dari atas. Aturan pertama yang terpenuhi menjadi rekomendasi.</p></div></div>
      <div class="rules">${[['R', 'Inert ≥ 20%', 'Batu, kaca, dan logam merusak reaktor dan tidak bisa dimakan maggot.'],
        ['U', 'Batas atas kadar air ≤ 20%', 'Memakai batas atas rentang, bukan taksiran tengah, agar muatan basah tidak lolos.'],
        ['M', 'Kadar air ≥ 60%, organik ≥ 60%, plastik ≤ 5%', 'Organik basah yang bersih cocok untuk larva BSF dan kompos.'],
        ['B', 'Kadar air < 65%', 'Dikeringkan di bak bio-drying dengan serbuk kayu 10–20%.'],
        ['R', 'Selain itu', 'Sangat basah dan tercampur: ditahan, lalu dilaporkan ke TPS asal.']]
        .map(([k, j, p], i) => `<div class="rule"><span class="no" style="background:${RUTE[k].warna}18;color:${RUTE[k].warna}">${i + 1}</span><div><div class="rule-h"><b>${j}</b>${rb(k)}</div><p>${p}</p></div></div>`).join('')}</div></div>
  </div>
  <div class="section-label">Neraca 30 hari</div>
  <div class="kpis">
    ${kpi({ label: 'Serbuk kayu dibutuhkan', icon: 'leaf', value: serbuk, dec: 1, unit: 'ton', accent: '#b56308', foot: 'Dosis 10–20% untuk muatan Rute B' })}
    ${kpi({ label: 'Air yang perlu diuapkan', icon: 'drop', value: airB, dec: 0, unit: 'ton', accent: '#078879', foot: 'Agar muatan Rute B mencapai 20%' })}
    ${kpi({ label: 'Listrik dari Rute U', icon: 'zap', value: mwhU, dec: 1, unit: 'MWh', accent: '#2865e8', foot: 'Asumsi efisiensi listrik 20%' })}
    ${kpi({ label: 'Dikembalikan ke sumber', icon: 'alert', value: r.byR.R, dec: 0, unit: 'ton', accent: '#5b6577', foot: 'Rute R, dilaporkan ke TPS asal' })}
  </div>
  <div class="notice info">${ico('info')}<div>Rumus: dosis serbuk kayu d = (w − 0,50) ÷ (0,50 − 0,12), dibatasi 10–20%. Air yang diuapkan = berat × (w − 20%) ÷ 80%. Listrik = berat × LHV × 20% ÷ 3,6. Semua parameter adalah asumsi prototipe dan perlu disepakati dengan pengelola PLTSa.</div></div>`;
  countUp(el);
  const hari = [...Array(30)].map((_, i) => geserHari(akhir, i - 29)), g = groupBy(a, x => tgl(x.t));
  chart($('#rC1'), {
    xAxis: Object.assign(axisCat(hari.map(hariID)), { boundaryGap: false }), yAxis: axisVal('ton'),
    tooltip: { trigger: 'axis', backgroundColor: '#0c1d45', borderWidth: 0, textStyle: { color: '#fff', fontFamily: FONT } },
    series: RK.map(k => ({ name: `${k} · ${RUTE[k].nama}`, type: 'line', stack: 'a', smooth: .25, symbol: 'none', smoothMonotone: 'x', lineStyle: { width: 0 }, itemStyle: { color: RUTE[k].warna }, areaStyle: { color: RUTE[k].warna, opacity: .88 }, data: hari.map(d => +sum((g[d] || []).filter(x => x.rute === k), x => x.ton).toFixed(1)) })),
  });
};

// ---------------------------------------------------------------- Model & validasi
PAGES.model = el => {
  el.innerHTML = `
  <div class="page-head"><div><h1>Model dan validasi</h1><p>Status setiap model, rencana data, cara membagi data latih dan uji, serta kriteria lulus. Bagian ini sama dengan lampiran laporan Bab 3.</p></div></div>
  <div class="notice info">${ico('info')}<div><b>Status saat ini.</b> Model segmentasi di aplikasi masih versi uji yang dilatih dengan gambar sintetis, dan kadar air belum dikalibrasi dengan uji oven. Pengumpulan foto dan uji oven dijadwalkan 9–27 November 2026.</div></div>
  <div class="grid g-3 mb">
    <div class="panel model-card"><span class="status wait">● Versi uji</span><h3>Segmentasi komposisi</h3><p>DeepLabv3+ dengan encoder ResNet-50. Setiap piksel diberi satu dari enam fraksi atau latar.</p>
      <ul><li>Pralatih: TACO dan ZeroWaste-f (±2.700 foto berlabel)</li><li>Penyesuaian: 210 foto tim dari Kudus dan Malang</li><li>Uji: 90 foto terkunci, dilabeli dua orang</li><li>Berjalan di HP dalam format ONNX INT8</li></ul></div>
    <div class="panel model-card"><span class="status wait">● Belum dikalibrasi</span><h3>Kadar air</h3><p>Neraca massa per fraksi, dikoreksi curah hujan 24 dan 72 jam dengan regresi ridge. Rentang 80% dari Jackknife+.</p>
      <ul><li>Kalibrasi: 25 uji oven (ASTM E790-15)</li><li>Validasi tinggalkan-satu pada 25 sampel</li><li>Rute U memakai batas atas rentang</li><li>Sebelum kalibrasi: rentang bawaan ±10 poin</li></ul></div>
    <div class="panel model-card"><span class="status ok">● Rumus standar</span><h3>Nilai kalor (LHV)</h3><p>Dihitung, bukan dilatih: nilai kalor kering tiap fraksi ditimbang komposisi, lalu dikurangi efek air.</p>
      <ul><li>LHV = (1 − w) · LHV<sub>kering</sub> − 2,443 · w</li><li>ISO 18125:2017 dan ISO 21654:2021</li><li>Nilai fraksi dari Tchobanoglous dkk. (1993)</li><li>Rentang LHV mengikuti rentang kadar air</li></ul></div>
  </div>
  <div class="grid g-2 mb">
    <div class="panel"><div class="panel-head"><div><h3>Rencana data tahap 1</h3><p>Satu unit = satu sampel sampah yang difoto 5 kali. Kolom latih dan uji ditulis unit / foto.</p></div></div>
      <div class="table-wrap"><table><thead><tr><th>Sumber</th><th class="r">Unit</th><th class="r">Foto</th><th class="r">Oven</th><th class="r">Latih</th><th class="r">Uji</th></tr></thead><tbody>
        ${[['TPS permukiman, Kudus', 10, 50, 4, '7 / 35', '3 / 15'], ['Pasar, Kudus', 10, 50, 4, '7 / 35', '3 / 15'], ['TPS permukiman, Malang', 10, 50, 4, '7 / 35', '3 / 15'], ['Pasar, Malang', 10, 50, 4, '7 / 35', '3 / 15'], ['Campuran buatan lab', 20, 100, 9, '14 / 70', '6 / 30']]
          .map(r => `<tr><td>${r[0]}</td>${r.slice(1).map(v => `<td class="r num">${v}</td>`).join('')}</tr>`).join('')}
        <tr style="font-weight:800;background:#f7f9fd"><td>Jumlah</td><td class="r">60</td><td class="r">300</td><td class="r">25</td><td class="r">42 / 210</td><td class="r">18 / 90</td></tr></tbody></table></div></div>
    <div class="panel"><div class="panel-head"><div><h3>Pembagian data tanpa kebocoran</h3><p>StratifiedGroupKFold: kelompok = unit, strata = lokasi. Kelima foto satu unit selalu berada di bagian yang sama.</p></div></div>
      <div class="split">
        <div class="split-row"><div class="blk" style="flex:1;background:linear-gradient(120deg,#0c1d45,#2762e8)"><small>Seluruh data tim</small><b>60 unit · 300 foto</b></div></div>
        <div class="split-row"><div class="blk" style="flex:42;background:#1a3a82"><small>Pengembangan (latih + validasi)</small><b>42 unit · 210 foto</b></div><div class="blk" style="flex:18;background:#a97a26"><small>Uji akhir, dikunci</small><b>18 unit · 90 foto</b></div></div>
        <div class="split-row" id="folds">${[1, 2, 3, 4, 5].map(i => `<div class="fold">Lipatan ${i}<br><small>8–9 unit</small></div>`).join('')}<div class="fold" style="flex:0 0 18%;border-color:#e3cb9c;background:#fbf4e6;color:#6f4a0a">Tidak disentuh</div></div>
        <p class="ref">Bergiliran, satu lipatan (emas) menjadi validasi dan empat lainnya menjadi data latih. Hasil rata-rata 5 putaran dipakai memilih pengaturan. Model final dilatih ulang pada 42 unit, lalu diuji satu kali pada 90 foto. Pembagian dibekukan dengan benih tetap dan sidik jari SHA-256.</p>
      </div></div>
  </div>
  <div class="panel mb"><div class="panel-head"><div><h3>Kriteria lulus evaluasi</h3><p>Diukur pada set uji akhir dengan selang kepercayaan 95% (bootstrap per unit, 2.000 kali)</p></div></div>
    <div class="table-wrap"><table><thead><tr><th>Aspek</th><th>Ukuran</th><th>Batas lulus</th></tr></thead><tbody>
      ${[['Segmentasi', 'mIoU enam fraksi dan latar', '≥ 0,55'], ['Segmentasi', 'Selisih mIoU terhadap CLIPSeg tanpa pelatihan', '≥ +0,15'], ['Komposisi', 'MAE proporsi massa per unit', '≤ 3 poin persen'],
         ['Kadar air', 'MAE terhadap uji oven', '≤ 5 poin persen'], ['Rentang', 'PICP rentang 80%', '0,70–0,90'], ['Keputusan', 'Muatan basah (oven > 20%) yang lolos ke Rute U', '≤ 5%'],
         ['Keputusan', 'Kesesuaian rute dengan rute dari kadar air oven', '≥ 80%'], ['Kecepatan', 'Waktu inferensi di Raspberry Pi 5', '≤ 2 detik per frame'], ['Kapasitas', 'Waktu dari selesai scan sampai hasil tampil', '< 60 detik'],
         ['Ketangguhan', 'Penurunan mIoU pada gangguan cahaya, kabur, derau', '≤ 0,10'], ['Kompresi', 'Penurunan mIoU setelah INT8', '< 0,01']]
        .map(r => `<tr><td><b>${r[0]}</b></td><td>${r[1]}</td><td class="num"><b>${r[2]}</b></td></tr>`).join('')}</tbody></table></div></div>
  <div class="panel"><div class="panel-head"><div><h3>Rujukan utama</h3></div></div><ol class="ref">
    <li>Chen, L.-C., dkk. (2018). Encoder-decoder with atrous separable convolution for semantic image segmentation. <i>ECCV</i>.</li>
    <li>Bashkirova, D., dkk. (2022). ZeroWaste dataset: Towards deformable object segmentation in cluttered scenes. <i>CVPR</i>.</li>
    <li>Proença, P. F., &amp; Simões, P. (2020). TACO: Trash annotations in context for litter detection. arXiv:2003.06975.</li>
    <li>Tchobanoglous, G., Theisen, H., &amp; Vigil, S. A. (1993). <i>Integrated Solid Waste Management</i>. McGraw-Hill.</li>
    <li>Hoerl, A. E., &amp; Kennard, R. W. (1970). Ridge regression. <i>Technometrics</i>, 12(1), 55–67.</li>
    <li>Barber, R. F., dkk. (2021). Predictive inference with the jackknife+. <i>The Annals of Statistics</i>, 49(1), 486–507.</li>
    <li>ASTM E790-15. Residual moisture in a refuse-derived fuel analysis sample. ISO 18125:2017. ISO 21654:2021.</li></ol></div>`;
  let i = 0; const folds = $$('#folds .fold', el).slice(0, 5);
  const putar = () => { folds.forEach((f, j) => f.classList.toggle('val', j === i)); i = (i + 1) % 5; };
  putar(); S.timer = setInterval(putar, 1400);
};

// ---------------------------------------------------------------- Laporan
const FL = { tps: 'semua', jenis: 'semua', rute: 'semua', dari: '', sampai: '' };
function barisEkspor(a) {
  return a.map(m => ({ 'ID muatan': m.id, 'Waktu': m.t.replace('T', ' '), 'TPS': S.tpsBy[m.tps]?.nama || m.tps, 'Jenis TPS': JENIS[S.tpsBy[m.tps]?.tipe] || '', 'Pelat': m.pelat,
    'Berat (ton)': m.ton, 'Kadar air (%)': m.w, 'Batas bawah (%)': m.wb, 'Batas atas (%)': m.wa, 'LHV (MJ/kg)': m.lhv,
    'Organik (%)': m.org, 'Plastik (%)': m.pla, 'Kertas (%)': m.ker, 'Tekstil (%)': m.tek, 'Kayu (%)': m.kay, 'Inert (%)': m.ine,
    'Hujan 24 jam (mm)': m.r24, 'Dosis serbuk kayu (%)': m.dosis || '', 'Rute': m.rute, 'Tujuan': RUTE[m.rute].tujuan, 'Cek manual': m.cek ? 'Ya' : '', 'Sumber': m.sumber }));
}
function rekapEkspor(a) {
  return perTps(a).map(r => ({ 'TPS': r.t.nama, 'Jenis TPS': JENIS[r.t.tipe] || '', 'Kecamatan': r.t.kecamatan, 'Muatan': r.n, 'Tonase (ton)': +r.ton.toFixed(2),
    'Kadar air rata-rata (%)': +r.w.toFixed(1), 'LHV rata-rata (MJ/kg)': +r.lhv.toFixed(2), 'Organik (%)': +r.org.toFixed(1), 'Inert (%)': +r.ine.toFixed(1),
    ...Object.fromEntries(RK.map(k => [`Rute ${k} (ton)`, +r.byR[k].toFixed(2)])), 'Porsi Rute R (%)': +r.pR.toFixed(1) }));
}
function unduh(blob, nama) { const u = URL.createObjectURL(blob), a = document.createElement('a'); a.href = u; a.download = nama; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 1500); }
function unduhCsv(a, nama) {
  const rows = barisEkspor(a); if (!rows.length) return toast('Tidak ada data untuk diunduh.');
  const kol = Object.keys(rows[0]), csv = '﻿' + [kol].concat(rows.map(r => kol.map(k => r[k]))).map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(';')).join('\r\n');
  unduh(new Blob([csv], { type: 'text/csv;charset=utf-8' }), `${nama}.csv`); toast('CSV diunduh.');
}
function labelFilter(F) {
  return [F.tps !== 'semua' ? S.tpsBy[F.tps]?.nama : 'Semua TPS', F.jenis !== 'semua' ? JENIS[F.jenis] : null, F.rute !== 'semua' ? `Rute ${F.rute}` : null, `${tglPanjang(F.dari)} – ${tglPanjang(F.sampai)}`].filter(Boolean).join(' · ');
}
PAGES.laporan = el => {
  if (!FL.dari) { FL.dari = geserHari(tanggalAkhir(), -6); FL.sampai = tanggalAkhir(); }
  el.innerHTML = `
  <div class="banner"><div class="eyebrow">Laporan · rekap dan unduhan</div><h1>Pusat laporan</h1>
    <p>Saring menurut TPS, jenis TPS, rute, dan tanggal. Unduh rekap Excel (rekap per TPS, rincian muatan, keterangan), CSV, atau cetak sebagai PDF untuk rapat dinas.</p></div>
  ${filterBar(FL)}
  <div class="panel mb" id="lapPrint">
    <div class="panel-head"><div><h3>Ringkasan laporan</h3><p id="lFilter"></p></div>
      <div class="report-actions no-print"><button class="btn btn-primary" id="lXlsx">${ico('down')} Unduh Excel</button><button class="btn btn-ghost" id="lCsv">${ico('file')} CSV</button><button class="btn btn-ghost" id="lPdf">${ico('print')} Cetak / PDF</button></div></div>
    <div class="summary-strip" id="lSum"></div>
    <div class="table-wrap" id="lTab"></div>
  </div>
  <div class="panel no-print"><div class="panel-head"><div><h3>Impor data dari aplikasi petugas</h3><p>Unggah berkas CSV hasil tombol unduh di aplikasi SORA HP. Data tersimpan di peramban ini dan langsung ikut dihitung di semua halaman.</p></div></div>
    <label class="dropzone" id="drop"><span class="m-ico" style="width:48px;height:48px;border-radius:14px;background:#e8efff;color:#2762e8;display:grid;place-items:center;flex:none">${ico('phone')}</span>
      <span style="flex:1"><b>Pilih atau seret berkas SORA-….csv</b><small id="impInfo">${S.impor.length ? `${f0(S.impor.length)} baris dari HP sudah diimpor.` : 'Belum ada data yang diimpor.'}</small></span>
      <input type="file" accept=".csv,text/csv" id="impFile" hidden><span class="btn btn-ghost">${ico('up')} Pilih berkas</span></label>
    <div style="margin-top:12px" ${S.impor.length ? '' : 'hidden'} id="impHapusWrap"><button class="btn btn-ghost" id="impHapus">Hapus data impor</button></div></div>`;
  const def = () => ({ tps: 'semua', jenis: 'semua', rute: 'semua', dari: geserHari(tanggalAkhir(), -6), sampai: tanggalAkhir() });
  const gambar = () => {
    const a = saring(FL), r = ringkas(a);
    $('#lFilter').textContent = labelFilter(FL);
    $('#lSum').innerHTML = [['Muatan', f0(r.n)], ['Tonase', f1(r.ton) + ' t'], ['Kadar air', f1(r.w) + '%'], ['LHV', f2(r.lhv) + ' MJ/kg'], ['Ke Rute R', f1(r.pR) + '%']].map(([k, v]) => `<div class="sum"><span>${k}</span><b class="num">${v}</b></div>`).join('');
    const rek = perTps(a);
    $('#lTab').innerHTML = `<table><thead><tr><th>TPS</th><th>Jenis</th><th class="r">Muatan</th><th class="r">Tonase</th><th class="r">Kadar air</th><th class="r">LHV</th>${RK.map(k => `<th class="r">${k}</th>`).join('')}<th>Porsi residu</th></tr></thead><tbody>${rek.map(x => `<tr>
      <td><b>${esc(x.t.nama)}</b></td><td>${JENIS[x.t.tipe] || ''}</td><td class="r num">${f0(x.n)}</td><td class="r num">${f1(x.ton)} t</td><td class="r num">${f1(x.w)}%</td><td class="r num">${f2(x.lhv)}</td>
      ${RK.map(k => `<td class="r num">${f1(x.byR[k])}</td>`).join('')}<td><div class="bar-cell"><span class="mini-bar"><i style="width:${Math.min(100, x.pR * 2)}%;background:${x.pR >= 25 ? '#c2413a' : x.pR >= 15 ? '#f0a43a' : '#1f9d74'}"></i></span><b class="num">${f0(x.pR)}%</b></div></td></tr>`).join('')}</tbody></table>`;
  };
  ikatFilter(el, FL, gambar, def);
  $('#lCsv').onclick = () => unduhCsv(saring(FL), `SORA-laporan-${FL.dari}_${FL.sampai}`);
  $('#lXlsx').onclick = () => {
    const a = saring(FL); if (!a.length) return toast('Tidak ada data untuk diunduh.');
    const wb = XLSX.utils.book_new();
    const s1 = XLSX.utils.json_to_sheet(rekapEkspor(a)), s2 = XLSX.utils.json_to_sheet(barisEkspor(a));
    s1['!cols'] = Object.keys(rekapEkspor(a)[0]).map(k => ({ wch: Math.max(10, k.length + 2) })); s2['!cols'] = Object.keys(barisEkspor(a)[0]).map(k => ({ wch: Math.max(10, k.length + 2) }));
    XLSX.utils.book_append_sheet(wb, s1, 'Rekap per TPS'); XLSX.utils.book_append_sheet(wb, s2, 'Rincian muatan');
    const info = XLSX.utils.aoa_to_sheet([['Laporan SORA'], ['Saringan', labelFilter(FL)], ['Dibuat', new Date().toLocaleString('id-ID')], ['Sumber data', S.impor.length ? 'Simulasi dan impor aplikasi HP' : 'Simulasi (bukan data lapangan)']]);
    XLSX.utils.book_append_sheet(wb, info, 'Keterangan');
    const out = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    unduh(new Blob([out], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), `SORA-rekap-${FL.dari}_${FL.sampai}.xlsx`); toast('Rekap Excel diunduh.');
  };
  $('#lPdf').onclick = () => window.print();
  const inp = $('#impFile'), dz = $('#drop');
  inp.onchange = () => inp.files[0] && imporCsv(inp.files[0]);
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
  dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('drag'); e.dataTransfer.files[0] && imporCsv(e.dataTransfer.files[0]); });
  $('#impHapus').onclick = () => { S.impor = []; store.set('sora-impor', []); S.tps = S.data.tps.slice(); S.tpsBy = Object.fromEntries(S.tps.map(t => [t.kode, t])); gabungImpor(); toast('Data impor dihapus.'); buka('laporan'); };
  gambar();
};

// ---------------------------------------------------------------- impor CSV aplikasi HP
function parseCsv(teks) {
  teks = teks.replace(/^﻿/, '');
  const pemisah = (teks.split('\n')[0].match(/;/g) || []).length >= (teks.split('\n')[0].match(/,/g) || []).length ? ';' : ',';
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
      const rows = parseCsv(rd.result), h = rows[0].map(x => x.trim()), ix = n => h.indexOf(n), v = (r, n) => r[ix(n)] ?? '';
      const num = s => { const x = parseFloat(String(s).replace(',', '.')); return isFinite(x) ? x : 0; };
      if (ix('ID muatan') < 0 || ix('Kadar air %') < 0) throw new Error('Kolom tidak dikenali');
      const byNama = Object.fromEntries(S.tps.map(t => [t.nama.toLowerCase(), t.kode]));
      const baru = rows.slice(1).map((r, i) => {
        const namaTps = v(r, 'TPS').trim(), kode = byNama[namaTps.toLowerCase()] || ('HP-' + namaTps.replace(/\W+/g, '-').toUpperCase());
        const rute = (v(r, 'Keputusan') || v(r, 'Rekomendasi')).trim().toUpperCase();
        const w = num(v(r, 'Kadar air %')), lhv = num(v(r, 'LHV MJ/kg')), t = waktuWIB(v(r, 'Waktu')) || waktuWIB(new Date().toISOString());
        return { id: `${v(r, 'ID muatan')}-${v(r, 'Bagian') || i + 1}`, t,
          tps: kode, tpsNama: namaTps, tipe: v(r, 'Jenis TPS') || 'lainnya', pelat: v(r, 'Pelat'), ton: num(v(r, 'Berat kg')) / 1000,
          w, wb: num(v(r, 'Batas bawah %')) || Math.max(0, w - 10), wa: num(v(r, 'Batas atas %')) || w + 10, lhv,
          org: num(v(r, 'Organik %')), pla: num(v(r, 'Plastik %')), ker: num(v(r, 'Kertas %')), tek: num(v(r, 'Tekstil %')), kay: num(v(r, 'Kayu %')), ine: num(v(r, 'Inert %')),
          r24: num(v(r, 'Hujan 24 jam mm')), r72: num(v(r, 'Hujan 72 jam mm')), rute: RK.includes(rute) ? rute : 'R', dosis: num(v(r, 'Dosis serbuk kayu %')),
          kwh: Math.max(0, 1000 * lhv * 0.2 / 3.6), cek: !!v(r, 'Peringatan').trim(), sumber: 'aplikasi' };
      }).filter(m => m.ton > 0);
      const ada = new Set(S.impor.map(m => m.id)), tambah = baru.filter(m => !ada.has(m.id));
      S.impor = S.impor.concat(tambah); store.set('sora-impor', S.impor); gabungImpor();
      toast(`${tambah.length} baris dari aplikasi HP diimpor.`); buka('laporan');
    } catch (e) { toast('Berkas tidak dikenali. Gunakan CSV dari tombol unduh di aplikasi SORA.'); }
  };
  rd.readAsText(file, 'utf-8');
}

// ------------------------------------------------------------------ router & shell
function buka(p) {
  if (!PAGES[p]) p = 'beranda';
  bersihkan();
  $$('#nav a').forEach(a => a.classList.toggle('on', a.dataset.p === p));
  $('#crumb').textContent = JUDUL[p];
  document.title = `${JUDUL[p]} · SORA`;
  const wrap = $('#pages'); wrap.innerHTML = `<div class="page" id="pg"></div>`;
  PAGES[p]($('#pg'));
  $('#app').classList.remove('open');
  $('#main').scrollIntoView({ block: 'start' }); window.scrollTo(0, 0);
}
function masuk(akun) {
  sesi.set(akun);
  $('#login').hidden = true; $('#app').hidden = false;
  $('#whoName').textContent = akun.nama; $('#whoRole').textContent = akun.peran; $('#whoAv').textContent = akun.av;
  $('#pillPeriod').textContent = `${tglPanjang(tanggalAwal())} – ${tglPanjang(tanggalAkhir())}`;
  buka((location.hash || '#beranda').slice(1));
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
  // Komponen Streamlit: beri tahu bahwa komponen siap dan minta tinggi penuh.
  if (window.parent !== window) {
    const kirim = (type, extra = {}) => window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, extra), '*');
    kirim('streamlit:componentReady', { apiVersion: 1 });
    window.addEventListener('message', e => { if (e.data && e.data.type === 'streamlit:render') kirim('streamlit:setFrameHeight', { height: Math.max(900, window.innerHeight) }); });
  }
  siapkanLogin();
  try {
    const res = await fetch('data/sora_demo.json', { cache: 'no-cache' });
    siapkanData(await res.json());
  } catch (e) {
    document.body.innerHTML = '<p style="padding:40px;font-family:sans-serif">Data dashboard gagal dimuat. Muat ulang halaman.</p>'; return;
  }
  $('#btnMini').onclick = () => { $('#app').classList.toggle('mini'); setTimeout(() => { S.charts.forEach(c => c.resize()); S.map && S.map.invalidateSize(); }, 320); };
  $('#btnOut').onclick = keluar;
  $('#btnMenu').onclick = () => $('#app').classList.toggle('open');
  window.addEventListener('hashchange', () => { if (!$('#app').hidden) buka(location.hash.slice(1)); });
  const s = sesi.get();
  if (s && AKUN.some(a => a.u === s.u)) masuk(s); else { $('#login').hidden = false; }
}
mulai();
})();
