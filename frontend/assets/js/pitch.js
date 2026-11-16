// Hero background: a floodlit pitch in perspective, with drifting light dust
// and a camera that eases toward the pointer. Pauses when off-screen or the tab
// is hidden, and draws a single still frame for reduced-motion users.

const PITCH_W = 68;   // metres
const PITCH_L = 105;
const REDUCED_FLICKER = matchMedia('(prefers-reduced-motion: reduce)').matches;

export function startPitch(canvas) {
  const ctx = canvas.getContext('2d');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let w = 0, h = 0, dpr = 1;
  let running = false, raf = 0, t0 = performance.now();
  const cam = { x: 0, tx: 0, y: 0, ty: 0 };
  let dust = [];

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = canvas.clientWidth; h = canvas.clientHeight;
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const n = Math.round(Math.min(140, (w * h) / 9000));
    dust = Array.from({ length: n }, () => newDust(true));
    if (!running) draw(performance.now());
  }

  function newDust(anywhere) {
    return {
      x: Math.random() * w,
      y: anywhere ? Math.random() * h : h + 10,
      r: Math.random() * 1.6 + 0.3,
      vy: -(Math.random() * 0.25 + 0.05),
      vx: (Math.random() - 0.5) * 0.12,
      a: Math.random() * 0.5 + 0.15,
      tw: Math.random() * Math.PI * 2,
    };
  }

  // Project pitch coordinates (x across, z along, metres) to the screen.
  function project(x, z) {
    const horizon = h * (0.36 + cam.y * 0.02);
    const camZ = 18;
    const scale = Math.min(w, 1400) * 0.95;
    const zz = z + camZ;
    const px = w * 0.5 + ((x - PITCH_W / 2 + cam.x * 6) * scale) / zz;
    const py = horizon + (h * 1.25 * 16) / zz;
    return [px, py];
  }

  function line(points, close) {
    ctx.beginPath();
    points.forEach(([x, z], i) => {
      const [px, py] = project(x, z);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    if (close) ctx.closePath();
    ctx.stroke();
  }

  function arc(cx, cz, r, a0, a1, steps = 48) {
    const pts = [];
    for (let i = 0; i <= steps; i++) {
      const a = a0 + ((a1 - a0) * i) / steps;
      pts.push([cx + Math.cos(a) * r, cz + Math.sin(a) * r]);
    }
    line(pts, false);
  }

  // A cone of light from (x, y) pointing at `angle` (radians, 0 = right, PI/2 = down).
  function drawBeam(x, y, angle, t) {
    const len = Math.hypot(w, h) * 1.1;
    const spread = 0.16;
    const g = ctx.createRadialGradient(x, y, 0, x, y, len);
    const flicker = REDUCED_FLICKER ? 1 : 0.92 + Math.sin(t * 2.1 + x) * 0.04;
    g.addColorStop(0, `rgba(240, 255, 215, ${0.16 * flicker})`);
    g.addColorStop(0.45, `rgba(225, 255, 190, ${0.05 * flicker})`);
    g.addColorStop(1, 'rgba(215, 255, 58, 0)');
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + Math.cos(angle - spread) * len, y + Math.sin(angle - spread) * len);
    ctx.lineTo(x + Math.cos(angle + spread) * len, y + Math.sin(angle + spread) * len);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  function drawMarkings(width, color) {
    ctx.lineWidth = width;
    ctx.strokeStyle = color;
    line([[0, 0], [PITCH_W, 0], [PITCH_W, PITCH_L], [0, PITCH_L]], true);
    line([[0, PITCH_L / 2], [PITCH_W, PITCH_L / 2]]);
    arc(PITCH_W / 2, PITCH_L / 2, 9.15, 0, Math.PI * 2, 64);
    for (const [z0, dir] of [[0, 1], [PITCH_L, -1]]) {
      line([[PITCH_W / 2 - 20.16, z0], [PITCH_W / 2 - 20.16, z0 + dir * 16.5], [PITCH_W / 2 + 20.16, z0 + dir * 16.5], [PITCH_W / 2 + 20.16, z0]]);
      line([[PITCH_W / 2 - 9.16, z0], [PITCH_W / 2 - 9.16, z0 + dir * 5.5], [PITCH_W / 2 + 9.16, z0 + dir * 5.5], [PITCH_W / 2 + 9.16, z0]]);
      // penalty arc: the part of the 9.15m circle around the spot that lies outside the box
      const a = Math.asin(5.5 / 9.15);
      const s = dir > 0 ? a : Math.PI + a;
      arc(PITCH_W / 2, z0 + dir * 11, 9.15, s, s + Math.PI - 2 * a, 24);
    }
  }

  function draw(now) {
    const t = (now - t0) / 1000;
    cam.x += (cam.tx - cam.x) * 0.04;
    cam.y += (cam.ty - cam.y) * 0.04;
    if (!reduced) cam.x += Math.sin(t * 0.15) * 0.002;

    ctx.clearRect(0, 0, w, h);

    // mowing stripes
    const stripes = 12;
    for (let i = 0; i < stripes; i++) {
      const z0 = (PITCH_L / stripes) * i, z1 = (PITCH_L / stripes) * (i + 1);
      const a = project(-6, z0), b = project(PITCH_W + 6, z0), c = project(PITCH_W + 6, z1), d = project(-6, z1);
      ctx.beginPath();
      ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.lineTo(c[0], c[1]); ctx.lineTo(d[0], d[1]); ctx.closePath();
      ctx.fillStyle = i % 2 ? 'rgba(18, 74, 42, 0.55)' : 'rgba(14, 60, 34, 0.55)';
      ctx.fill();
    }

    // markings: a wide faint pass for the glow, then the crisp line
    // (two strokes are far cheaper than shadowBlur on every frame)
    drawMarkings(5, 'rgba(215, 255, 58, 0.07)');
    drawMarkings(1.4, 'rgba(230, 255, 210, 0.34)');

    // a scanning light sweep moving down the pitch
    if (!reduced) {
      const sz = ((t * 9) % (PITCH_L + 30)) - 15;
      const [, sy] = project(PITCH_W / 2, sz);
      const g = ctx.createLinearGradient(0, sy - 60, 0, sy + 60);
      g.addColorStop(0, 'rgba(215,255,58,0)');
      g.addColorStop(0.5, 'rgba(215,255,58,0.06)');
      g.addColorStop(1, 'rgba(215,255,58,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, sy - 60, w, 120);
    }

    // floodlight beams from the top corners, swaying slowly
    drawBeam(w * 0.08, -h * 0.05, 0.62 + Math.sin(t * 0.35) * 0.08, t);
    drawBeam(w * 0.92, -h * 0.05, Math.PI - 0.62 - Math.sin(t * 0.3 + 1.3) * 0.08, t);

    // floodlight dust
    for (const p of dust) {
      if (!reduced) {
        p.y += p.vy; p.x += p.vx; p.tw += 0.03;
        if (p.y < -10) Object.assign(p, newDust(false));
      }
      const a = p.a * (0.6 + 0.4 * Math.sin(p.tw));
      ctx.fillStyle = `rgba(235, 255, 200, ${a})`;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
    }

    if (running) raf = requestAnimationFrame(draw);
  }

  function start() { if (!running && !reduced) { running = true; raf = requestAnimationFrame(draw); } }
  function stop() { running = false; cancelAnimationFrame(raf); }

  window.addEventListener('resize', resize, { passive: true });
  window.addEventListener('pointermove', (e) => {
    cam.tx = (e.clientX / window.innerWidth - 0.5) * 2;
    cam.ty = (e.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
  new IntersectionObserver(([entry]) => (entry.isIntersecting ? start() : stop())).observe(canvas);

  resize();
  start();
}
