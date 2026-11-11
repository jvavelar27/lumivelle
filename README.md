# LumiVelle landing page (static)

Static landing page: `index.html` (inline CSS/JS plus the `campaign.js` session-timer module, no frontend framework or package dependencies). Adapted from the `lp1-GLP-1.html` source layout (`.herolp`, `.born-cols`, `.ing-grid`, `.steps-grid`, `.offer-wrap`, `details.qa`).

## Run locally
    python -m http.server 8000     # then open http://localhost:8000

## Test
    python -m unittest discover -s tests -v

## Deploy (Vercel, static)
Import `jvavelar27/lumivelle`, framework Other. `vercel.json` sets `node scripts/build.mjs` as build command and `dist` as output directory, plus security headers and asset caching.
`npm run build` copies only HTML, favicon, `campaign.js` and optimized assets into `dist/`; tests, source notes and documentation are not published.

## Files
- `assets/` — optimized `.webp` images (product, hero, kit-2, kit-3). Product art must match the supplied label (`Affiliate Brief/images/cap-1-img1.png`, kept out of this repo).
- `privacy.html`, `terms.html` — short affiliate-page notices; checkout terms belong to the merchant.
- Original offer HTML variants, videos and outdated instructions were removed after adaptation. The user's brief remains outside the repository.
- All raster assets are WebP. The visual refresh uses `agent-image-generation / Luxin`: Nano Banana Pro for the reference-conditioned product hero; GPT Image 2 for the mature-woman editorial portrait, gelatin still life and empty photography set. Kits composite the original product cutout onto that set. `asset-manifest.json` records all four generation jobs/assets and exact image sizes/hashes. No billing or paid top-up was used.
- Versioned `*-editorial-v2.webp` filenames replace the previous generic backgrounds and contextual images, preventing stale image caches. Captions distinguish illustrations from customers/results. No provider watermark appears on the new generated imagery.
- Browser QA passed at 320, 375, 390, 768, 1024, 1440 and 812px landscape, including gallery, keyboard FAQ and JavaScript-disabled content.

## Known source limitations
- No exact ingredient amounts, serving size or Supplement Facts available; page avoids dosing, duration and results claims.
- Checkout shows conflicting prices ($79/$89/$99 per bottle vs $99 total for 3 bottles), so no prices, savings or durations are displayed.
- Verified from merchant modals: package renews every 28 days until canceled; optional Wellness Club is separate; refund requests do not cancel renewals. Page discloses this near the CTA and in the FAQ without repeating merchant dates or prices. Optional extras (money-back protection, express shipping) are default-on at checkout; the page tells buyers to review them. Terms/refund pages are modals on the merchant site, not linkable.
- Guarantee is described only as "60-day money-back guarantee, subject to the merchant's refund policy".
- Google Fonts is the only remote resource (typefaces); CSP in `vercel.json` allows it.
- Rating figures (4.8, 17,012+ reviews) were supplied by the advertiser and are shown as advertiser-provided, not independently verified, in the rating strip and review module. No individual testimonials, verified-buyer labels, third-party badges, prices or discounts are used.
- The top banner has a visitor-session timer (`campaign.js`): 90 minutes from first load in the tab session, stored in `sessionStorage`, never a calendar or offer deadline. See `DR-STRUCTURE.md` for the required direct-response section order.

## /vsl route (Wistia video page)
- `vsl.html` is served at `/vsl` (Vercel `cleanUrls`); it is independent of the root sales page and is `noindex, nofollow`. Layout, CSS, headline, three press logos and green button come from the supplied reference page. The video is the supplied Wistia embed: media `dr4rq15xr1` ("VSL 1 - LumiVelle [47_31]"), `aspect="0.8126410835214447"`, scripts `https://fast.wistia.com/player.js` and `https://fast.wistia.com/embed/dr4rq15xr1.js` (module), and the supplied `:not(:defined)` swatch placeholder style (it carries its own `padding-top`, so no CSS aspect-ratio is added).
- Player controls: a muted silent preview autoplays (`autoplay="true" muted="true" silent-autoplay="true"`), with `big-play-button="false"`, `play-bar-control="false"` (no timeline, seek slider or duration display), `play-pause-control="true"`, `volume-control="true"` and `playback-rate-control="false"`. Wistia branding and plan entitlements are untouched.
- Click for sound: a visible overlay inside `#video` holds a real `<button id="start-video" type="button" aria-label="Restart video with sound">` with the text "Click for sound". It is disabled (with "Loading video…") until the player is ready, and it works even if the browser blocked the preview. A trusted click, tap or Enter synchronously, in the same handler, pauses the preview, sets `silentAutoplay = false`, seeks `currentTime = 0`, sets `muted = false` and `volume = 1`, and calls `play()` (no await before `play()`, so the user gesture is kept). Repeated clicks while starting are ignored. The overlay hides only once the position is back near zero and playback really has sound; if `play()` rejects or throws, the button is re-enabled with a "try again" status. The preview being on screen never hides the overlay, and nothing else ever starts playback.
- The green purchase button opens at **2834 seconds of video playback (47:14)** in the real listening session (the one started by "Click for sound"), never wall-clock time and never from the silent preview, even if the preview is already past 2834. The page uses the core Wistia Aurora `<wistia-player>` API: after `customElements.whenDefined("wistia-player")`, `player.currentTime` is read on `time-update` and `seeked` only once the session is listening. While the seek to zero is in flight, callbacks still carrying the preview's old position are ignored. Readiness is a finite `duration` above zero (there is no documented ready flag) or `api-ready`. Event payloads and window messages are never trusted. There is no `?test=true`/debug shortcut, and a slow or failed player shows a visible status with a reload link without unlocking anything. The title `[47_31]` is the supplied identifier, not the unlock time.
- An earned reveal is remembered in `sessionStorage` under the versioned key `lumivelle-vsl-listen-unlock:v2:dr4rq15xr1:2834` (legacy preview-era and Vimeo keys cannot open it and are not migrated); denied storage degrades gracefully.
- Sound "stage" (headline shrink, player growth and pin) starts only in the listening session when `player.muted === false` and `volume > 0`; Escape steps out. Without JavaScript a notice explains JavaScript is required.
- Only allowlisted tracking fields (utm_*, fbclid, gclid, ttclid, click_id, sub1-5, src, sck) are appended to the checkout link, never overriding `hid`/`affid`.
- `vercel.json` CSP allows only the Wistia hosts observed in a real playback probe (fast.wistia.com/.net, embed-ssl.wistia.com, embed-cloudfront.wistia.com, plus distillery/pipedream stats for connect) with `blob:` media and workers. Optional Sentry/Litix telemetry is not allowed and may be blocked without affecting playback. Local `vsl-player.js`, `vsl-kit.css` and `style.css` are referenced with `?v=wistia3` because `/assets` is cached for 24 hours.
- Build copies `vsl.html` and six files from `assets/vsl/`. Tests: `tests/test_vsl.py` (route/embed/CSP) and `tests/test_vsl_player.py` (unlock behaviour against the labelled double in `tests/vsl_double.mjs`; real Wistia playback was verified by the parent in a real browser, not by these tests).
