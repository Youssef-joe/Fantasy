import { team } from './teams.js';
import { startPitch } from './pitch.js';

const FEED_URL = 'data/predictions/latest.json';
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const SPOTLIGHT_MS = 7000;
const FORMATIONS = ['3-4-3', '3-5-2', '4-4-2', '4-3-3', '4-5-1', '5-3-2', '5-4-1'];

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const f1 = (n) => (n == null || Number.isNaN(n) ? '–' : Number(n).toFixed(1));
const money = (n) => (n == null ? '–' : `£${Number(n).toFixed(1)}m`);
const pct = (n) => (n == null ? '–' : `${Number(n).toFixed(1)}%`);
const canPlay = (p) => p.chance_of_playing == null || p.chance_of_playing >= 75;
const value = (p) => (p.price ? p.predicted_points / p.price : 0);

let FEED = null;
let BY_ID = new Map();

/* ------------------------------------------------------------------ */
/* boot                                                                */
/* ------------------------------------------------------------------ */

document.addEventListener('DOMContentLoaded', () => {
  initChrome();
  startPitch($('#pitchCanvas'));
  load();
});

async function load() {
  $('#loadError').hidden = true;
  try {
    const res = await fetch(FEED_URL, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    FEED = await res.json();
    BY_ID = new Map(FEED.predictions.map((p) => [p.player_id, p]));
  } catch (err) {
    console.error('Feed failed to load', err);
    $('#loadError').hidden = false;
    return;
  }
  renderHero();
  renderWire();
  renderPicks();
  renderXI();
  renderFixtures();
  initBoard();
  renderModel();
  $('#footerUpdated').textContent = `Gameweek ${FEED.gameweek}, ${FEED.season} season. Predictions generated ${new Date(FEED.generated_at).toLocaleString()}.`;
}

$('#retryLoad')?.addEventListener('click', load);

/* ------------------------------------------------------------------ */
/* page chrome: top bar, menu, nav highlight, reveal-on-scroll         */
/* ------------------------------------------------------------------ */

function initChrome() {
  const topbar = $('#topbar');
  const onScroll = () => topbar.classList.toggle('scrolled', window.scrollY > 20);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  const menuBtn = $('#menuBtn');
  const nav = $('#nav');
  const setMenu = (open) => {
    nav.classList.toggle('open', open);
    menuBtn.setAttribute('aria-expanded', String(open));
    menuBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  };
  menuBtn.addEventListener('click', () => setMenu(!nav.classList.contains('open')));
  nav.addEventListener('click', (e) => { if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setMenu(false); });

  const links = new Map($$('.nav a').map((a) => [a.getAttribute('href').slice(1), a]));
  const navObserver = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        links.forEach((a) => a.classList.remove('active'));
        links.get(entry.target.id)?.classList.add('active');
      }
    }
  }, { rootMargin: '-45% 0px -50% 0px' });
  links.forEach((_, id) => { const el = document.getElementById(id); if (el) navObserver.observe(el); });

  observeReveals(document);
}

const revealObserver = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (entry.isIntersecting) {
      entry.target.classList.add('in');
      revealObserver.unobserve(entry.target);
    }
  }
}, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

function observeReveals(root) {
  $$('.reveal, .pick, .fixture-grid, .model-score', root).forEach((el) => revealObserver.observe(el));
}

/* ------------------------------------------------------------------ */
/* helpers                                                             */
/* ------------------------------------------------------------------ */

function teamChip(code) {
  const t = team(code);
  return `<span class="team-chip" style="--c1:${t.c1};--c2:${t.c2}" title="${esc(t.name)}"><i aria-hidden="true"></i>${esc(code)}</span>`;
}

function fixtureText(p) {
  const fx = p.fixtures?.length ? p.fixtures : [{ opponent: p.opponent, is_home: p.is_home }];
  return fx.map((f) => `${f.opponent} (${f.is_home === 'HOME' ? 'H' : 'A'})`).join(' + ');
}

function availabilityFlag(p) {
  if (p.chance_of_playing == null || p.chance_of_playing === 100) return '';
  const out = p.chance_of_playing <= 25;
  return `<span class="flag${out ? ' out' : ''}" title="${esc(p.news || '')}">${p.chance_of_playing}%</span>`;
}

function relativeTime(iso) {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)} days ago`;
}

function countUp(el, to, { decimals = 1, duration = 1200 } = {}) {
  if (REDUCED) { el.textContent = Number(to).toFixed(decimals); return; }
  const start = performance.now();
  const step = (now) => {
    const k = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - k, 4);
    el.textContent = (to * eased).toFixed(decimals);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* ------------------------------------------------------------------ */
/* hero                                                                */
/* ------------------------------------------------------------------ */

function renderHero() {
  const gw = String(FEED.gameweek);
  const gwEl = $('#heroGw');
  gwEl.textContent = gw;
  gwEl.dataset.text = gw;
  $('#heroEyebrow').innerHTML = `Season ${esc(FEED.season)} · <b>updated ${esc(relativeTime(FEED.generated_at))}</b>`;
  document.title = `GW${gw} predictions · Fantasy.AI`;

  startCountdown(new Date(FEED.deadline_time));
  startSpotlight(FEED.predictions.filter(canPlay).slice(0, 5));
}

function startCountdown(deadline) {
  const fmt = new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  $('#deadlineText').textContent = `GW${FEED.gameweek} · ${fmt.format(deadline)}`;
  const box = $('#countdown');
  box.setAttribute('aria-label', `Transfer deadline ${fmt.format(deadline)}`);
  const pad = (n) => String(n).padStart(2, '0');

  const tick = () => {
    const ms = deadline - Date.now();
    if (ms <= 0) {
      box.classList.add('passed');
      $('#deadlineText').textContent = `GW${FEED.gameweek} deadline has passed`;
      $('#topbarDeadline').textContent = `GW${FEED.gameweek} in progress`;
      return false;
    }
    const s = Math.floor(ms / 1000);
    const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
    $('#cdD').textContent = pad(d);
    $('#cdH').textContent = pad(h);
    $('#cdM').textContent = pad(m);
    $('#cdS').textContent = pad(s % 60);
    $('#topbarDeadline').innerHTML = `GW${FEED.gameweek} deadline <strong>${d}d ${h}h ${pad(m)}m</strong>`;
    return true;
  };
  if (tick()) {
    const timer = setInterval(() => { if (!tick()) clearInterval(timer); }, 1000);
  }
}

function startSpotlight(players) {
  const card = $('#spotlightCard');
  const dots = $('#spotlightDots');
  const aside = $('#spotlight');
  const pauseBtn = $('#spotlightPause');
  const bar = $('#spotlightProgress');
  if (!players.length) { card.innerHTML = ''; return; }

  let index = 0;
  let userPaused = REDUCED;
  let hoverPaused = false;
  let progress = null;

  dots.innerHTML = players.map((p, i) =>
    `<button role="tab" aria-selected="${i === 0}" aria-controls="spotlightCard" data-i="${i}">${esc(p.web_name)}</button>`).join('');

  const show = (i) => {
    index = i;
    const p = players[i];
    const t = team(p.team);
    $$('button', dots).forEach((b, j) => b.setAttribute('aria-selected', String(j === i)));
    const old = $('.sp', card);
    if (old) { old.classList.add('leave'); setTimeout(() => old.remove(), 300); }
    const el = document.createElement('div');
    el.className = 'sp enter';
    el.innerHTML = `
      <span class="sp-rank" aria-hidden="true">${i + 1}</span>
      <div class="sp-team sp-anim">${teamChip(p.team)}<span>${esc(t.name)} · ${esc(fixtureText(p))}</span></div>
      <h3 class="sp-name sp-anim">${esc(p.web_name)}</h3>
      <div class="sp-points sp-anim"><span class="big" data-to="${p.predicted_points}">0.0</span><span class="unit">predicted<br>points</span></div>
      <dl class="sp-stats sp-anim">
        <div class="sp-stat"><dt>Form</dt><dd>${f1(p.avg_last_5)}</dd></div>
        <div class="sp-stat"><dt>Price</dt><dd>${money(p.price)}</dd></div>
        <div class="sp-stat"><dt>Owned</dt><dd>${pct(p.selected_by_percent)}</dd></div>
        <div class="sp-stat"><dt>Pos</dt><dd>${esc(p.position)}</dd></div>
      </dl>`;
    el.addEventListener('click', () => openPlayer(p.player_id));
    el.style.cursor = 'pointer';
    card.appendChild(el);
    countUp($('.big', el), p.predicted_points, { duration: 1100 });
    runProgress();
  };

  const runProgress = () => {
    progress?.cancel();
    progress = bar.animate([{ width: '0%' }, { width: '100%' }], { duration: SPOTLIGHT_MS, easing: 'linear', fill: 'forwards' });
    progress.onfinish = () => show((index + 1) % players.length);
    syncPause();
  };

  const syncPause = () => {
    const paused = userPaused || hoverPaused;
    if (progress) paused ? progress.pause() : progress.play();
    aside.classList.toggle('paused', userPaused);
    pauseBtn.setAttribute('aria-pressed', String(userPaused));
    pauseBtn.setAttribute('aria-label', userPaused ? 'Resume rotation' : 'Pause rotation');
    pauseBtn.innerHTML = userPaused
      ? '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z"/></svg>'
      : '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="2" width="3.5" height="12" rx="1"/><rect x="9.5" y="2" width="3.5" height="12" rx="1"/></svg>';
  };

  dots.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (b) show(Number(b.dataset.i));
  });
  dots.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    const next = (index + (e.key === 'ArrowRight' ? 1 : players.length - 1)) % players.length;
    show(next);
    $$('button', dots)[next].focus();
  });
  pauseBtn.addEventListener('click', () => { userPaused = !userPaused; syncPause(); });
  aside.addEventListener('pointerenter', () => { hoverPaused = true; syncPause(); });
  aside.addEventListener('pointerleave', () => { hoverPaused = false; syncPause(); });
  aside.addEventListener('focusin', () => { hoverPaused = true; syncPause(); });
  aside.addEventListener('focusout', () => { hoverPaused = false; syncPause(); });

  // glow follows the pointer, card tilts slightly
  aside.addEventListener('pointermove', (e) => {
    const r = aside.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
    aside.style.setProperty('--mx', `${x * 100}%`);
    aside.style.setProperty('--my', `${y * 100}%`);
    if (!REDUCED) aside.style.transform = `rotateY(${(x - 0.5) * 6}deg) rotateX(${(0.5 - y) * 6}deg)`;
  });
  aside.addEventListener('pointerleave', () => { aside.style.transform = ''; });

  card.innerHTML = '';
  show(0);
}

/* ------------------------------------------------------------------ */
/* availability wire                                                   */
/* ------------------------------------------------------------------ */

function renderWire() {
  const items = (FEED.injured_players || []).slice(0, 18);
  const wire = $('#wire');
  if (!items.length) { wire.hidden = true; return; }
  const html = items.map((p) => {
    const chance = p.chance_of_playing == null ? '' : `<span class="pct" style="color:${p.chance_of_playing >= 50 ? 'var(--amber)' : 'var(--coral)'}">${p.chance_of_playing}%</span>`;
    return `<div class="wire-item">${teamChip(p.team)}<b>${esc(p.web_name)}</b>${chance}<span class="news">${esc(p.news || p.status)}</span></div>`;
  }).join('');
  // content twice so the loop is seamless; the copy is hidden from screen readers
  $('#wireItems').innerHTML = `<div style="display:flex">${html}</div><div style="display:flex" aria-hidden="true">${html}</div>`;
  $('#wireItems').style.setProperty('--ticker-duration', `${items.length * 5}s`);
}

/* ------------------------------------------------------------------ */
/* picks                                                               */
/* ------------------------------------------------------------------ */

function renderPicks() {
  const pool = FEED.predictions.filter(canPlay);
  const used = new Set();
  const take = (list) => { const p = list.find((x) => !used.has(x.player_id)); if (p) used.add(p.player_id); return p; };

  const captain = take(pool);
  const differential = take(pool.filter((p) => (p.selected_by_percent ?? 100) < 10));
  const valuePick = take([...pool].filter((p) => p.predicted_points >= 4).sort((a, b) => value(b) - value(a)));

  const cards = [
    captain && { p: captain, label: 'Captain', cls: 'captain', letter: 'C', why: 'Highest predicted points of anyone likely to play.' },
    differential && { p: differential, label: 'Differential', cls: '', letter: 'D', why: `Top prediction among players owned by fewer than 10% of managers.` },
    valuePick && { p: valuePick, label: 'Value', cls: '', letter: 'V', why: `Most predicted points per £1m, among players predicted 4+ points.` },
  ].filter(Boolean);

  $('#picksGrid').innerHTML = cards.map(({ p, label, cls, letter, why }) => {
    const t = team(p.team);
    return `
      <article class="pick" style="--c1:${t.c1}" data-id="${p.player_id}" tabindex="0" aria-label="${label}: ${esc(p.web_name)}, ${f1(p.predicted_points)} predicted points. Open details.">
        <span class="pick-big-letter" aria-hidden="true">${letter}</span>
        <span class="pick-label ${cls}">${label}</span>
        <p class="pick-why">${esc(why)}</p>
        <h3 class="pick-name">${esc(p.web_name)}</h3>
        <div class="pick-meta">${teamChip(p.team)}<span class="pos pos-${p.position}">${p.position}</span><span>${esc(fixtureText(p))}</span>${availabilityFlag(p)}</div>
        <div class="pick-foot">
          <span class="pick-pts"><span data-to="${p.predicted_points}">0.0</span><small>pts</small></span>
          <span class="pick-side">${money(p.price)}<br><b>${pct(p.selected_by_percent)}</b> owned<br>${value(p).toFixed(2)} pts/£m</span>
        </div>
      </article>`;
  }).join('');

  $$('.pick').forEach((el, i) => {
    el.style.transitionDelay = `${i * 120}ms`;
    el.addEventListener('click', () => openPlayer(Number(el.dataset.id)));
    el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPlayer(Number(el.dataset.id)); } });
    revealObserver.observe(el);
    const num = $('[data-to]', el);
    new IntersectionObserver(([e], obs) => {
      if (e.isIntersecting) { countUp(num, Number(num.dataset.to), { duration: 1400 }); obs.disconnect(); }
    }, { threshold: 0.4 }).observe(el);
  });
}

/* ------------------------------------------------------------------ */
/* best XI                                                             */
/* ------------------------------------------------------------------ */

function pickXI(formation) {
  const [d, m, f] = formation.split('-').map(Number);
  const pool = FEED.predictions.filter(canPlay);
  const top = (pos, n) => pool.filter((p) => p.position === pos).slice(0, n);
  const lines = { GKP: top('GKP', 1), DEF: top('DEF', d), MID: top('MID', m), FWD: top('FWD', f) };
  const all = [...lines.GKP, ...lines.DEF, ...lines.MID, ...lines.FWD];
  const captain = all.reduce((a, b) => (b.predicted_points > a.predicted_points ? b : a), all[0]);
  const points = all.reduce((s, p) => s + p.predicted_points, 0) + (captain?.predicted_points || 0);
  const cost = all.reduce((s, p) => s + (p.price || 0), 0);
  return { lines, all, captain, points, cost };
}

function renderXI() {
  const results = FORMATIONS.map((f) => ({ f, ...pickXI(f) }));
  const best = results.reduce((a, b) => (b.points > a.points ? b : a));
  const picker = $('#formationPicker');
  picker.innerHTML = FORMATIONS.map((f) =>
    `<button role="radio" aria-checked="${f === best.f}" data-f="${f}" title="${f === best.f ? 'Highest-scoring formation' : ''}">${f}${f === best.f ? ' ★' : ''}</button>`).join('');
  picker.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    $$('button', picker).forEach((x) => x.setAttribute('aria-checked', String(x === b)));
    drawXI(b.dataset.f);
  });
  picker.addEventListener('keydown', (e) => radioKeys(e, picker));

  // pitch tilts toward the pointer
  const stage = $('#xiStage'), pitch = $('#xiPitch');
  if (!REDUCED) {
    stage.addEventListener('pointermove', (e) => {
      const r = stage.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      pitch.style.setProperty('--rz', `${x * -6}deg`);
      pitch.style.setProperty('--rx', `${y * 6}deg`);
    });
    stage.addEventListener('pointerleave', () => { pitch.style.setProperty('--rz', '0deg'); pitch.style.setProperty('--rx', '0deg'); });
  }

  // first draw when the pitch scrolls into view, so players "walk on"
  new IntersectionObserver(([e], obs) => { if (e.isIntersecting) { drawXI(best.f); obs.disconnect(); } }, { threshold: 0.25 }).observe(stage);
}

function drawXI(formation) {
  const xi = pickXI(formation);
  const container = $('#xiPlayers');
  const rowsY = { FWD: 15, MID: 38, DEF: 62, GKP: 86 };
  const existing = new Map($$('.token', container).map((el) => [Number(el.dataset.id), el]));
  const keep = new Set();

  for (const [pos, players] of Object.entries(xi.lines)) {
    players.forEach((p, i) => {
      const x = ((i + 1) / (players.length + 1)) * 100;
      const y = rowsY[pos];
      keep.add(p.player_id);
      let el = existing.get(p.player_id);
      if (!el) {
        const t = team(p.team);
        el = document.createElement('div');
        el.className = 'token entering';
        el.dataset.id = p.player_id;
        el.innerHTML = `
          <div class="token-body" tabindex="0" role="button" aria-label="${esc(p.web_name)}, ${esc(p.team)}, ${f1(p.predicted_points)} predicted points">
            <div class="token-shirt" style="--c1:${t.c1};--c2:${t.c2}"><b>${esc(p.team)}</b></div>
            <div class="token-name">${esc(p.web_name)}</div>
            <div class="token-pts">${f1(p.predicted_points)}</div>
          </div>`;
        const body = $('.token-body', el);
        body.addEventListener('click', () => openPlayer(p.player_id));
        body.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPlayer(p.player_id); } });
        el.style.setProperty('--x', `${x}%`);
        el.style.setProperty('--y', `${y}%`);
        container.appendChild(el);
        const delay = REDUCED ? 0 : 60 + (pos === 'GKP' ? 0 : pos === 'DEF' ? 1 : pos === 'MID' ? 2 : 3) * 90 + i * 40;
        setTimeout(() => el.classList.remove('entering'), delay);
      } else {
        el.style.setProperty('--x', `${x}%`);
        el.style.setProperty('--y', `${y}%`);
      }
      const shirt = $('.token-shirt', el);
      $('.token-armband', shirt)?.remove();
      if (p.player_id === xi.captain.player_id) shirt.insertAdjacentHTML('beforeend', '<span class="token-armband" aria-label="Captain">C</span>');
    });
  }
  existing.forEach((el, id) => {
    if (!keep.has(id)) { el.classList.add('leaving'); setTimeout(() => el.remove(), 500); }
  });

  countUp($('#xiPoints'), xi.points, { decimals: 1, duration: 900 });
  $('#xiCost').textContent = money(xi.cost);
  $('#xiList').innerHTML = xi.all.map((p) => `
    <li tabindex="0" data-id="${p.player_id}">
      <span class="pos pos-${p.position}">${p.position}</span>
      <span class="n">${esc(p.web_name)}${p.player_id === xi.captain.player_id ? ' <span class="volt">(C)</span>' : ''}</span>
      <span class="c">${money(p.price)}</span>
      <span class="p">${f1(p.predicted_points)}</span>
    </li>`).join('');
  $$('#xiList li').forEach((li) => {
    const open = () => openPlayer(Number(li.dataset.id));
    li.addEventListener('click', open);
    li.addEventListener('keydown', (e) => { if (e.key === 'Enter') open(); });
  });
}

function radioKeys(e, group) {
  if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp'].includes(e.key)) return;
  e.preventDefault();
  const buttons = $$('button', group);
  const i = buttons.indexOf(document.activeElement);
  const next = buttons[(i + (e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : buttons.length - 1)) % buttons.length];
  next.focus();
  next.click();
}

/* ------------------------------------------------------------------ */
/* fixture radar                                                       */
/* ------------------------------------------------------------------ */

function renderFixtures() {
  const byTeam = FEED.fixtures_by_team || {};
  const gws = Array.from({ length: 5 }, (_, i) => FEED.gameweek + i).filter((g) => g <= 38);
  const rows = Object.entries(byTeam).map(([code, fixtures]) => {
    const perGw = gws.map((g) => fixtures.filter((f) => f.gameweek === g));
    const diffs = fixtures.map((f) => f.difficulty);
    const avg = diffs.length ? diffs.reduce((a, b) => a + b, 0) / diffs.length : 5;
    return { code, perGw, avg };
  });

  const table = $('#fixtureGrid');
  const draw = (sort) => {
    const sorted = [...rows].sort((a, b) =>
      sort === 'az' ? a.code.localeCompare(b.code) : sort === 'hard' ? b.avg - a.avg : a.avg - b.avg);
    let cell = 0;
    table.innerHTML = `
      <caption class="sr-only">Fixture difficulty for the next ${gws.length} gameweeks</caption>
      <thead><tr><th scope="col">Team</th>${gws.map((g) => `<th scope="col" class="gw">GW${g}</th>`).join('')}<th scope="col" class="gw">Avg</th></tr></thead>
      <tbody>${sorted.map((r) => `
        <tr>
          <th scope="row">${teamChip(r.code)}</th>
          ${r.perGw.map((fx) => {
            const d = REDUCED ? 0 : (cell++) * 12;
            if (!fx.length) return `<td class="fx blank" style="--d:${d}ms">—</td>`;
            if (fx.length > 1) {
              return `<td class="fx dgw" style="--d:${d}ms">${fx.map((f) => `<span class="fdr-${f.difficulty}">${esc(f.opponent)}<small>${f.is_home ? 'H' : 'A'}</small></span>`).join('')}</td>`;
            }
            const f = fx[0];
            return `<td class="fx fdr-${f.difficulty}" style="--d:${d}ms" title="Difficulty ${f.difficulty} of 5">${esc(f.opponent)}<small>${f.is_home ? 'H' : 'A'}</small></td>`;
          }).join('')}
          <td class="fx-avg">${r.avg.toFixed(1)}</td>
        </tr>`).join('')}
      </tbody>`;
  };
  draw('easy');

  const sortGroup = $('#fixtureSort');
  sortGroup.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    $$('button', sortGroup).forEach((x) => x.setAttribute('aria-checked', String(x === b)));
    const visible = table.classList.contains('in');
    table.classList.remove('in');
    draw(b.dataset.sort);
    if (visible) requestAnimationFrame(() => requestAnimationFrame(() => table.classList.add('in')));
  });
  sortGroup.addEventListener('keydown', (e) => radioKeys(e, sortGroup));
}

/* ------------------------------------------------------------------ */
/* player board                                                        */
/* ------------------------------------------------------------------ */

const board = { pos: 'ALL', q: '', sort: 'predicted_points', maxPrice: Infinity, limit: 40 };

function initBoard() {
  const prices = FEED.predictions.map((p) => p.price).filter(Boolean);
  const maxP = Math.ceil(Math.max(...prices) * 2) / 2;
  const minP = Math.floor(Math.min(...prices) * 2) / 2;
  const slider = $('#maxPrice');
  slider.min = minP; slider.max = maxP; slider.value = maxP;
  $('#maxPriceOut').textContent = 'any';
  $('#playersSub').textContent = `${FEED.predictions.length} players with a fixture in GW${FEED.gameweek}. Search, filter and sort; select a player for fixtures and news.`;

  $('#search').addEventListener('input', (e) => { board.q = e.target.value.trim().toLowerCase(); board.limit = 40; drawBoard(); });
  const posGroup = $('#posFilter');
  posGroup.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    $$('button', posGroup).forEach((x) => x.setAttribute('aria-checked', String(x === b)));
    board.pos = b.dataset.pos; board.limit = 40; drawBoard();
  });
  posGroup.addEventListener('keydown', (e) => radioKeys(e, posGroup));
  $('#sortBy').addEventListener('change', (e) => { board.sort = e.target.value; board.limit = 40; drawBoard(); });
  slider.addEventListener('input', () => {
    const v = Number(slider.value);
    board.maxPrice = v >= maxP ? Infinity : v;
    $('#maxPriceOut').textContent = board.maxPrice === Infinity ? 'any' : money(v);
    board.limit = 40; drawBoard();
  });
  $('#showMore').addEventListener('click', () => { board.limit += 40; drawBoard(true); });
  drawBoard();
}

function drawBoard(append = false) {
  const maxPts = FEED.predictions[0]?.predicted_points || 1;
  const list = FEED.predictions
    .filter((p) => board.pos === 'ALL' || p.position === board.pos)
    .filter((p) => !board.q || p.web_name.toLowerCase().includes(board.q) || p.player_name.toLowerCase().includes(board.q) || p.team.toLowerCase().includes(board.q) || team(p.team).name.toLowerCase().includes(board.q))
    .filter((p) => (p.price ?? 0) <= board.maxPrice)
    .sort((a, b) => {
      const get = (p) => (board.sort === 'value' ? value(p) : p[board.sort] ?? -1);
      return get(b) - get(a);
    });

  const body = $('#boardBody');
  const prev = append ? body.children.length : 0;
  const shown = list.slice(0, board.limit);
  if (!shown.length) {
    body.innerHTML = '<div class="board-empty">No players match these filters.</div>';
  } else {
    const html = shown.slice(prev).map((p, i) => {
      const d = REDUCED ? 0 : Math.min(i, 20) * 25;
      return `
      <div class="row" role="row" tabindex="0" data-id="${p.player_id}" style="--d:${d}ms">
        <span class="rank" role="cell">${prev + i + 1}</span>
        <span class="who" role="cell"><b>${esc(p.web_name)}</b><span>${teamChip(p.team)}<span class="pos pos-${p.position}">${p.position}</span>${availabilityFlag(p)}</span></span>
        <span class="fix hide-sm" role="cell">${esc(fixtureText(p))}</span>
        <span class="num hide-sm" role="cell">${money(p.price)}</span>
        <span class="num hide-md" role="cell">${pct(p.selected_by_percent)}</span>
        <span class="num hide-sm" role="cell">${f1(p.avg_last_5)}</span>
        <span class="pred" role="cell"><span class="pred-bar" aria-hidden="true"><i style="--w:${Math.max(2, (p.predicted_points / maxPts) * 100)}%;--d:${d}ms"></i></span><b>${f1(p.predicted_points)}</b></span>
      </div>`;
    }).join('');
    if (append) body.insertAdjacentHTML('beforeend', html); else body.innerHTML = html;
  }
  $('#boardCount').textContent = `Showing ${shown.length} of ${list.length} players`;
  $('#showMore').hidden = shown.length >= list.length;
}

$('#boardBody').addEventListener('click', (e) => {
  const row = e.target.closest('.row');
  if (row) openPlayer(Number(row.dataset.id));
});
$('#boardBody').addEventListener('keydown', (e) => {
  const row = e.target.closest('.row');
  if (row && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); openPlayer(Number(row.dataset.id)); }
});

/* ------------------------------------------------------------------ */
/* player drawer                                                       */
/* ------------------------------------------------------------------ */

function openPlayer(id) {
  const p = BY_ID.get(id);
  if (!p) return;
  const t = team(p.team);
  const fixtures = (FEED.fixtures_by_team?.[p.team] || []).slice(0, 5);
  const chance = p.chance_of_playing ?? 100;
  const C = 2 * Math.PI * 26;
  const chanceCls = chance <= 25 ? 'out' : chance < 100 ? 'warn' : '';

  $('#drawerBody').innerHTML = `
    <div class="drawer-hero" style="--c1:${t.c1}">
      <div class="pick-meta">${teamChip(p.team)}<span class="pos pos-${p.position}">${p.position}</span></div>
      <h2 id="drawerName">${esc(p.web_name)}</h2>
      <p>${esc(p.player_name)} · ${esc(t.name)}</p>
    </div>
    <div class="drawer-section">
      <h3>Gameweek ${FEED.gameweek}</h3>
      <dl class="drawer-stats">
        <div class="hl"><dt>Predicted</dt><dd>${f1(p.predicted_points)}</dd></div>
        <div><dt>Form (last 5)</dt><dd>${f1(p.avg_last_5)}</dd></div>
        <div><dt>Pts / £m</dt><dd>${value(p).toFixed(2)}</dd></div>
        <div><dt>Price</dt><dd>${money(p.price)}</dd></div>
        <div><dt>Owned</dt><dd>${pct(p.selected_by_percent)}</dd></div>
        <div><dt>Fixture</dt><dd style="font-size:14px">${esc(fixtureText(p))}</dd></div>
      </dl>
      ${p.fixtures?.length > 1 ? `<p class="model-note">Double gameweek: ${p.fixtures.map((f) => `${esc(f.opponent)} ${f1(f.predicted_points)}`).join(' + ')} points.</p>` : ''}
    </div>
    <div class="drawer-section">
      <h3>Availability</h3>
      <div class="chance ${chanceCls}">
        <svg viewBox="0 0 60 60" aria-hidden="true"><circle class="track" cx="30" cy="30" r="26"/><circle class="val" cx="30" cy="30" r="26" stroke-dasharray="${C}" stroke-dashoffset="${C}"/></svg>
        <div><b>${chance}%</b> chance of playing${p.status ? ` · ${esc(p.status)}` : ''}</div>
      </div>
      ${p.news ? `<p class="drawer-news" style="margin-top:14px">${esc(p.news)}</p>` : ''}
    </div>
    ${fixtures.length ? `
    <div class="drawer-section">
      <h3>Next fixtures</h3>
      <div class="drawer-fixtures">${fixtures.map((f) => `<div class="fdr-${f.difficulty}">${esc(f.opponent)}<small>GW${f.gameweek} ${f.is_home ? 'H' : 'A'}</small></div>`).join('')}</div>
    </div>` : ''}`;

  const dialog = $('#playerDrawer');
  if (!dialog.open) dialog.showModal();
  requestAnimationFrame(() => {
    const val = $('.chance .val', dialog);
    if (val) val.style.strokeDashoffset = String(C * (1 - chance / 100));
  });
}

$('#playerDrawer').addEventListener('click', (e) => {
  // click on the backdrop (outside the panel) closes it
  if (e.target === e.currentTarget) e.currentTarget.close();
});

/* ------------------------------------------------------------------ */
/* model                                                               */
/* ------------------------------------------------------------------ */

function renderModel() {
  const m = FEED.model;
  const box = $('.model-score');
  if (!m || m.test_mae == null) { box.hidden = true; return; }
  const base = m.baseline_mae_avg_last_5;
  const max = Math.max(m.test_mae, base || 0) * 1.1;
  $('#barCompare').innerHTML = `
    <div class="bc-row model"><div class="bc-top"><span>Model: average error per prediction</span><b>${m.test_mae.toFixed(2)}</b></div><div class="bc-track"><i style="--w:${(m.test_mae / max) * 100}%"></i></div></div>
    ${base != null ? `<div class="bc-row"><div class="bc-top"><span>Baseline: last-5 average</span><b>${base.toFixed(2)}</b></div><div class="bc-track"><i style="--w:${(base / max) * 100}%"></i></div></div>` : ''}`;

  let verdict = '';
  if (base != null) {
    const gain = ((base - m.test_mae) / base) * 100;
    verdict = gain > 0
      ? `The model's predictions are <b>${gain.toFixed(1)}% closer</b> to what players actually scored than the baseline. `
      : `Right now the model is <b>not beating</b> the baseline. We're working on it. `;
  }
  const trained = m.trained_at ? new Date(m.trained_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '';
  $('#modelNote').innerHTML = `Lower is better. ${verdict}Measured on ${m.n_test?.toLocaleString() ?? '–'} held-out matches after training on ${m.n_train?.toLocaleString() ?? '–'} from this season${trained ? `, retrained ${esc(trained)}` : ''}.`;
}
