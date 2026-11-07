"""Acceptance checks for the LumiVelle adaptation. Run: python -m unittest discover -s tests -v."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = 'https://order.wealthpay.io/qo52qotcz7vr?hid=b2lkPW9mZl82NDcxMDc5JmFpZD1hZmZfMjg3NzUxNCZ1aWQ9YmxfODY3NTQxMQ%3D%3D&affid=aff_2877514'

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

class LandingAcceptance(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'index.html').exists(), 'LumiVelle index.html must exist')
        self.html = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.parser = PageParser()
        self.parser.feed(self.html)
    def test_brand_and_offer(self):
        self.assertRegex(self.html, r'(?i)lumivelle')
        self.assertIn('Advanced Skin Renewal Gummies', self.html)
        self.assertEqual(sum(tag == 'h1' for tag, _ in self.parser.tags), 1)
        for old in ['sonnus', 'slimsoda', 'usesonnus', '3 a.m.', 'GLP-1', 'videos-lp', 'buyCount', 'stockFill', 'data-cf-beacon']:
            self.assertNotIn(old.lower(), self.html.lower())
    def test_exact_purchase_destination(self):
        outbound = [a for tag, a in self.parser.tags if tag == 'a' and 'order.wealthpay.io' in a.get('href', '')]
        self.assertGreaterEqual(len(outbound), 3)
        for a in outbound:
            self.assertEqual(a['href'], CHECKOUT)
            self.assertIn('sponsored', a.get('rel', ''))
    def test_internal_links(self):
        ids = [a['id'] for _, a in self.parser.tags if 'id' in a]
        self.assertEqual(len(ids), len(set(ids)), 'IDs must be unique')
        for tag, a in self.parser.tags:
            href = a.get('href', '')
            if tag == 'a' and href.startswith('#'):
                self.assertIn(href[1:], ids, f'Broken anchor: {href}')
    def test_images_optimized_and_present(self):
        imgs = [a for tag, a in self.parser.tags if tag == 'img']
        self.assertGreaterEqual(len(imgs), 4)
        for a in imgs:
            src = a.get('src', '')
            self.assertFalse(src.startswith(('data:', 'http')), 'Use local optimized images')
            self.assertTrue(src.endswith('.webp'), f'Not WebP: {src}')
            self.assertTrue((ROOT / src).is_file(), f'Missing image: {src}')
            self.assertIn('alt', a)
            self.assertIn('width', a)
            self.assertIn('height', a)
        self.assertNotIn('data:image', self.html)
    def test_core_layout_is_adapted_not_replaced(self):
        for cls in ['herolp', 'hl-top', 'hl-bottom', 'born-cols', 'ing-grid', 'steps-grid', 'offer-wrap', 'qa']:
            self.assertIn(cls, self.html)
    def test_customer_information_and_disclosures(self):
        for term in ['60', 'support@uselumivelle.com', 'Dietary', 'Food and Drug Administration', 'affiliate']:
            self.assertIn(term.lower(), self.html.lower())
        self.assertGreaterEqual(sum(tag == 'details' for tag, _ in self.parser.tags), 6)
        self.assertIn('prefers-reduced-motion', self.html)
        self.assertIn(':focus-visible', self.html)
    def test_subscription_disclosure(self):
        for term in ['subscription', '28 days', 'Wellness Club', 'cancel']:
            self.assertIn(term.lower(), self.html.lower())
    def test_no_fabricated_proof_or_guaranteed_timeline(self):
        for claim in ['verified buyer', '12,000+', 'clinically proven', 'fda-approved', '96% sold', '70% off', '90-day', 'nine days', 'no side effects']:
            self.assertNotIn(claim, self.html.lower())

if __name__ == '__main__':
    unittest.main()
