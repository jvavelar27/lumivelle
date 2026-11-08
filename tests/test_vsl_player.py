"""Behaviour of assets/vsl/vsl-player.js against a clearly-labelled test double
(tests/vsl_double.mjs) for the <wistia-player> component. Real Wistia playback
is verified separately in a browser; nothing here claims it."""
from pathlib import Path
import json
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
KEY = 'lumivelle-vsl-unlock:dr4rq15xr1:2834'

def run(body):
    source = "import {loadPage, flush, CHECKOUT} from './tests/vsl_double.mjs';\n" + body
    result = subprocess.run(['node', '--input-type=module', '-e', source], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

class MarkupAndCaching(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / 'vsl.html').read_text(encoding='utf-8')
        self.js = (ROOT / 'assets/vsl/vsl-player.js').read_text(encoding='utf-8')
    def test_unlock_point_is_exactly_2834_seconds_and_no_shortcuts(self):
        self.assertIn('data-vdelay="2834"', self.html)
        self.assertIn('data-video-id="dr4rq15xr1"', self.html)
        for text in (self.html, self.js):
            self.assertNotIn('2847', text)
        self.assertNotIn('test=true', self.js)
        self.assertNotIn('"test"', self.js)
        self.assertNotIn('Vimeo', self.js)
        self.assertNotIn('_wq', self.js)
    def test_player_hides_timeline_but_keeps_pause_and_sound(self):
        tag = re.search(r'<wistia-player\b(.*?)>', self.html, re.S).group(1)
        self.assertIn('play-bar-control="false"', tag)
        self.assertIn('play-pause-control="true"', tag)
        self.assertIn('volume-control="true"', tag)
        self.assertIn('silent-autoplay="allow"', tag)
        self.assertIn('playback-rate-control="false"', tag)
        self.assertNotIn('settings-control="false"', tag)
        self.assertNotRegex(tag, r'seo|branding|logo')
    def test_local_player_assets_are_versioned_so_cached_adapters_cannot_break_the_cta(self):
        refs = re.findall(r'(?:src|href)="(/assets/vsl/(?:vsl-player\.js|vsl-kit\.css|style\.css)[^"]*)"', self.html)
        self.assertEqual(len(refs), 3)
        for ref in refs:
            self.assertRegex(ref, r'\?v=wistia')
    def test_no_double_height_on_undefined_player(self):
        css = (ROOT / 'assets/vsl/vsl-kit.css').read_text(encoding='utf-8') + (ROOT / 'assets/vsl/style.css').read_text(encoding='utf-8')
        self.assertNotIn('540 / 666', css)
        self.assertNotRegex(css, r'wistia-player[^{]*\{[^}]*aspect-ratio')
        self.assertIn('0.8126410835214447', css)
    def test_csp_has_no_vimeo_and_no_blanket_allowlist(self):
        config = json.loads((ROOT / 'vercel.json').read_text(encoding='utf-8'))
        csp = next(h['value'] for r in config['headers'] if r['source'] == '/(.*)' for h in r['headers'] if h['key'] == 'Content-Security-Policy')
        self.assertNotIn('vimeo', csp.lower())
        self.assertNotRegex(csp, r"(?<![\w-])\*(?![\w.])")
        directives = {p.strip().split()[0]: p.strip().split()[1:] for p in csp.split(';') if p.strip()}
        for name in ['base-uri', 'form-action', 'frame-ancestors']:
            self.assertIn(name, directives)
        self.assertIn('blob:', directives['media-src'])
        self.assertIn('https://fast.wistia.com', directives['img-src'])
        self.assertIn('https://fast.wistia.com', directives['connect-src'])
    def test_no_js_notice_explains_javascript_is_needed(self):
        self.assertIn('<noscript>', self.html)
        self.assertIn('JavaScript is required', self.html)

class UnlockAtPlaybackSecond(unittest.TestCase):
    def test_stays_hidden_until_current_time_reaches_2834(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush();
const before=p.revealed();
p.at(2833.99); await flush(); const justBefore=p.revealed();
p.at(2834); await flush();
console.log(JSON.stringify({error:p.error,before,justBefore,after:p.revealed(),notice:p.notice.textContent}));
""")
        self.assertIsNone(got['error'])
        self.assertFalse(got['before'])
        self.assertFalse(got['justBefore'])
        self.assertTrue(got['after'])
        self.assertIn('order option', got['notice'])
    def test_seeking_past_the_point_unlocks_but_seeking_before_it_does_not(self):
        got = run("""
const a=loadPage({alreadyReady:true}); await flush(); a.at(2000,'seeked'); await flush();
const b=loadPage({alreadyReady:true}); await flush(); b.at(2900,'seeked'); await flush();
console.log(JSON.stringify({early:a.revealed(),late:b.revealed()}));
""")
        self.assertFalse(got['early'])
        self.assertTrue(got['late'])
    def test_wall_clock_pause_and_play_events_never_unlock(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush();
p.at(10,'play'); p.at(12,'pause'); p.player.paused=true; await flush();
p.advance(10*3600*1000); await flush();
console.log(JSON.stringify({revealed:p.revealed()}));
""")
        self.assertFalse(got['revealed'])
    def test_no_debug_query_shortcut(self):
        got = run("const p=loadPage({alreadyReady:true,search:'?test=true&debug=1&t=3000'}); await flush(); p.advance(1e8); await flush(); console.log(JSON.stringify({r:p.revealed()}));")
        self.assertFalse(got['r'])
    def test_already_ready_player_resumes_from_current_time(self):
        got = run("""
const a=loadPage({alreadyReady:true,startTime:2900}); await flush();
const b=loadPage({alreadyReady:true,startTime:12}); await flush();
console.log(JSON.stringify({resumed:a.revealed(),fresh:b.revealed()}));
""")
        self.assertTrue(got['resumed'])
        self.assertFalse(got['fresh'])
    def test_api_ready_event_resumes_and_late_component_definition_is_awaited(self):
        got = run("""
const a=loadPage(); await flush(); a.player.makeReady(2950); a.player.emit('api-ready'); await flush();
const b=loadPage({defined:'late'}); await flush(); const beforeDefine=b.revealed();
b.player.makeReady(2950); b.define(); await flush(); await flush();
console.log(JSON.stringify({viaApiReady:a.revealed(),beforeDefine,afterDefine:b.revealed()}));
""")
        self.assertTrue(got['viaApiReady'])
        self.assertFalse(got['beforeDefine'])
        self.assertTrue(got['afterDefine'])
    def test_listeners_are_attached_before_the_component_is_defined(self):
        got = run("""
const p=loadPage({defined:'never'}); await flush();
console.log(JSON.stringify({n:['api-ready','time-update','seeked','play','volume-change'].map((t)=>(p.player.listeners[t]||[]).length)}));
""")
        self.assertTrue(all(n >= 1 for n in got['n']), got)

class MalformedAndForeign(unittest.TestCase):
    def test_nonnumeric_current_time_does_not_unlock(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush();
for (const bad of [null,undefined,'2900',NaN,Infinity,-5,true,{},[2900]]) { p.player.currentTime=bad; p.player.emit('time-update'); p.player.emit('seeked'); }
await flush();
console.log(JSON.stringify({revealed:p.revealed()}));
""")
        self.assertFalse(got['revealed'])
    def test_event_detail_is_never_trusted_over_current_time(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush();
p.player.currentTime=10;
p.player.emit('time-update',{seconds:9999,currentTime:9999}); p.player.emit('seeked',{seconds:9999});
await flush();
console.log(JSON.stringify({revealed:p.revealed()}));
""")
        self.assertFalse(got['revealed'])
    def test_no_window_message_listener_so_foreign_frames_cannot_unlock(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush();
const handlers=p.win.listeners.message||[];
for (const f of handlers) f({origin:'https://evil.example',data:{event:'time-update',currentTime:9999}});
console.log(JSON.stringify({listeners:handlers.length,revealed:p.revealed()}));
""")
        self.assertEqual(got['listeners'], 0)
        self.assertFalse(got['revealed'])

class SessionPersistence(unittest.TestCase):
    def test_reveal_persists_with_wistia_id_and_old_or_other_state_cannot_open_it(self):
        got = run("""
const store=new Map();
const a=loadPage({store,alreadyReady:true}); await flush(); a.at(2840); await flush();
const keys=[...store.keys()];
const same=loadPage({store,alreadyReady:true}); await flush();
const vimeo=loadPage({store:new Map([['lumivelle-vsl-unlock:1244806219:2834','1']]),alreadyReady:true}); await flush();
const other=loadPage({store:new Map([['lumivelle-vsl-unlock:dr4rq15xr1:2847','1']]),alreadyReady:true}); await flush();
console.log(JSON.stringify({keys,same:same.revealed(),vimeo:vimeo.revealed(),other:other.revealed()}));
""")
        self.assertEqual(got['keys'], [KEY])
        self.assertTrue(got['same'])
        self.assertFalse(got['vimeo'])
        self.assertFalse(got['other'])
    def test_denied_storage_does_not_break_the_unlock(self):
        got = run("""
const p=loadPage({storage:'denied',alreadyReady:true}); await flush();
p.at(100); await flush(); const early=p.revealed();
p.at(2834); await flush();
console.log(JSON.stringify({error:p.error,early,after:p.revealed()}));
""")
        self.assertIsNone(got['error'])
        self.assertFalse(got['early'])
        self.assertTrue(got['after'])

class PlayerFailure(unittest.TestCase):
    def failure(self, opts, advance='p.advance(30000);'):
        return run(f"""
const p=loadPage({opts}); await flush(); await flush(); {advance} await flush();
console.log(JSON.stringify({{error:p.error,revealed:p.revealed(),hidden:p.status.hidden,text:p.status.textContent,html:p.status.innerHTML}}));
""")
    def assert_clear_failure(self, got):
        self.assertIsNone(got['error'])
        self.assertFalse(got['revealed'])
        self.assertFalse(got['hidden'])
        self.assertIn('reload', (got['text'] + got['html']).lower())
    def test_component_never_defined_times_out_to_status_without_unlocking(self):
        self.assert_clear_failure(self.failure("{defined:'never'}"))
    def test_definition_failure_shows_status(self):
        self.assert_clear_failure(self.failure("{defined:'reject'}", ''))
    def test_browser_without_custom_elements_shows_status(self):
        self.assert_clear_failure(self.failure("{defined:'missing'}", ''))
    def test_missing_player_element_shows_status(self):
        self.assert_clear_failure(self.failure('{noPlayer:true}', ''))
    def test_defined_but_never_ready_times_out(self):
        self.assert_clear_failure(self.failure("{defined:'resolve'}"))
    def test_ready_after_a_timeout_clears_the_status(self):
        got = run("""
const p=loadPage({defined:'resolve'}); await flush(); p.advance(30000); const shown=!p.status.hidden;
p.player.makeReady(5); p.player.emit('api-ready'); await flush();
console.log(JSON.stringify({shown,hiddenAfter:p.status.hidden,revealed:p.revealed()}));
""")
        self.assertTrue(got['shown'])
        self.assertTrue(got['hiddenAfter'])
        self.assertFalse(got['revealed'])

class StageAndTracking(unittest.TestCase):
    def test_stage_only_when_sound_is_really_on_and_escape_exits(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush();
p.player.emit('play'); await flush(); const mutedPlay=p.body.classList.contains('is-stage');
p.player.muted=false; p.player.volume=0; p.player.emit('volume-change'); await flush(); const zero=p.body.classList.contains('is-stage');
p.player.muted='no'; p.player.volume=1; p.player.emit('volume-change'); await flush(); const odd=p.body.classList.contains('is-stage');
p.player.muted=false; p.player.emit('volume-change'); await flush(); const on=p.body.classList.contains('is-stage'), stripped=p.body.classList.contains('is-stripped');
for (const f of p.docListeners.keydown||[]) f({key:'Escape'});
console.log(JSON.stringify({mutedPlay,zero,odd,on,stripped,afterEsc:p.body.classList.contains('is-stage'),stillStripped:p.body.classList.contains('is-stripped')}));
""")
        self.assertFalse(got['mutedPlay'])
        self.assertFalse(got['zero'])
        self.assertFalse(got['odd'])
        self.assertTrue(got['on'])
        self.assertTrue(got['stripped'])
        self.assertFalse(got['afterEsc'])
        self.assertTrue(got['stillStripped'])
    def test_reveal_leaves_stage_and_marks_page_revealed(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush(); p.player.muted=false; p.player.emit('volume-change'); await flush();
p.at(2834); await flush();
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
