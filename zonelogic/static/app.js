// ZoneLogic frontend. All geometry is normalized 0..1 so zones survive any display size.
const BASE = location.pathname.endsWith("/") ? location.pathname : location.pathname + "/";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const api = async (path, body) => {
  const r = await fetch(BASE + path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : undefined);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
};

const state = { seg: 0, clip: null, zones: [], rules: [], events: [], drawing: null, nextRule: 1,
                playing: false, t: 0, lastT: 0, wallStart: 0, tStart: 0 };
const video = $("video"), canvas = $("overlay"), ctx = canvas.getContext("2d");

// ---- player: a playlist of segment videos on one timeline, or a virtual clock when a clip has no video.
// VAST stores each 30 s chunk as six 5 s segment files; clip.segments = [{t0, duration, video}].
const segs = () => (state.clip && state.clip.segments) || [];
const hasVideo = () => segs().length > 0;
const duration = () => (state.clip && state.clip.duration) || 0;
const mediaUrl = (v) => (/^https?:/.test(v) ? v : BASE + v);
function now() {
  if (hasVideo()) return segs()[state.seg].t0 + video.currentTime;
  if (state.playing) return Math.min(duration(), state.tStart + (performance.now() - state.wallStart) / 1000);
  return state.t;
}
function loadSeg(i, offset) {
  state.seg = i;
  const src = mediaUrl(segs()[i].video);
  const go = () => { video.currentTime = offset; if (state.playing) video.play().catch(() => {}); };
  if (video.dataset.src !== src) {
    video.dataset.src = src; video.src = src;
    video.addEventListener("loadedmetadata", go, { once: true });
  } else go();
}
function seek(t) {
  t = Math.max(0, Math.min(duration(), t));
  if (hasVideo()) {
    let i = segs().findIndex((s) => t < s.t0 + s.duration);
    if (i < 0) i = segs().length - 1;
    loadSeg(i, Math.min(t - segs()[i].t0, segs()[i].duration - 0.05));
  }
  state.t = state.tStart = t; state.wallStart = performance.now(); state.lastT = t;
}
function setPlaying(on) {
  if (on && now() >= duration() - 0.05) seek(0);
  state.playing = on;
  if (hasVideo()) on ? video.play().catch(() => {}) : video.pause();
  else { state.tStart = state.t; state.wallStart = performance.now(); }
  $("play").textContent = on ? "Pause" : "Play";
}
video.onended = () => {
  if (state.seg + 1 < segs().length) loadSeg(state.seg + 1, 0);
  else setPlaying(false);
};

// ---- clips
async function loadClips() {
  const list = await api("api/clips");
  $("clip").innerHTML = list.map((c) =>
    `<option value="${esc(c.id)}">${esc(c.camera_id)} / ${esc(c.id)}${c.source === "synthetic" ? " (synthetic)" : ""}</option>`).join("");
  if (list.length) await openClip(list[0].id);
}
async function openClip(id, t = 0) {
  setPlaying(false);
  state.clip = await api("api/clips/" + encodeURIComponent(id));
  state.clip.frames.sort((a, b) => a.t - b.t);
  $("clip").value = id;
  $("synthetic").style.display = state.clip.source === "synthetic" ? "block" : "none";
  if (!state.clip.segments && state.clip.video_url)
    state.clip.segments = [{ t0: 0, duration: state.clip.duration, video: state.clip.video_url }];
  delete video.dataset.src; state.seg = 0;
  if (hasVideo()) video.style.display = "block";
  else { video.removeAttribute("src"); video.style.display = "none"; }
  seek(t);
}
$("clip").onchange = (e) => openClip(e.target.value);

function framesAt(t) { // last frame at or before t
  const f = state.clip ? state.clip.frames : [];
  let lo = 0, hi = f.length - 1, best = null;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (f[m].t <= t) { best = f[m]; lo = m + 1; } else hi = m - 1; }
  return best;
}

// ---- drawing
function resize() {
  const r = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  canvas.width = r.width * dpr; canvas.height = r.height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
new ResizeObserver(resize).observe(canvas);

function poly(points, fill, stroke) {
  const { width: w, height: h } = canvas.getBoundingClientRect();
  ctx.beginPath();
  points.forEach(([x, y], i) => (i ? ctx.lineTo(x * w, y * h) : ctx.moveTo(x * w, y * h)));
  ctx.closePath();
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.stroke();
}

function render() {
  const { width: w, height: h } = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, w, h);
  const t = now();
  ctx.font = "12px system-ui"; ctx.textBaseline = "bottom";
  for (const z of state.zones) {
    poly(z.polygon, "rgba(63,182,168,.22)", "#3fb6a8");
    ctx.fillStyle = "#3fb6a8"; ctx.fillText(z.name, z.polygon[0][0] * w + 4, z.polygon[0][1] * h - 2);
  }
  if (state.drawing && state.drawing.length) {
    ctx.setLineDash([6, 4]); poly(state.drawing, null, "#fff"); ctx.setLineDash([]);
    for (const [x, y] of state.drawing) { ctx.fillStyle = "#fff"; ctx.fillRect(x * w - 3, y * h - 3, 6, 6); }
  }
  const f = framesAt(t);
  // an incident is "live" for a second after it fires, so its box shows in red
  const live = state.events.filter((e) => e.clip_id === state.clip?.id && t >= e.t && t - e.t < 1.0);
  if (f && $("showBoxes").checked) {
    for (const d of f.dets) {
      const [x1, y1, x2, y2] = d.box;
      const hot = live.some((e) => e.cls === d.cls && Math.abs(e.box[0] - x1) < 0.05 && Math.abs(e.box[1] - y1) < 0.05);
      ctx.strokeStyle = hot ? "#e5534b" : "#7ee787"; ctx.lineWidth = hot ? 3 : 1.5;
      ctx.strokeRect(x1 * w, y1 * h, (x2 - x1) * w, (y2 - y1) * h);
      ctx.fillStyle = ctx.strokeStyle; ctx.fillText(`${d.cls} ${Math.round(d.conf * 100)}%`, x1 * w + 2, y1 * h - 2);
    }
  }
  // fire alerts for incidents crossed during playback
  if (state.playing) {
    for (const e of state.events)
      if (e.clip_id === state.clip?.id && e.status === "open" && e.t > state.lastT && e.t <= t) alertFor(e);
    if (!hasVideo() && t >= duration()) setPlaying(false);
  }
  state.lastT = t; if (!hasVideo()) state.t = t;
  const d = duration() || 1;
  $("scrub").max = d; if (document.activeElement !== $("scrub")) $("scrub").value = t;
  $("time").textContent = `${t.toFixed(1)} / ${d.toFixed(1)} s`;
  requestAnimationFrame(render);
}

canvas.addEventListener("click", (e) => {
  if (!state.drawing) return;
  const r = canvas.getBoundingClientRect();
  state.drawing.push([(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height]);
  $("finish").disabled = state.drawing.length < 3;
});
$("draw").onclick = () => {
  state.drawing = []; $("stage").classList.add("drawing");
  $("draw").disabled = true; $("cancel").disabled = false;
};
function stopDrawing() {
  state.drawing = null; $("stage").classList.remove("drawing");
  $("draw").disabled = false; $("finish").disabled = true; $("cancel").disabled = true;
}
$("cancel").onclick = stopDrawing;
$("finish").onclick = () => {
  let name = $("zoneName").value.trim() || `zone ${state.zones.length + 1}`;
  if (state.zones.some((z) => z.name === name)) name += ` (${state.zones.length + 1})`;
  state.zones.push({ name, polygon: state.drawing.map(([x, y]) => [+x.toFixed(4), +y.toFixed(4)]) });
  $("zoneName").value = ""; stopDrawing(); renderLists();
};

// ---- rules
$("addRule").onclick = () => {
  const zone = $("ruleZone").value;
  const classes = $("ruleClasses").value.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
  if (!zone) return status("Draw a zone first.");
  if (!classes.length) return status("Give at least one object class.");
  state.rules.push({
    id: `r${state.nextRule++}`, zone, classes, trigger: $("ruleTrigger").value,
    dwell_s: +$("ruleDwell").value || 0, anchor: $("ruleAnchor").value,
    min_overlap: 0.3, min_conf: +$("ruleConf").value || 0,
  });
  renderLists();
};
const describe = (r) => `${r.id}: ${r.classes.join("/")} ${r.trigger === "dwell"
  ? `inside "${r.zone}" for ${r.dwell_s}s+` : `enters "${r.zone}"`} (conf ≥ ${r.min_conf}, ${r.anchor})`;

function renderLists() {
  $("zones").innerHTML = state.zones.map((z, i) =>
    `<li>${esc(z.name)} <span class="muted">(${z.polygon.length} points)</span> <button data-zone="${i}">Delete</button></li>`).join("");
  $("ruleZone").innerHTML = state.zones.map((z) => `<option>${esc(z.name)}</option>`).join("");
  $("rules").innerHTML = state.rules.map((r, i) => `<li>${esc(describe(r))} <button data-rule="${i}">Delete</button></li>`).join("");
}
$("zones").onclick = (e) => {
  const i = e.target.dataset.zone; if (i === undefined) return;
  const name = state.zones[i].name;
  state.zones.splice(i, 1); state.rules = state.rules.filter((r) => r.zone !== name); renderLists();
};
$("rules").onclick = (e) => {
  const i = e.target.dataset.rule; if (i !== undefined) { state.rules.splice(i, 1); renderLists(); }
};

// ---- evaluation and incidents
const status = (msg) => { $("runStatus").textContent = msg; };
async function run(scope) {
  if (!state.rules.length) return status("Add a rule first.");
  const body = { zones: state.zones, rules: state.rules };
  status("Running…");
  try {
    const path = scope === "camera"
      ? `api/cameras/${encodeURIComponent(state.clip.camera_id)}/evaluate`
      : `api/clips/${encodeURIComponent(state.clip.id)}/evaluate`;
    const { events } = await api(path, body);
    const ruleById = Object.fromEntries(state.rules.map((r) => [r.id, r]));
    state.events = events.map((e) => ({ ...e, ruleText: describe(ruleById[e.rule]) }));
    const clipsHit = new Set(events.map((e) => e.clip_id)).size;
    status(`${events.length} incident(s)` + (scope === "camera" ? ` across ${clipsHit} clip(s) from ${state.clip.camera_id}` : ""));
    renderIncidents();
  } catch (err) { status("Error: " + err.message); }
}
$("runClip").onclick = () => run("clip");
$("runCamera").onclick = () => run("camera");

function renderIncidents() {
  const el = $("incidents");
  if (!state.events.length) { el.innerHTML = `<li class="muted">No incidents.</li>`; return; }
  el.innerHTML = state.events.map((e, i) => `
    <li class="ticket ${e.status}">
      <div><span class="tag">${e.status === "open" ? "OPEN" : "RESOLVED"}</span>
        <strong>${esc(e.cls)}</strong> ${e.trigger === "dwell" ? "stayed in" : "entered"} "${esc(e.zone)}"</div>
      <div class="meta">${esc(e.clip_id)} at ${e.t.toFixed(1)} s · confidence ${Math.round(e.conf * 100)}% · track ${e.track_id}</div>
      <div class="meta">${esc(e.ruleText)}</div>
      <div class="row"><button data-show="${i}">Show evidence</button>
        <button data-resolve="${i}">${e.status === "open" ? "Mark resolved" : "Reopen"}</button></div>
    </li>`).join("");
}
$("incidents").onclick = async (e) => {
  const { show, resolve } = e.target.dataset;
  if (show !== undefined) {
    const ev = state.events[show];
    if (ev.clip_id !== state.clip.id) await openClip(ev.clip_id, ev.t); else { setPlaying(false); seek(ev.t); }
  }
  if (resolve !== undefined) {
    const ev = state.events[resolve]; ev.status = ev.status === "open" ? "resolved" : "open"; renderIncidents();
  }
};

// ---- alert action: banner, beep, vibration where the browser supports it
let audio;
function alertFor(e) {
  const b = $("banner");
  b.textContent = `Rule ${e.rule}: ${e.cls} ${e.trigger === "dwell" ? "stayed in" : "entered"} "${e.zone}" at ${e.t.toFixed(1)} s`;
  b.style.display = "block"; clearTimeout(alertFor.timer);
  alertFor.timer = setTimeout(() => (b.style.display = "none"), 2500);
  try {
    audio = audio || new AudioContext();
    const o = audio.createOscillator(), g = audio.createGain();
    o.frequency.value = 880; g.gain.value = 0.15; o.connect(g).connect(audio.destination);
    o.start(); o.stop(audio.currentTime + 0.25);
  } catch {}
  if (navigator.vibrate) navigator.vibrate(200);
}

$("play").onclick = () => setPlaying(!state.playing);
$("scrub").oninput = (e) => seek(+e.target.value);

renderLists();
loadClips().catch((err) => status("Could not load clips: " + err.message));
requestAnimationFrame(render);
