"""User-visible start flow: no silent autoplay, explicit accessible sound action."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
class Tags(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags=[]
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

class ManualSoundStart(unittest.TestCase):
    def test_video_waits_for_a_visible_sound_start_action(self):
        html=(ROOT/'vsl.html').read_text(encoding='utf-8')
        parsed=Tags(); parsed.feed(html)
        player=next(a for t,a in parsed.tags if t=='wistia-player')
        self.assertEqual(player.get('autoplay'),'false','Do not start the VSL silently before a visitor acts')
        self.assertEqual(player.get('muted'),'false')
        self.assertEqual(player.get('silent-autoplay'),'false')
        self.assertEqual(player.get('play-bar-control'),'false')
        button=next((a for t,a in parsed.tags if t=='button' and a.get('id')=='start-video'),None)
        self.assertIsNotNone(button,'A prominent real button must start video with sound; not an API-only unmute')
        self.assertEqual(button.get('type'),'button')
        self.assertEqual(button.get('aria-label'),'Play video with sound')
        self.assertIn('Play video with sound',html)
        self.assertIn('data-vdelay="2834"',html)

if __name__=='__main__':unittest.main()
