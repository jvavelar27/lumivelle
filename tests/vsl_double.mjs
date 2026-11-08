// TEST DOUBLE ONLY. A minimal browser + Vimeo player.js boundary so the real
// assets/vsl/vsl-player.js can run in Node. It does not simulate or claim any
// real Vimeo behaviour: events are emitted only when a test calls emit().
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

class FakePlayer {
  static instances = [];
  constructor(el) {
    if (FakePlayer.throwOnCreate) throw new Error('double: constructor failure');
    this.el = el;
    this.handlers = {};
    this.time = FakePlayer.startTime ?? 0;
    this.muted = true;
    this.volume = 1;
    this.readyMode = FakePlayer.readyMode || 'resolve';
    FakePlayer.instances.push(this);
  }
  on(e, f) { (this.handlers[e] ||= []).push(f); }
  ready() {
    if (this.readyMode === 'reject') return Promise.reject(new Error('double: not ready'));
    if (this.readyMode === 'never') return new Promise(() => {});
    return Promise.resolve();
  }
  getCurrentTime() { return Promise.resolve(this.time); }
  getMuted() { return FakePlayer.mutedFails ? Promise.reject(new Error('x')) : Promise.resolve(this.muted); }
  getVolume() { return Promise.resolve(this.volume); }
  emit(e, data) { (this.handlers[e] || []).forEach((f) => f(data)); }
}

export function loadPage({ vimeo = true, storage = 'ok', store = new Map(), search = '', startTime, readyMode, throwOnCreate = false, mutedFails = false } = {}) {
  FakePlayer.instances = [];
  FakePlayer.startTime = startTime;
  FakePlayer.readyMode = readyMode;
  FakePlayer.throwOnCreate = throwOnCreate;
  FakePlayer.mutedFails = mutedFails;
  const video = new El('div', { id: 'video', 'data-vdelay': '2834', 'data-video-id': '1244806219', 'data-stage': '' });
  const iframe = new El('iframe');
  const offer = new El('div', { 'data-reveal-scroll': 'fit', 'data-reveal-scroll-delay': '600' });
  const notice = new El('p', { 'data-offer-notice': 'Your order option is now available below the video.' });
  const buy = new El('a', { href: CHECKOUT });
  const status = new El('p', { id: 'player-status' });
  status.hidden = true;
  const body = new El('body');
  offer.style.display = 'none';
  offer.querySelector = (s) => (s === '[data-offer-notice]' ? notice : null);
  const docListeners = {};
  const document = {
    readyState: 'complete',
    body,
    documentElement: new El('html'),
    getElementById: (id) => ({ video, 'player-status': status }[id] || null),
    querySelector: (s) => (s === 'iframe' || s === '#video iframe' ? iframe : null),
    querySelectorAll: (s) => (s === '.esconder' ? [offer] : s === 'a.buylink' || s === '.buylink' ? [buy] : []),
    addEventListener: (t, f) => (docListeners[t] ||= []).push(f),
    removeEventListener() {},
  };
  const timers = [];
  let now = 0;
  let id = 0;
  const win = {
    document,
    Vimeo: vimeo ? { Player: FakePlayer } : undefined,
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
    win, document, body, video, offer, notice, buy, status, iframe, store, error, advance, docListeners,
    player: FakePlayer.instances[0],
    revealed: () => offer.style.display === 'block' && body.classList.contains('is-revealed'),
  };
}
