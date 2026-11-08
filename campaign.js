// Visitor-session timer. Counts from the moment this browser tab session first
// opened the page; it is NOT a calendar deadline and says nothing about the
// merchant's pricing, stock or offer availability.
export const SESSION_KEY = 'lumivelle-session-start';
export const DEFAULT_DURATION = 5400;

export function getSessionStart(storage, nowMs) {
  let stored = null;
  try { stored = storage.getItem(SESSION_KEY); } catch (e) { stored = null; }
  const parsed = Number(stored);
  if (stored !== null && stored !== '' && Number.isFinite(parsed) && parsed > 0) return parsed;
  try { storage.setItem(SESSION_KEY, String(nowMs)); } catch (e) { /* storage denied: timer lives in memory only */ }
  return nowMs;
}

export function getRemainingSeconds(startMs, nowMs, durationSeconds) {
  const elapsed = Math.max(0, Math.floor((nowMs - startMs) / 1000));
  return Math.min(durationSeconds, Math.max(0, durationSeconds - elapsed));
}

export function formatCountdown(seconds) {
  const s = Number.isFinite(seconds) && seconds > 0 ? Math.floor(seconds) : 0;
  const pad = (n) => String(n).padStart(2, '0');
  return { hours: pad(Math.floor(s / 3600)), minutes: pad(Math.floor((s % 3600) / 60)), seconds: pad(s % 60) };
}

function boot() {
  const root = document.getElementById('session-countdown');
  if (!root) return;
  const duration = Number(root.dataset.durationSeconds) || DEFAULT_DURATION;
  let storage = { getItem: () => null, setItem: () => {} };
  try { storage = window.sessionStorage; } catch (e) { /* denied */ }
  const start = getSessionStart(storage, Date.now());
  const parts = {
    hours: root.querySelector('[data-unit="hours"]'),
    minutes: root.querySelector('[data-unit="minutes"]'),
    seconds: root.querySelector('[data-unit="seconds"]'),
  };
  const state = root.closest('#campaign-banner')?.querySelector('[data-state]');
  let timer = null;
  function render() {
    const left = getRemainingSeconds(start, Date.now(), duration);
    const f = formatCountdown(left);
    for (const key of Object.keys(parts)) if (parts[key]) parts[key].textContent = f[key];
    root.dataset.start = String(start);
    root.dataset.remaining = String(left);
    root.setAttribute('aria-label', 'Session timer: ' + Number(f.hours) + ' hours, ' + Number(f.minutes) + ' minutes remaining');
    if (left === 0) {
      root.dataset.complete = 'true';
      if (state) state.textContent = 'Session timer complete. Package options remain available on the order page.';
      if (timer) clearInterval(timer);
    }
  }
  render();
  if (root.dataset.complete !== 'true') timer = setInterval(render, 1000);
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
}
