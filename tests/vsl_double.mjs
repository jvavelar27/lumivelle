// TEST DOUBLE ONLY. A minimal browser + <wistia-player> boundary so the real
// assets/vsl/vsl-player.js can run in Node. It does not simulate or claim any
// real Wistia behaviour: events fire only when a test calls emit(), and every
// property (currentTime, duration, muted...) is set by the test. Real playback
// is verified separately in a browser.
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
export const CHECKOUT = 'https://order.wealthpay.io/qo52qotcz7vr?hid=b2lkPW9mZl82NDcxMDc5JmFpZD1hZmZfMjg3NzUxNCZ1aWQ9YmxfODY3NTQxMQ%3D%3D&affid=aff_2877514';
export const flush = () => new Promise((r) => setImmediate(r));

class El {
  constructor(name, attrs = {}) {
    this.name = name;
    this.attrs = { ...attrs };
    this.style = { setProperty(k, v) { this[k] = v; } };
    this._c = new Set();
    this.listeners = {};
    this.textContent = '';
    this.innerHTML = '';
    this.hidden = false;
    this.href = attrs.href || '';
    this.offsetWidth = 400;
    this.offsetHeight = 500;
    this.clientWidth = 300;
    this.scrollWidth = 200;
    this.parentNode = null;
    const self = this;
    this.classList = {
      add: (...c) => c.forEach((x) => self._c.add(x)),
      remove: (...c) => c.forEach((x) => self._c.delete(x)),
      contains: (c) => self._c.has(c),
      toggle: (c, on) => (on ? self._c.add(c) : self._c.delete(c)),
    };
  }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  setAttribute(k, v) { this.attrs[k] = v; }
  addEventListener(t, f) { (this.listeners[t] ||= []).push(f); }
  removeEventListener() {}
  querySelector() { return null; }
  getBoundingClientRect() { return { bottom: 100, top: 0 }; }
  scrollIntoView() {}
}

// Stands in for <wistia-player>. Before "definition" it only accepts listeners,
// like a not-yet-upgraded custom element; the test decides when it is usable.
class FakeWistia extends El {
  constructor() {
    super('wistia-player', { 'media-id': 'dr4rq15xr1' });
    this._t = 0;
    this.duration = 0;
    this.readyState = 0;
    this.paused = true;
    this._muted = true;
    this._volume = 1;
    this._silentAutoplay = true;
    this.log = []; // ordered record of writes and calls made BY THE PAGE
    this.playMode = 'resolve'; // 'resolve' | 'reject' | 'throw' | 'pending' | 'resolve-silent'
    this.seekMode = 'instant'; // 'instant' | 'stale' (position keeps its old value until settleSeek())
    this._pendingSeek = null;
  }
  get currentTime() { return this._t; }
  set currentTime(v) {
    this.log.push('currentTime=' + v);
    if (this.seekMode === 'stale') this._pendingSeek = v; else this._t = v;
  }
  settleSeek() { if (this._pendingSeek !== null) { this._t = this._pendingSeek; this._pendingSeek = null; } }
  get muted() { return this._muted; }
  set muted(v) { this._muted = v; this.log.push('muted=' + v); }
  get volume() { return this._volume; }
  set volume(v) { this._volume = v; this.log.push('volume=' + v); }
  get silentAutoplay() { return this._silentAutoplay; }
  set silentAutoplay(v) { this._silentAutoplay = v; this.log.push('silentAutoplay=' + v); }
  emit(type, detail) { (this.listeners[type] || []).forEach((f) => f({ type, detail })); }
  // test helper: the component finishes defining and metadata is initialised
  makeReady(time = 0) {
    this.duration = 3908.13; this.readyState = 4; this._t = time;
    this.play = () => {
      this.log.push('play');
      if (this.playMode === 'throw') throw new Error('double: play threw');
      if (this.playMode === 'reject') return Promise.reject(new Error('double: play rejected'));
      if (this.playMode === 'pending') return new Promise(() => {});
      if (this.playMode !== 'resolve-silent') this.paused = false;
      return Promise.resolve();
    };
    this.pause = () => { this.log.push('pause'); this.paused = true; };
  }
}

// defined: 'resolve' | 'late' | 'never' | 'reject' | 'missing' (no customElements at all)
export function loadPage({ defined = 'resolve', alreadyReady = false, startTime = 0, noPlayer = false, storage = 'ok', store = new Map(), search = '' } = {}) {
  const video = new El('div', { id: 'video', 'data-vdelay': '2834', 'data-video-id': 'dr4rq15xr1', 'data-stage': '' });
  const player = noPlayer ? null : new FakeWistia();
  if (player && alreadyReady) player.makeReady(startTime);
  const offer = new El('div', { 'data-reveal-scroll': 'fit', 'data-reveal-scroll-delay': '600' });
  const notice = new El('p', { 'data-offer-notice': 'Your order option is now available below the video.' });
  const buy = new El('a', { href: CHECKOUT });
  const status = new El('p', { id: 'player-status' });
  status.hidden = true;
  const body = new El('body');
  const startButton = new El('button', { id: 'start-video', type: 'button' });
  startButton.disabled = true;
  const startOverlay = new El('div', { id: 'start-overlay' });
  const startNote = new El('p', { id: 'start-note' });
  startNote.textContent = 'Loading video…';
  offer.style.display = 'none';
  offer.querySelector = (s) => (s === '[data-offer-notice]' ? notice : null);
  const docListeners = {};
  const document = {
    readyState: 'complete',
    body,
    documentElement: new El('html'),
    getElementById: (id) => ({ video, 'player-status': status, 'start-video': startButton, 'start-overlay': startOverlay, 'start-note': startNote }[id] || null),
    querySelector: (s) => (s === 'wistia-player' || s === '#video wistia-player' ? player : null),
    querySelectorAll: (s) => (s === '.esconder' ? [offer] : s === 'a.buylink' || s === '.buylink' ? [buy] : []),
    addEventListener: (t, f) => (docListeners[t] ||= []).push(f),
    removeEventListener() {},
  };
  let defineNow = () => {};
  const customElements = {
    whenDefined: () => {
      if (defined === 'never') return new Promise(() => {});
      if (defined === 'reject') return Promise.reject(new Error('double: definition failed'));
      if (defined === 'late') return new Promise((resolve) => { defineNow = resolve; });
      return Promise.resolve();
    },
  };
  const timers = [];
  let now = 0;
  let id = 0;
  const win = {
    document,
    customElements: defined === 'missing' ? undefined : customElements,
    location: { search, href: 'https://lumivelle-topaz.vercel.app/vsl' + search, pathname: '/vsl' },
    innerWidth: 400,
    innerHeight: 800,
    scrollCalls: [],
    listeners: {},
    setTimeout: (f, ms = 0) => { timers.push({ id: ++id, f, at: now + ms }); return id; },
    clearTimeout: (i) => { const k = timers.findIndex((t) => t.id === i); if (k >= 0) timers.splice(k, 1); },
    matchMedia: () => ({ matches: false }),
    getComputedStyle: () => ({ display: 'none', paddingLeft: '0', paddingRight: '0', fontSize: '20px' }),
    scrollBy: (o) => win.scrollCalls.push(o),
    scrollTo() {},
    addEventListener: (t, f) => (win.listeners[t] ||= []).push(f),
    removeEventListener() {},
    URLSearchParams, URL, Number, Math, parseFloat, isFinite, Array, Object, String, Promise, JSON, console,
  };
  if (storage === 'ok') {
    win.sessionStorage = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)) };
  } else {
    Object.defineProperty(win, 'sessionStorage', { get() { throw new Error('SecurityError: storage denied'); } });
  }
  win.window = win;
  win.self = win;
  vm.createContext(win);
  let error = null;
  try {
    vm.runInContext(readFileSync(join(root, 'assets/vsl/vsl-player.js'), 'utf-8'), win, { filename: 'vsl-player.js' });
  } catch (e) {
    error = String(e);
  }
  const advance = (ms) => {
    now += ms;
    for (;;) {
      const due = timers.filter((t) => t.at <= now).sort((a, b) => a.at - b.at)[0];
      if (!due) break;
      timers.splice(timers.indexOf(due), 1);
      due.f();
    }
  };
  return {
    win, document, body, video, offer, notice, buy, status, store, error, advance, docListeners, player, startButton, startOverlay, startNote,
    // a physical click/tap/Enter arrives as a trusted click; isTrusted:false models script-made events
    click: (isTrusted = true, extra = {}) => (startButton.listeners.click || []).forEach((f) => f({ type: 'click', isTrusted, preventDefault() {}, ...extra })),
    define: () => defineNow(),
    // tests move the playhead and then fire the event, as the component would
    at: (seconds, type = 'time-update', detail) => { player._t = seconds; player.emit(type, detail); },
    revealed: () => offer.style.display === 'block' && body.classList.contains('is-revealed'),
  };
}
