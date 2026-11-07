# LumiVelle landing page (static)

Static landing page: `index.html` (inline CSS/JS, no frontend framework or package dependencies). Adapted from the `lp1-GLP-1.html` source layout (`.herolp`, `.born-cols`, `.ing-grid`, `.steps-grid`, `.offer-wrap`, `details.qa`).

## Run locally
    python -m http.server 8000     # then open http://localhost:8000

## Test
    python -m unittest discover -s tests -v

## Deploy (Vercel, static)
Import `jvavelar27/lumivelle`, framework Other. `vercel.json` sets `node scripts/build.mjs` as build command and `dist` as output directory, plus security headers and asset caching.
`npm run build` copies only HTML, favicon and optimized assets into `dist/`; tests, source notes and documentation are not published.

## Files
- `assets/` — optimized `.webp` images (product, hero, kit-2, kit-3). Product art must match the supplied label (`Affiliate Brief/images/cap-1-img1.png`, kept out of this repo).
- `privacy.html`, `terms.html` — short affiliate-page notices; checkout terms belong to the merchant.
- Original offer HTML variants, videos and outdated instructions were removed after adaptation. The user's brief remains outside the repository.
- All raster assets are WebP. Two contextual images were generated with text-to-image-free; captions distinguish illustration from customers/results. Provider watermarks retained.
- Browser QA passed at 320, 375, 390, 768, 1024, 1440 and 812px landscape, including gallery, keyboard FAQ and JavaScript-disabled content.

## Known source limitations
- No exact ingredient amounts, serving size or Supplement Facts available; page avoids dosing, duration and results claims.
- Checkout shows conflicting prices ($79/$89/$99 per bottle vs $99 total for 3 bottles), so no prices, savings or durations are displayed.
- Verified from merchant modals: package renews every 28 days until canceled; optional Wellness Club is separate; refund requests do not cancel renewals. Page discloses this near the CTA and in the FAQ without repeating merchant dates or prices. Optional extras (money-back protection, express shipping) are default-on at checkout; the page tells buyers to review them. Terms/refund pages are modals on the merchant site, not linkable.
- Guarantee is described only as "60-day money-back guarantee, subject to the merchant's refund policy".
- Google Fonts is the only remote resource (typefaces); CSP in `vercel.json` allows it.
- No reviews, ratings, customer counts, urgency or testimonials are used because none are verified.
