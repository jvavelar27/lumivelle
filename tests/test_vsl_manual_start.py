"""Silent preview, then an explicit restart from zero with sound."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
class Tags(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags=[]
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

class PreviewSoundRestart(unittest.TestCase):
    def test_muted_preview_has_a_visible_restart_with_sound_action(self):
        html=(ROOT/'vsl.html').read_text(encoding='utf-8')
        parsed=Tags(); parsed.feed(html)
        player=next(a for t,a in parsed.tags if t=='wistia-player')
        self.assertEqual(player.get('autoplay'),'true','Run a muted preview before the visitor chooses to hear the VSL')
        self.assertEqual(player.get('muted'),'true')
        self.assertEqual(player.get('silent-autoplay'),'true')
        self.assertEqual(player.get('play-bar-control'),'false')
        button=next((a for t,a in parsed.tags if t=='button' and a.get('id')=='start-video'),None)
        self.assertIsNotNone(button,'A prominent real button must start video with sound; not an API-only unmute')
        self.assertEqual(button.get('type'),'button')
        self.assertEqual(button.get('aria-label'),'Restart video with sound')
        self.assertIn('Click for sound',html)
        self.assertNotIn('video restarts from the beginning',html.lower())
        self.assertNotIn('vsl-start__helper',html)
        self.assertIn('data-vdelay="2834"',html)

if __name__=='__main__':unittest.main()
