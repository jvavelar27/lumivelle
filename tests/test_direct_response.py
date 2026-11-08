"""Tests for preserved direct-response architecture and honest session timer."""
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))

class DirectResponseStructure(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.tags = Tags()
        self.tags.feed(self.html)
    def test_campaign_and_social_proof_precede_hero(self):
        ids = [a.get('id') for _, a in self.tags.items if a.get('id')]
        for name in ['campaign-banner', 'rating-strip', 'top']:
            self.assertIn(name, ids)
        self.assertLess(ids.index('campaign-banner'), ids.index('rating-strip'))
        self.assertLess(ids.index('rating-strip'), ids.index('top'))
        self.assertIn('SESSION TIMER', self.html)
        self.assertIn('17,012+', self.html)
        self.assertIn('4.8', self.html)
        self.assertIn('Advertiser-provided', self.html)
    def test_persuasive_sequence_matches_base_functions(self):
        roles = [a['data-dr-role'] for _, a in self.tags.items if 'data-dr-role' in a]
        expected = ['campaign', 'proof-strip', 'hero', 'early-proof', 'trust-strip', 'story', 'mechanism', 'born', 'ingredients', 'steps', 'mid-cta', 'ritual', 'decision-cta', 'qualifier', 'comparison', 'expectation', 'offer', 'guarantee', 'trust-recap', 'reviews', 'faq', 'final-cta']
        positions = []
        for role in expected:
            self.assertIn(role, roles, f'Missing DR function: {role}')
            positions.append(roles.index(role))
        self.assertEqual(positions, sorted(positions), 'Do not replace the sales sequence with an informational brochure')
    def test_review_figures_are_attributed_not_independently_verified(self):
        self.assertGreaterEqual(self.html.count('Advertiser-provided'), 2)
        self.assertNotIn('Trustpilot', self.html)
        self.assertNotIn('Verified Buyer', self.html)
    def test_banner_small_text_contrast(self):
        match = re.search(r'\.campaign\{background:#([0-9A-Fa-f]{6});color:#fff', self.html)
        self.assertIsNotNone(match)
        c = match.group(1)
        rgb = [int(c[i:i+2], 16) / 255 for i in (0, 2, 4)]
        linear = [x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4 for x in rgb]
        luminance = sum(a*b for a,b in zip(linear, [0.2126, 0.7152, 0.0722]))
        self.assertGreaterEqual(1.05 / (luminance + 0.05), 4.5)
    def test_session_timer_is_not_presented_as_real_offer_expiry(self):
        self.assertTrue((ROOT / 'campaign.js').exists(), 'Session timer module must exist')
        self.assertIn('campaign.js', self.html)
        banner = self.html[self.html.find('id="campaign-banner"'):self.html.find('id="rating-strip"')]
        for unsupported in ['offer expires', 'sale ends', 'stock reserved', '70% OFF']:
            self.assertNotIn(unsupported.lower(), banner.lower())

class SessionTimerBehavior(unittest.TestCase):
    def run_node(self, body):
        self.assertTrue((ROOT / 'campaign.js').exists(), 'Session timer is not implemented yet')
        source = "import {getSessionStart, getRemainingSeconds, formatCountdown} from './campaign.js';\n" + body
        result = subprocess.run(['node', '--input-type=module', '-e', source], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)
    def test_timer_counts_from_entry_and_refresh_does_not_reset(self):
        got = self.run_node("""
const data=new Map(); const storage={getItem:k=>data.has(k)?data.get(k):null,setItem:(k,v)=>data.set(k,v)};
const start=getSessionStart(storage,100000);
const refreshed=getSessionStart(storage,165000);
console.log(JSON.stringify({start,refreshed,remaining:getRemainingSeconds(start,165000,5400),formatted:formatCountdown(5335)}));
""")
        self.assertEqual(got['start'], 100000)
        self.assertEqual(got['refreshed'], 100000)
        self.assertEqual(got['remaining'], 5335)
        self.assertEqual(got['formatted'], {'hours': '01', 'minutes': '28', 'seconds': '55'})
    def test_expired_timer_does_not_artificially_restart(self):
        got = self.run_node("""
const data=new Map(); const storage={getItem:k=>data.has(k)?data.get(k):null,setItem:(k,v)=>data.set(k,v)};
const start=getSessionStart(storage,100000);
const later=getSessionStart(storage,10000000);
console.log(JSON.stringify({start,later,remaining:getRemainingSeconds(start,10000000,5400),formatted:formatCountdown(0)}));
""")
        self.assertEqual(got['start'], got['later'])
        self.assertEqual(got['remaining'], 0)
        self.assertEqual(got['formatted'], {'hours': '00', 'minutes': '00', 'seconds': '00'})
    def test_countdown_clamps_negative_elapsed_and_invalid_remaining(self):
        got = self.run_node("console.log(JSON.stringify({left:getRemainingSeconds(200000,100000,5400),negative:formatCountdown(-2),invalid:formatCountdown(NaN)}));")
        self.assertEqual(got['left'], 5400)
        self.assertEqual(got['negative'], {'hours': '00', 'minutes': '00', 'seconds': '00'})
        self.assertEqual(got['invalid'], {'hours': '00', 'minutes': '00', 'seconds': '00'})

if __name__ == '__main__':
    unittest.main()
