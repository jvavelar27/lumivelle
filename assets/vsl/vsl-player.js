/* vsl-player.js — LumiVelle /vsl page behaviour on the Wistia player.

   Adapted from the H&W vsl-pitch.js (stage, pitch reveal, fit lines), using the
   core Wistia Aurora <wistia-player> component (direct properties and events,
   not the legacy queue-based API):

     1. the order button opens when the viewer's PLAYBACK reaches the pitch
        second (data-vdelay on #video = 2834 = 47:14). Never wall-clock time,
        never a query-string shortcut, never as an error or timeout fallback:
        pausing stops progress toward it, and the button only appears from
        player.currentTime read on time-update / seeked / api-ready, or from the
        resume position of an already-ready player. Event payloads are never
        trusted; no window message listener exists.
     2. start — the video never plays by itself: a visible button starts it with
        sound. The trusted click handler sets muted=false, volume=1 and calls
        play() synchronously (no await first, or the gesture is lost). The overlay
        hides only once playback really has sound; a failed play() leaves it
        retryable with a clear message.
     2b. stage — real sound on (player.muted === false and volume > 0): headline
        shrinks, player grows and pins until the pitch (Escape steps out)
     3. reveal — body.is-revealed, announcement, "fit" scroll
     4. player failure / slow load — a visible status with a reload link only
     5. tracking params carried onto the checkout link without touching hid/affid */
(function () {
  "use strict";

  var video = document.getElementById("video");
  var status = document.getElementById("player-status");
  var startOverlay = document.getElementById("start-overlay");
  var startButton = document.getElementById("start-video");
  var startNote = document.getElementById("start-note");
  var offers = Array.prototype.slice.call(document.querySelectorAll(".esconder"));

  var UNLOCK_SECONDS = video ? Number(video.getAttribute("data-vdelay")) || 0 : 0;
  var VIDEO_ID = video ? video.getAttribute("data-video-id") || "" : "";
  var STORAGE_KEY = "lumivelle-vsl-unlock:" + VIDEO_ID + ":" + UNLOCK_SECONDS;
  var PLAYER_TAG = "wistia-player";
  var READY_TIMEOUT_MS = 20000;

  var lessMotion = function () {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  };

  /* [data-fit-line] text shrinks until it fits its box on one line, 11px
     floor; below that it wraps. */
  var shrinkToFit = function (text) {
    var box = text.parentNode;
    if (!box) return;
    text.style.fontSize = "";
    text.style.whiteSpace = "";
    var cs = window.getComputedStyle(box);
    var available = box.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
    if (!available || !text.scrollWidth || text.scrollWidth <= available) return;

    var base = parseFloat(window.getComputedStyle(text).fontSize) || 20;
    var size = Math.max(11, Math.floor((base * available) / text.scrollWidth));
    text.style.fontSize = size + "px";
    for (var pass = 0; text.scrollWidth > available && size > 11 && pass < 6; pass++) {
      size = Math.max(11, Math.floor((size * available) / text.scrollWidth));
      text.style.fontSize = size + "px";
    }
    text.style.whiteSpace = text.scrollWidth > available ? "normal" : "";
  };

  var fitLines = function () {
    Array.prototype.forEach.call(document.querySelectorAll("[data-fit-line]"), shrinkToFit);
  };

  /* ---- Checkout tracking -------------------------------------------------- */

  /* Only these fields travel, and only when the checkout link does not
     already carry them: hid and affid (and anything else) are never touched. */
  var TRACKING = /^(utm_(source|medium|campaign|term|content)|fbclid|gclid|ttclid|click_id|clickid|sub[1-5]|src|sck)$/;

  var carryTracking = function () {
    var incoming;
    try {
      incoming = new URLSearchParams(window.location.search);
    } catch (e) {
      return;
    }
    var extra = [];
    Array.prototype.forEach.call(document.querySelectorAll("a.buylink"), function (link) {
      var href = link.href || "";
      var query = href.indexOf("?") === -1 ? "" : href.slice(href.indexOf("?") + 1);
      var present = new URLSearchParams(query);
      extra = [];
      incoming.forEach(function (value, key) {
        if (!TRACKING.test(key) || present.has(key) || !value || value.length > 200) return;
        extra.push(encodeURIComponent(key) + "=" + encodeURIComponent(value));
      });
      if (extra.length) link.href = href + (query ? "&" : "?") + extra.join("&");
    });
  };

  /* ---- Session memory of an earned reveal ---------------------------------- */

  var readRevealed = function () {
    try {
      return window.sessionStorage.getItem(STORAGE_KEY) === "1";
    } catch (e) {
      return false;
    }
  };

  var saveRevealed = function () {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, "1");
    } catch (e) {
      /* storage denied: the reveal still happens, it just is not remembered */
    }
  };

  /* ---- Stage -------------------------------------------------------------- */

  var revealed = false;
  var stageActive = false;
  var stageDone = false;

  var measureSticky = function () {
    var pinned = document.querySelector(".vsl-video");
    var height = pinned && document.body.classList.contains("is-stripped") ? pinned.offsetHeight : 0;
    document.body.style.setProperty("--sticky-h", height + "px");
  };

  var enterStage = function () {
    if (stageActive || stageDone || revealed) return;
    stageActive = true;
    /* The stage never makes the player narrower than it is now. */
    if (video) video.style.setProperty("--vsl-rest-w", video.offsetWidth + "px");
    document.body.classList.add("is-stage", "is-stripped");
    window.setTimeout(measureSticky, 600); /* after the transition */
  };

  var exitStage = function () {
    if (!stageActive) return;
    stageActive = false;
    stageDone = true;
    document.body.classList.remove("is-stage");
  };

  /* Sound counts as on only when the player says so: muted is exactly false
     and volume is above zero. Anything else keeps the page out of the stage. */
  var checkSound = function (player) {
    if (player.muted === false && typeof player.volume === "number" && player.volume > 0) enterStage();
  };

  if (video && video.hasAttribute("data-stage")) {
    document.addEventListener("keydown", function (e) {
      if (stageActive && (e.key === "Escape" || e.key === "Esc")) exitStage();
    });
  }

  /* ---- Reveal ------------------------------------------------------------- */

  var scrollOnReveal = function (offer) {
    var mode = offer.getAttribute("data-reveal-scroll");
    if (mode !== "fit") return;
    var behavior = lessMotion() ? "auto" : "smooth";
    var wait = Number(offer.getAttribute("data-reveal-scroll-delay")) || 0;
    window.setTimeout(function () {
      var overflow = offer.getBoundingClientRect().bottom - window.innerHeight;
      if (overflow > 0) window.scrollBy({ top: overflow + 16, behavior: behavior });
    }, wait);
  };

  /* An endless pulse off screen is wasted paint. */
  var pauseWhenOffscreen = function (offer) {
    if (!window.IntersectionObserver) return;
    var target = offer.querySelector(".vsl-cta") || offer;
    new window.IntersectionObserver(function (entries) {
      document.body.classList.toggle("cta-offscreen", !entries[entries.length - 1].isIntersecting);
    }).observe(target);
  };

  var reveal = function (restored) {
    if (revealed) return;
    revealed = true;
    offers.forEach(function (offer) {
      offer.style.display = "block";
    });
    document.body.classList.add("is-revealed");
    exitStage();
    fitLines();
    offers.forEach(function (offer) {
      pauseWhenOffscreen(offer);
      /* screen readers hear that the button arrived */
      var notice = offer.querySelector("[data-offer-notice]");
      if (notice) notice.textContent = notice.getAttribute("data-offer-notice");
      if (!restored) scrollOnReveal(offer);
    });
    if (!restored) saveRevealed();
  };

  /* A position unlocks the offer only if it is a real, finite number of
     seconds at or past the pitch second. */
  var handlePosition = function (seconds) {
    if (typeof seconds !== "number" || !isFinite(seconds)) return;
    if (UNLOCK_SECONDS > 0 && seconds >= UNLOCK_SECONDS) reveal(false);
  };

  /* ---- Start with sound ---------------------------------------------------- */

  var soundOn = function (player) {
    return player.muted === false && typeof player.volume === "number" && player.volume > 0;
  };

  var setStartNote = function (text) {
    if (startNote) startNote.textContent = text;
  };

  var enableStart = function () {
    if (!startButton) return;
    startButton.disabled = false;
    setStartNote("");
  };

  var hideOverlay = function () {
    if (startOverlay) startOverlay.hidden = true;
    hideStatus();
  };

  /* Playing with sound, however it began (our button or the native controls),
     is a started video. Muted playback is not: the overlay stays. */
  var maybeStarted = function (player) {
    if (soundOn(player) && player.paused !== true) hideOverlay();
  };

  var startFailed = function () {
    if (startButton) startButton.disabled = false;
    setStartNote("");
    showStatus("The video could not start. Tap Play video with sound to try again.", true);
  };

  var bindStart = function (player) {
    if (!startButton) return;
    startButton.addEventListener("click", function (e) {
      /* only a real user gesture starts the video, and never a disabled button */
      if (!e || e.isTrusted !== true || startButton.disabled) return;
      var result;
      try {
        /* all in this same handler, synchronously: awaiting first loses the gesture */
        player.muted = false;
        player.volume = 1;
        result = player.play();
      } catch (err) {
        return startFailed();
      }
      startButton.disabled = true;
      setStartNote("Starting video…");
      Promise.resolve(result).then(
        function () {
          if (startButton) startButton.disabled = false;
          setStartNote("");
          maybeStarted(player);
        },
        startFailed
      );
    });
  };

  /* ---- Player status ------------------------------------------------------ */

  var showStatus = function (message, retryable) {
    if (!status) return;
    status.innerHTML = retryable ? message : message + ' <a href="/vsl">Reload this page</a> to try again.';
    status.hidden = false;
    if (!retryable) setStartNote("");
  };

  var hideStatus = function () {
    if (status) status.hidden = true;
  };

  /* ---- Boot --------------------------------------------------------------- */

  var boot = function () {
    carryTracking();
    if (readRevealed()) reveal(true);

    var player = document.querySelector("#video " + PLAYER_TAG);
    if (!player) return showStatus("The video could not be found.");
    if (!window.customElements || typeof window.customElements.whenDefined !== "function") {
      return showStatus("This browser cannot run the video player.");
    }

    var ready = false;
    var timeout = null;

    var markReady = function () {
      ready = true;
      window.clearTimeout(timeout);
      hideStatus();
      enableStart();
      /* resume: the viewer may already be past the pitch */
      handlePosition(player.currentTime);
    };

    /* There is no apiReady flag: a finite duration above zero (and usable
       methods) means the media metadata is initialised. */
    var checkReady = function () {
      if (ready) return;
      var d = player.duration;
      if (typeof d === "number" && isFinite(d) && d > 0 && typeof player.play === "function") markReady();
    };

    /* Listen right away: an element that is not defined yet can already
       receive listeners, and the component fires them once it is upgraded. */
    player.addEventListener("api-ready", markReady);
    player.addEventListener("time-update", function () {
      handlePosition(player.currentTime);
    });
    player.addEventListener("seeked", function () {
      handlePosition(player.currentTime);
    });
    player.addEventListener("play", function () {
      checkSound(player);
      maybeStarted(player);
    });
    player.addEventListener("volume-change", function () {
      checkSound(player);
      maybeStarted(player);
    });
    bindStart(player);

    timeout = window.setTimeout(function () {
      if (!ready) showStatus("The video player is taking too long to load.");
    }, READY_TIMEOUT_MS);

    window.customElements.whenDefined(PLAYER_TAG).then(checkReady, function () {
      window.clearTimeout(timeout);
      showStatus("The video player could not load.");
    });
    checkReady();
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  fitLines();
  var lastWidth = window.innerWidth;
  var resizeTimer = null;
  window.addEventListener("resize", function () {
    if (window.innerWidth === lastWidth) return; /* mobile URL bar show/hide */
    lastWidth = window.innerWidth;
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      fitLines();
      measureSticky();
    }, 150);
  });
})();
