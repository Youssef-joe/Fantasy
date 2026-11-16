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
  initMyTeam();
  renderFixtures();
  initBoard();
  renderModel();
  renderRecord();
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

// The pitch shows either the optimiser's £100m squad (from squad.json) or the
// "dream XI": the top predicted player for every slot, ignoring price.
const xiState = { mode: 'squad', formation: null, horizon: 'gw' };
let SQUADS = null;

function pickXI(formation) {
  const [d, m, f] = formation.split('-').map(Number);
  const pool = FEED.predictions.filter(canPlay);
  const top = (pos, n) => pool.filter((p) => p.position === pos).slice(0, n);
  const lines = { GKP: top('GKP', 1), DEF: top('DEF', d), MID: top('MID', m), FWD: top('FWD', f) };
  const all = [...lines.GKP, ...lines.DEF, ...lines.MID, ...lines.FWD];
  const byPts = [...all].sort((a, b) => b.predicted_points - a.predicted_points);
  const points = all.reduce((s, p) => s + p.predicted_points, 0) + (byPts[0]?.predicted_points || 0);
  const cost = all.reduce((s, p) => s + (p.price || 0), 0);
  return {
    lines, all, bench: [], captainId: byPts[0]?.player_id, viceId: byPts[1]?.player_id,
    points, cost, pts: (p) => p.predicted_points,
  };
}

function squadLineup(h) {
  const get = (id) => ({ ...(BY_ID.get(id) || {}), ...h.players[String(id)], player_id: id });
  const all = h.starting.map(get);
  const lines = { GKP: [], DEF: [], MID: [], FWD: [] };
  all.forEach((p) => lines[p.position].push(p));
  return {
    lines, all, bench: h.bench.map(get), captainId: h.captain, viceId: h.vice_captain,
    points: h.points, cost: h.cost, pts: (p) => p.points,
  };
}

function renderXI() {
  const results = FORMATIONS.map((f) => ({ f, ...pickXI(f) }));
  const best = results.reduce((a, b) => (b.points > a.points ? b : a));
  xiState.formation = best.f;
  const picker = $('#formationPicker');
  picker.innerHTML = FORMATIONS.map((f) =>
    `<button role="radio" aria-checked="${f === best.f}" data-f="${f}" title="${f === best.f ? 'Highest-scoring formation' : ''}">${f}${f === best.f ? ' ★' : ''}</button>`).join('');
  picker.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    $$('button', picker).forEach((x) => x.setAttribute('aria-checked', String(x === b)));
    xiState.formation = b.dataset.f;
    drawXI();
  });
  picker.addEventListener('keydown', (e) => radioKeys(e, picker));

  const modeGroup = $('#xiMode');
  modeGroup.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    $$('button', modeGroup).forEach((x) => x.setAttribute('aria-checked', String(x === b)));
    xiState.mode = b.dataset.mode;
    drawXI();
  });
  modeGroup.addEventListener('keydown', (e) => radioKeys(e, modeGroup));

  const horizonGroup = $('#xiHorizon');
  horizonGroup.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    $$('button', horizonGroup).forEach((x) => x.setAttribute('aria-checked', String(x === b)));
    xiState.horizon = b.dataset.h;
    drawXI();
  });
  horizonGroup.addEventListener('keydown', (e) => radioKeys(e, horizonGroup));

  const squadsReady = fetch('data/predictions/squad.json', { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : null))
    .then((s) => {
      if (s?.gameweek === FEED.gameweek && s.horizons?.length) {
        SQUADS = s;
        horizonGroup.innerHTML = s.horizons.map((h, i) =>
          `<button role="radio" aria-checked="${i === 0}" data-h="${h.key}">${h.gameweeks.length > 1 ? `Next ${h.gameweeks.length} GWs` : `This GW`}</button>`).join('');
      }
    })
    .catch(() => null)
    .finally(() => {
      if (!SQUADS) { xiState.mode = 'dream'; modeGroup.hidden = true; }
    });

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
  new IntersectionObserver(([e], obs) => {
    if (e.isIntersecting) { obs.disconnect(); squadsReady.then(drawXI); }
  }, { threshold: 0.25 }).observe(stage);
}

function drawXI() {
  const squadMode = xiState.mode === 'squad' && SQUADS;
  const h = squadMode ? (SQUADS.horizons.find((x) => x.key === xiState.horizon) || SQUADS.horizons[0]) : null;
  const xi = squadMode ? squadLineup(h) : pickXI(xiState.formation);

  $('#formationPicker').hidden = !!squadMode;
  $('#xiHorizon').hidden = !squadMode;
  $('#xiSub').textContent = squadMode
    ? `The best legal FPL squad for £${SQUADS.budget}m: 15 players, at most 3 per club, picked by an optimiser to maximise predicted points for ${h.gameweeks.length > 1 ? `GW${h.gameweeks[0]}–${h.gameweeks.at(-1)}` : `GW${h.gameweeks[0]}`}.`
    : 'The top predicted player for every slot in the formation, ignoring price. Useful for captain and transfer ideas, but not a squad you could afford.';
  $('#xiPointsLabel').textContent = squadMode && h.gameweeks.length > 1 ? `Predicted points, ${h.gameweeks.length} GWs` : 'Predicted points';
  $('#xiPointsNote').textContent = 'starting XI, captain counted twice';
  $('#xiCostLabel').textContent = squadMode ? 'Squad cost' : 'XI cost';
  $('#xiCostNote').textContent = squadMode ? `15 players · £${(SQUADS.budget - h.cost).toFixed(1)}m in the bank` : 'starting XI only, no budget';

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
          <div class="token-body" tabindex="0" role="button">
            <div class="token-shirt" style="--c1:${t.c1};--c2:${t.c2}"><b>${esc(p.team)}</b></div>
            <div class="token-name">${esc(p.web_name)}</div>
            <div class="token-pts"></div>
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
      // points and armbands change between modes and horizons, so refresh them every draw
      const role = p.player_id === xi.captainId ? 'captain' : p.player_id === xi.viceId ? 'vice-captain' : '';
      $('.token-pts', el).textContent = f1(xi.pts(p));
      $('.token-body', el).setAttribute('aria-label',
        `${p.web_name}, ${p.team}, ${f1(xi.pts(p))} predicted points${role ? `, ${role}` : ''}`);
      const shirt = $('.token-shirt', el);
      $('.token-armband', shirt)?.remove();
      if (role === 'captain') shirt.insertAdjacentHTML('beforeend', '<span class="token-armband" aria-hidden="true">C</span>');
      if (role === 'vice-captain') shirt.insertAdjacentHTML('beforeend', '<span class="token-armband vice" aria-hidden="true">V</span>');
    });
  }
  existing.forEach((el, id) => {
    if (!keep.has(id)) { el.classList.add('leaving'); setTimeout(() => el.remove(), 500); }
  });

  const bench = $('#xiBench');
  bench.hidden = !xi.bench.length;
  bench.innerHTML = xi.bench.map((p, i) => `
    <div class="bench-card" tabindex="0" role="button" data-id="${p.player_id}" style="--d:${REDUCED ? 0 : 400 + i * 80}ms"
         aria-label="Bench ${i + 1}: ${esc(p.web_name)}, ${f1(xi.pts(p))} predicted points">
      ${teamChip(p.team)}<b>${esc(p.web_name)}</b><span class="p">${f1(xi.pts(p))}</span>
    </div>`).join('');

  countUp($('#xiPoints'), xi.points, { decimals: 1, duration: 900 });
  $('#xiCost').textContent = money(xi.cost);
  const row = (p, cls = '') => `
    <li tabindex="0" data-id="${p.player_id}" class="${cls}">
      <span class="pos pos-${p.position}">${p.position}</span>
      <span class="n">${esc(p.web_name)}${p.player_id === xi.captainId ? ' <span class="volt">(C)</span>' : p.player_id === xi.viceId ? ' <span class="volt">(V)</span>' : ''}</span>
      <span class="c">${money(p.price)}</span>
      <span class="p">${f1(xi.pts(p))}</span>
    </li>`;
  $('#xiList').innerHTML = xi.all.map((p) => row(p)).join('')
    + (xi.bench.length ? `<li class="sub" aria-hidden="true">Bench</li>${xi.bench.map((p) => row(p, 'bench')).join('')}` : '');
  $$('#xiBench .bench-card').forEach((card) => {
    const open = () => openPlayer(Number(card.dataset.id));
    card.addEventListener('click', open);
    card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
  });
  $$('#xiList li[data-id]').forEach((li) => {
    const open = () => openPlayer(Number(li.dataset.id));
    li.addEventListener('click', open);
    li.addEventListener('keydown', (e) => { if (e.key === 'Enter') open(); });
  });
}

/* ------------------------------------------------------------------ */
/* your team: import by FPL ID, best XI, transfer suggestions          */
/* ------------------------------------------------------------------ */

const TEAM_KEY = 'fantasy.teamId';
const STATUS_TEXT = { i: 'Injured', s: 'Suspended', u: 'Unavailable', n: 'Not eligible', d: 'Doubtful' };

// Describe any player id using the prediction (if they have one) or the player index.
function describe(id) {
  const pred = BY_ID.get(id);
  const idx = FEED.players?.[String(id)];
  if (pred) return { ...pred, gw: pred.predicted_points, horizon: pred.points_horizon ?? pred.predicted_points, predicted: true };
  const [web_name, teamCode, position, price, status] = idx || ['Unknown', 'UNK', 'MID', 0, 'u'];
  return {
    player_id: id, web_name, team: teamCode, position, price, gw: 0, horizon: 0, predicted: false,
    reason: STATUS_TEXT[status] || 'No fixture',
  };
}

// Best legal XI from a squad for a points key ('gw' or 'horizon'), trying every formation.
function bestXIFrom(squad, key) {
  const byPos = { GKP: [], DEF: [], MID: [], FWD: [] };
  squad.forEach((p) => byPos[p.position]?.push(p));
  Object.values(byPos).forEach((l) => l.sort((a, b) => b[key] - a[key]));
  let best = null;
  for (let d = 3; d <= 5; d++) for (let m = 2; m <= 5; m++) {
    const f = 10 - d - m;
    if (f < 1 || f > 3 || byPos.DEF.length < d || byPos.MID.length < m || byPos.FWD.length < f || !byPos.GKP.length) continue;
    const xi = [byPos.GKP[0], ...byPos.DEF.slice(0, d), ...byPos.MID.slice(0, m), ...byPos.FWD.slice(0, f)];
    const sum = xi.reduce((s, p) => s + p[key], 0);
    if (!best || sum > best.sum) best = { xi, sum, formation: `${d}-${m}-${f}` };
  }
  if (!best) return null;
  const ranked = [...best.xi].sort((a, b) => b[key] - a[key]);
  const inXI = new Set(best.xi.map((p) => p.player_id));
  const bench = squad.filter((p) => !inXI.has(p.player_id))
    .sort((a, b) => (a.position === 'GKP') - (b.position === 'GKP') || b[key] - a[key]);
  return { ...best, bench, captain: ranked[0], vice: ranked[1], total: best.sum + (ranked[0]?.[key] || 0) };
}

// Every legal single transfer (same position, affordable at today's prices, max 3 per club),
// ranked by the gain in best-XI points over the horizon.
function suggestTransfers(squad, bank, limit = 3) {
  const base = bestXIFrom(squad, 'horizon')?.total ?? 0;
  const owned = new Set(squad.map((p) => p.player_id));
  const clubs = {};
  squad.forEach((p) => { clubs[p.team] = (clubs[p.team] || 0) + 1; });
  const pool = FEED.predictions.filter((p) => !owned.has(p.player_id) && canPlay(p))
    .map((p) => describe(p.player_id));
  const best = new Map(); // best move per player out, so suggestions aren't all the same swap
  for (const out of squad) {
    const budget = (out.price || 0) + bank + 1e-9;
    for (const cand of pool) {
      if (cand.position !== out.position || cand.price > budget) continue;
      if (cand.team !== out.team && (clubs[cand.team] || 0) >= 3) continue;
      const next = squad.map((p) => (p.player_id === out.player_id ? cand : p));
      const gain = (bestXIFrom(next, 'horizon')?.total ?? 0) - base;
      if (gain > 0.05 && (!best.has(out.player_id) || gain > best.get(out.player_id).gain)) {
        best.set(out.player_id, { out, inn: cand, gain });
      }
    }
  }
  return [...best.values()].sort((a, b) => b.gain - a.gain).slice(0, limit);
}

function initMyTeam() {
  const form = $('#teamForm'), input = $('#teamId'), err = $('#teamError'), forget = $('#teamForget');
  const store = {
    get() { try { return localStorage.getItem(TEAM_KEY); } catch { return null; } },
    set(v) { try { localStorage.setItem(TEAM_KEY, v); } catch { /* storage unavailable */ } },
    clear() { try { localStorage.removeItem(TEAM_KEY); } catch { /* storage unavailable */ } },
  };
  const showError = (msg) => { err.textContent = msg; err.hidden = !msg; };

  async function loadTeam(id) {
    showError('');
    const btn = $('#teamLoad');
    btn.disabled = true; btn.textContent = 'Loading…';
    try {
      const res = await fetch(`/api/fpl-team?id=${encodeURIComponent(id)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || 'Could not load that team.');
      store.set(id);
      forget.hidden = false;
      renderMyTeam(data);
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false; btn.textContent = 'Load my team';
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const id = input.value.replace(/\D/g, '');
    if (!id) { showError('Enter your FPL team ID: the number in your team URL.'); input.focus(); return; }
    loadTeam(id);
  });
  forget.addEventListener('click', () => {
    store.clear(); input.value = ''; forget.hidden = true;
    $('#myteamResult').hidden = true; $('#myteamResult').innerHTML = '';
  });

  const saved = store.get();
  if (saved && /^\d{1,9}$/.test(saved)) { input.value = saved; loadTeam(saved); }
}

function renderMyTeam(team) {
  const box = $('#myteamResult');
  const squad = team.picks.map((p) => describe(p.player_id));
  const xi = bestXIFrom(squad, 'gw');
  const transfers = suggestTransfers(squad, team.bank);
  const hz = FEED.horizon_gameweeks || [FEED.gameweek];
  const hzLabel = hz.length > 1 ? `GW${hz[0]}–${hz.at(-1)}` : `GW${hz[0]}`;
  const flag = (p) => (p.predicted
    ? (p.chance_of_playing != null && p.chance_of_playing < 100 ? `<span class="warn amber">${p.chance_of_playing}%</span>` : '')
    : `<span class="warn">${esc(p.reason)}</span>`);
  const row = (p, cls = '') => `
    <li class="${cls}" tabindex="0" data-id="${p.player_id}">
      <span class="pos pos-${p.position}">${p.position}</span>
      <span class="n">${teamChip(p.team)}<b>${esc(p.web_name)}</b>${p === xi?.captain ? '<span class="tag">C</span>' : p === xi?.vice ? '<span class="tag v">V</span>' : ''}</span>
      ${flag(p) || '<span></span>'}
      <span class="p">${f1(p.gw)}</span>
    </li>`;

  box.innerHTML = `
    <div class="myteam-head">
      <div>
        <h3>${esc(team.name)}</h3>
        <p>${esc(team.manager)}${team.overall_rank ? ` · overall rank ${team.overall_rank.toLocaleString()}` : ''} · squad as of the GW${team.gameweek} deadline</p>
      </div>
      <dl class="myteam-stats">
        <div class="hl"><dt>Predicted GW${FEED.gameweek}</dt><dd>${xi ? f1(xi.total) : '–'}</dd></div>
        <div><dt>Formation</dt><dd>${xi?.formation ?? '–'}</dd></div>
        <div><dt>In the bank</dt><dd>${money(team.bank)}</dd></div>
      </dl>
    </div>
    <div class="myteam-grid">
      <div class="myteam-card">
        <h4>Your best XI for GW${FEED.gameweek}</h4>
        <p>Picked from your 15 for the most predicted points. Captain: <b>${esc(xi?.captain?.web_name ?? '–')}</b>.</p>
        <ol class="squad-list">
          ${(xi?.xi || []).map((p) => row(p)).join('')}
          <li class="sub" aria-hidden="true">Bench</li>
          ${(xi?.bench || []).map((p) => row(p, 'bench')).join('')}
        </ol>
      </div>
      <div class="myteam-card">
        <h4>Best transfers</h4>
        <p>Single free transfers that add the most predicted points to your best XI over ${hzLabel}, within your £${team.bank.toFixed(1)}m bank and the 3-per-club limit.</p>
        ${transfers.length ? transfers.map((t, i) => `
          <div class="transfer" style="--d:${REDUCED ? 0 : i * 90}ms">
            <div class="side out"><span>Out</span><b>${esc(t.out.web_name)}</b><small>${esc(t.out.team)} · ${money(t.out.price)}${t.out.predicted ? ` · ${f1(t.out.horizon)} pts` : ` · ${esc(t.out.reason)}`}</small></div>
            <span class="arrow" aria-hidden="true">→</span>
            <div class="side in"><span>In</span><b>${esc(t.inn.web_name)}</b><small>${esc(t.inn.team)} · ${money(t.inn.price)} · ${f1(t.inn.horizon)} pts</small></div>
            <div class="gain"><span>Predicted gain over ${hzLabel}</span><strong>+${f1(t.gain)}</strong></div>
          </div>`).join('') : '<p class="model-note">No single transfer improves your predicted points. Save the free transfer.</p>'}
        <p class="myteam-note">Uses today's prices; your selling price in FPL can be lower after a price rise. Transfers made since the GW${team.gameweek} deadline aren't public yet, so they won't show here.</p>
      </div>
    </div>`;
  box.hidden = false;
  $$('.squad-list li[data-id]', box).forEach((li) => {
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
/* track record                                                        */
/* ------------------------------------------------------------------ */

async function renderRecord() {
  let acc;
  try {
    const res = await fetch('data/predictions/accuracy.json', { cache: 'no-cache' });
    if (!res.ok) return;
    acc = await res.json();
  } catch { return; }
  const cols = [
    ...(acc.backtest || []).map((r) => ({ ...r, kind: 'backtest' })),
    ...(acc.live || []).map((r) => ({ ...r, kind: 'live' })),
  ].slice(-12); // the most recent dozen; live results push the backtest out over the season
  if (!cols.length) return;
  $('#record').hidden = false;

  const max = Math.max(...cols.map((c) => c.oracle_top20_avg_points || 0), 1);
  const h = (v) => `${Math.max(1.5, (v / max) * 100)}%`;
  $('#recordChart').innerHTML = cols.map((c, i) => {
    const d = REDUCED ? 0 : i * 70;
    const label = `GW${c.gameweek}${c.kind === 'backtest' ? ' (backtest)' : ''}: our top 20 averaged ${c.top20_avg_points.toFixed(1)} points, last-5 average top 20 ${c.baseline_top20_avg_points.toFixed(1)}, best possible ${c.oracle_top20_avg_points.toFixed(1)}`;
    return `
      <div class="rc-col ${c.kind}" role="img" aria-label="${esc(label)}" title="${esc(label)}">
        <div class="rc-bars">
          <span class="rc-oracle" style="--h:${h(c.oracle_top20_avg_points)}"></span>
          <span class="rc-bar model" style="--h:${h(c.top20_avg_points)};--d:${d}ms"><b>${c.top20_avg_points.toFixed(1)}</b></span>
          <span class="rc-bar base" style="--h:${h(c.baseline_top20_avg_points)};--d:${d + 60}ms"><b>${c.baseline_top20_avg_points.toFixed(1)}</b></span>
        </div>
        <div class="rc-label">GW${c.gameweek}<small>${c.kind === 'backtest' ? 'backtest' : 'live'}</small></div>
      </div>`;
  }).join('');
  revealObserver.observe($('#recordChart'));
  // on narrow screens the chart scrolls sideways: start at the latest gameweek
  $('#recordChart').scrollLeft = $('#recordChart').scrollWidth;

  const ls = acc.live_summary, bs = acc.backtest_summary;
  const parts = [];
  if (ls) {
    parts.push(`Live, over ${ls.gameweeks} gameweek${ls.gameweeks > 1 ? 's' : ''}: our top 20 averaged <b>${ls.top20_avg_points.toFixed(1)} points</b> against ${ls.baseline_top20_avg_points.toFixed(1)} (best possible ${ls.oracle_top20_avg_points.toFixed(1)}).`);
  }
  if (bs) {
    const first = acc.backtest[0].gameweek, last = acc.backtest[acc.backtest.length - 1].gameweek;
    parts.push(`Striped bars are a backtest of GW${first}–${last}: each gameweek predicted by a model trained only on earlier matches. Top 20 averaged <b>${bs.top20_avg_points.toFixed(1)}</b> against ${bs.baseline_top20_avg_points.toFixed(1)}.`);
  }
  $('#recordFoot').innerHTML = parts.join(' ');

  const latest = (acc.live || []).at(-1);
  const box = $('#recordLatest');
  if (!latest) {
    box.innerHTML = `
      <div class="record-pending">
        <span class="big">GW${FEED.gameweek}</span>
        <p>Live scoring starts once Gameweek ${FEED.gameweek} has been played and FPL confirms the points. The predictions on this page are frozen at the deadline and checked against the real results.</p>
      </div>`;
    return;
  }
  const c = latest.captain;
  const verdict = (a) => (a >= 6 ? 'hit' : a <= 2 ? 'miss' : '');
  box.innerHTML = `
    <h3>Gameweek ${latest.gameweek}</h3>
    <p>What our top picks predicted, and what they scored.</p>
    <div class="captain-result">
      <div class="who"><span>Captain pick</span><b>${esc(c.web_name)}</b>${teamChip(c.team)}</div>
      <div class="score"><strong>${c.actual}</strong>pts scored<br>predicted ${f1(c.predicted)}</div>
    </div>
    <ol class="result-list">
      <li class="head"><span>Top 10 predicted</span><span class="v">Pred</span><span class="v">Real</span></li>
      ${latest.top_predicted.map((p) => `
        <li><span class="n">${teamChip(p.team)}<b>${esc(p.web_name)}</b></span>
          <span class="v">${f1(p.predicted)}</span>
          <span class="v act ${verdict(p.actual)}">${p.actual}</span></li>`).join('')}
    </ol>`;
}

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
  const gws = Array.isArray(m.test_gameweeks) && m.test_gameweeks.length
    ? `GW${m.test_gameweeks[0]}–${m.test_gameweeks[m.test_gameweeks.length - 1]}` : null;
  const how = m.split === 'by gameweek' && gws
    ? `Tested on ${gws} (${m.n_test?.toLocaleString() ?? '–'} player-matches), each time training only on matches played before that gameweek`
    : `Measured on ${m.n_test?.toLocaleString() ?? '–'} held-out matches`;
  const picks = m.top20_avg_points != null && m.baseline_top20_avg_points != null
    ? ` Its top 20 picks each week averaged <b>${m.top20_avg_points.toFixed(1)} points</b>, against ${m.baseline_top20_avg_points.toFixed(1)} for the baseline's.` : '';
  const seasons = Array.isArray(m.seasons_used) && m.seasons_used.length > 1 ? ` Trained on ${m.seasons_used.length} seasons of matches` : '';
  $('#modelNote').innerHTML = `Lower is better. ${verdict}${how}.${picks}${seasons}${seasons && trained ? `, retrained ${esc(trained)}.` : trained ? ` Retrained ${esc(trained)}.` : seasons ? '.' : ''}`;
}
