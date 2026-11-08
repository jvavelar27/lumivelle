# Direct-response structure (do not remove)

The original base page was a direct-response sequence, not an informational brochure. `tests/test_direct_response.py` enforces this order through `data-dr-role` attributes in `index.html`. Each section must keep advancing conviction or the next action.

| # | `data-dr-role` | Original function | LumiVelle section |
|---|---|---|---|
| 1 | `campaign` (`#campaign-banner`) | Offer/urgency topbar + visitor-session timer from the user's screenshot | LUMIVELLE OFFER band, checkout link, SESSION TIMER |
| 2 | `proof-strip` (`#rating-strip`) | Star rating before the hero | Five stars, Excellent, Rated 4.8 · 17,012+ Reviews, linked to `#reviews` |
| 3 | `hero` (`#top`) | Promise + first CTA | `.herolp` hero |
| 4 | `early-proof` | Early proof cards (`.results`) | Label-checkable facts (four roles, chewable, 30 per bottle, 60-day policy), no testimonials |
| 5 | `trust-strip` | Credibility strip | Pack facts + merchant 60-day policy; no media logos or certifications |
| 6 | `story` | Emotional problem story | Second-person scene, routines that keep growing, inside-out reframe |
| 7 | `mechanism` | Problem/solution mechanism developed inside the original `.story` | "Korean Pink Gelatin" curiosity section |
| 8 | `born` | Product reveal | "Meet LumiVelle" |
| 9 | `ingredients` | Ingredient mechanism (`.ing`) | Four-part ingredient map |
| 10 | `steps` | 4 steps | Collagen Reset in four steps |
| 11 | `mid-cta` | CTA after the mechanism | "Ready to try the inside-out step?" |
| 12 | `ritual` | Lived daily experience (`.day`) | Daily ritual, label-directed dosing only |
| 13 | `decision-cta` | Urgency CTA | Decision prompt; no stock counts or batches |
| 14 | `qualifier` | Who it is for (`.whosec`) | Suits you / check first |
| 15 | `comparison` | Comparison table | Topical vs oral support |
| 16 | `expectation` | Expectation timeline (`.expect`) | Experience guide, not a results timeline |
| 17 | `offer` | Package offer + decision helpers | Gallery, 1/2/3 bottles, helpers, subscription disclosure |
| 18 | `guarantee` | Guarantee + CTA | Actual 60-day merchant window + CTA |
| 19 | `trust-recap` | Trust recap (`.sproof`) | Formula/format/policy recap |
| 20 | `reviews` (`#reviews`) | Review module (`.rvw`) | Aggregate 4.8 / 17,012+ with source note, no individual reviews |
| 21 | `faq` | FAQs + CTA | FAQ accordion + CTA |
| 22 | `final-cta` | Final CTA | Closing CTA, then footer disclosures |

## Provenance and semantics
- **Rating figures (4.8, 17,012+ reviews):** supplied and authorized by the user from their own screenshot. They are advertiser-provided and not independently verified. The page says so in the rating strip and in the review module. No third-party platform affiliation, badge, "verified buyer" label, individual quote or histogram may be added.
- **Session timer:** counts down 5400 seconds (90 minutes) from the visitor's first page load in the browser tab session (`sessionStorage` key `lumivelle-session-start`). It is not a calendar date. Refresh does not reset it, and at zero it stays at 00:00:00 and does not loop. It must never imply that pricing, stock or the merchant offer expires. The timer row is visible by default, independent of the unrelated inline `html.js` bootstrap. Without JavaScript it stays visible with an explicit enable-JavaScript message, and the purchase link still works. Logic lives in `campaign.js` and is tested in Node.
- **Separation of claims:** the campaign scaffolding (banner, timer, CTAs, rating strip) is persuasion structure. Factual product claims stay limited to what the brief supports (see README "Known source limitations").
