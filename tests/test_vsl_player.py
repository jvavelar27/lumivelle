"""Behaviour of assets/vsl/vsl-player.js against a clearly-labelled test double
(tests/vsl_double.mjs). Real Vimeo behaviour is verified separately in a browser."""
from pathlib import Path
import json
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
KEY = 'lumivelle-vsl-unlock:1244806219:2834'

def run(body):
    source = "import {loadPage, flush, CHECKOUT} from './tests/vsl_double.mjs';\n" + body
    result = subprocess.run(['node', '--input-type=module', '-e', source], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

class UnlockAtPlaybackSecond(unittest.TestCase):
    def test_unlock_point_is_exactly_2834_seconds_in_markup_and_script(self):
        html = (ROOT / 'vsl.html').read_text(encoding='utf-8')
        self.assertIn('data-vdelay="2834"', html)
        self.assertNotIn('2847', html)
        js = (ROOT / 'assets/vsl/vsl-player.js').read_text(encoding='utf-8')
        self.assertNotIn('2847', js)
        self.assertNotIn('test=true', js)
        self.assertNotIn('"test"', js)
    def test_binds_the_page_iframe_and_stays_hidden_until_playback_reaches_2834(self):
        got = run("""
const p=loadPage(); await flush();
const before=p.revealed();
p.player.emit('timeupdate',{seconds:2833.99,percent:.9,duration:3000}); await flush();
const justBefore=p.revealed();
p.player.emit('timeupdate',{seconds:2834,percent:.95,duration:3000}); await flush();
console.log(JSON.stringify({error:p.error,bound:p.player.el===p.iframe,before,justBefore,after:p.revealed(),notice:p.notice.textContent}));
""")
        self.assertIsNone(got['error'])
        self.assertTrue(got['bound'])
        self.assertFalse(got['before'])
        self.assertFalse(got['justBefore'])
        self.assertTrue(got['after'])
        self.assertIn('order option', got['notice'])
    def test_seeking_past_the_point_unlocks_but_seeking_to_before_it_does_not(self):
        got = run("""
const a=loadPage(); await flush(); a.player.emit('seeked',{seconds:2000}); await flush();
const b=loadPage(); await flush(); b.player.emit('seeked',{seconds:2900}); await flush();
console.log(JSON.stringify({early:a.revealed(),late:b.revealed()}));
""")
        self.assertFalse(got['early'])
        self.assertTrue(got['late'])
    def test_wall_clock_and_pause_never_unlock(self):
        got = run("""
const p=loadPage(); await flush();
p.player.emit('play',{seconds:10}); p.player.emit('pause',{seconds:12}); await flush();
p.advance(10*3600*1000); await flush();
console.log(JSON.stringify({revealed:p.revealed()}));
""")
        self.assertFalse(got['revealed'])
    def test_no_test_mode_query_shortcut(self):
        got = run("const p=loadPage({search:'?test=true&debug=1'}); await flush(); p.advance(1e8); await flush(); console.log(JSON.stringify({r:p.revealed()}));")
        self.assertFalse(got['r'])
    def test_resume_unlocks_from_current_time_after_ready(self):
        got = run("""
const p=loadPage({startTime:2900}); await flush(); await flush();
const q=loadPage({startTime:12}); await flush(); await flush();
console.log(JSON.stringify({resumed:p.revealed(),fresh:q.revealed()}));
""")
        self.assertTrue(got['resumed'])
        self.assertFalse(got['fresh'])

class MalformedAndForeign(unittest.TestCase):
    def test_malformed_payloads_do_not_unlock(self):
        got = run("""
const p=loadPage(); await flush();
for (const bad of [null,undefined,{},[],'2900',2900,{seconds:'2900'},{seconds:NaN},{seconds:Infinity},{seconds:-5},{seconds:null},{percent:1},{seconds:true}]) {
  p.player.emit('timeupdate',bad); p.player.emit('seeked',bad);
}
await flush();
console.log(JSON.stringify({revealed:p.revealed()}));
""")
        self.assertFalse(got['revealed'])
    def test_no_window_message_listener_so_foreign_frames_cannot_unlock(self):
        got = run("""
const p=loadPage(); await flush();
const handlers=p.win.listeners.message||[];
for (const f of handlers) f({origin:'https://evil.example',data:{event:'timeupdate',data:{seconds:9999}}});
console.log(JSON.stringify({listeners:handlers.length,revealed:p.revealed()}));
""")
        self.assertEqual(got['listeners'], 0)
        self.assertFalse(got['revealed'])

class SessionPersistence(unittest.TestCase):
    def test_reveal_persists_for_same_session_and_not_other_video_or_threshold(self):
        got = run("""
const store=new Map();
const a=loadPage({store}); await flush(); a.player.emit('timeupdate',{seconds:2840}); await flush();
const keys=[...store.keys()];
const same=loadPage({store}); await flush();
const other=loadPage({store:new Map([['lumivelle-vsl-unlock:1244806219:2847','1']])}); await flush();
console.log(JSON.stringify({keys,sameRevealedAtLoad:same.revealed(),otherRevealed:other.revealed()}));
""")
        self.assertEqual(got['keys'], [KEY])
        self.assertTrue(got['sameRevealedAtLoad'])
        self.assertFalse(got['otherRevealed'])
    def test_denied_storage_does_not_break_the_unlock(self):
        got = run("""
const p=loadPage({storage:'denied'}); await flush();
p.player.emit('timeupdate',{seconds:100}); await flush(); const early=p.revealed();
p.player.emit('timeupdate',{seconds:2834}); await flush();
console.log(JSON.stringify({error:p.error,early,after:p.revealed()}));
""")
        self.assertIsNone(got['error'])
        self.assertFalse(got['early'])
        self.assertTrue(got['after'])

class PlayerFailureAndNoJs(unittest.TestCase):
    def failure(self, opts, advance=''):
        return run(f"""
const p=loadPage({opts}); await flush(); await flush(); {advance} await flush();
console.log(JSON.stringify({{error:p.error,revealed:p.revealed(),hidden:p.status.hidden,text:p.status.textContent,html:p.status.innerHTML}}));
""")
    def assert_clear_failure(self, got):
        self.assertIsNone(got['error'])
        self.assertFalse(got['revealed'])
        self.assertFalse(got['hidden'])
        self.assertIn('reload', (got['text'] + got['html']).lower())
    def test_missing_sdk_shows_status_and_never_reveals(self):
        self.assert_clear_failure(self.failure('{vimeo:false}'))
    def test_player_creation_failure_shows_status(self):
        self.assert_clear_failure(self.failure('{throwOnCreate:true}'))
    def test_ready_rejection_shows_status(self):
        self.assert_clear_failure(self.failure("{readyMode:'reject'}"))
    def test_player_that_never_becomes_ready_times_out_to_status(self):
        self.assert_clear_failure(self.failure("{readyMode:'never'}", 'p.advance(30000);'))
    def test_no_js_notice_explains_javascript_is_needed(self):
        html = (ROOT / 'vsl.html').read_text(encoding='utf-8')
        self.assertIn('<noscript>', html)
        self.assertIn('JavaScript is required', html)

class StageAndTracking(unittest.TestCase):
    def test_stage_only_when_sound_is_really_on_and_escape_exits(self):
        got = run("""
const p=loadPage(); await flush();
p.player.emit('play',{seconds:1}); await flush(); const mutedPlay=p.body.classList.contains('is-stage');
p.player.muted=false; p.player.volume=0; p.player.emit('volumechange',{volume:0}); await flush(); const zero=p.body.classList.contains('is-stage');
p.player.volume=1; p.player.emit('volumechange',{volume:1}); await flush(); const on=p.body.classList.contains('is-stage'), stripped=p.body.classList.contains('is-stripped');
for (const f of p.docListeners.keydown||[]) f({key:'Escape'});
console.log(JSON.stringify({mutedPlay,zero,on,stripped,afterEsc:p.body.classList.contains('is-stage'),stillStripped:p.body.classList.contains('is-stripped')}));
""")
        self.assertFalse(got['mutedPlay'])
        self.assertFalse(got['zero'])
        self.assertTrue(got['on'])
        self.assertTrue(got['stripped'])
        self.assertFalse(got['afterEsc'])
        self.assertTrue(got['stillStripped'])
    def test_reveal_leaves_stage_and_marks_page_revealed(self):
        got = run("""
const p=loadPage(); await flush(); p.player.muted=false; p.player.emit('volumechange',{volume:1}); await flush();
p.player.emit('timeupdate',{seconds:2834}); await flush();
console.log(JSON.stringify({stage:p.body.classList.contains('is-stage'),revealed:p.body.classList.contains('is-revealed')}));
""")
        self.assertFalse(got['stage'])
        self.assertTrue(got['revealed'])
    def test_tracking_params_never_override_hid_affid_or_add_debug(self):
        got = run("""
const p=loadPage({search:'?utm_source=fb&utm_campaign=x&hid=EVIL&affid=EVIL&sub1=abc&test=true&debug=1&foo=bar'}); await flush();
console.log(JSON.stringify({href:p.buy.href,base:CHECKOUT}));
""")
        self.assertTrue(got['href'].startswith(got['base'] + '&'))
        self.assertIn('utm_source=fb', got['href'])
        self.assertIn('sub1=abc', got['href'])
        for bad in ['EVIL', 'test=', 'debug', 'foo=']:
            self.assertNotIn(bad, got['href'])
        self.assertEqual(got['href'].count('hid='), 1)
    def test_checkout_unchanged_without_params(self):
        got = run("const p=loadPage(); await flush(); console.log(JSON.stringify({same:p.buy.href===CHECKOUT}));")
        self.assertTrue(got['same'])

if __name__ == '__main__':
    unittest.main()
