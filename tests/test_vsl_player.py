"""Behaviour of assets/vsl/vsl-player.js against a clearly-labelled test double
(tests/vsl_double.mjs) for the <wistia-player> component. Real Wistia playback
is verified separately in a browser; nothing here claims it.

Flow under test: a muted silent PREVIEW autoplays behind an overlay; a trusted
click/tap/Enter restarts from zero with sound (the LISTENING session). Only the
listening session can earn the 2834-second (47:14) checkout reveal."""
from pathlib import Path
import json
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
KEY = 'lumivelle-vsl-listen-unlock:v2:dr4rq15xr1:2834'
LEGACY_KEY = 'lumivelle-vsl-unlock:dr4rq15xr1:2834'
RESTART_ORDER = ['pause', 'silentAutoplay=false', 'currentTime=0', 'muted=false', 'volume=1', 'play']

PRELUDE = """import {loadPage, flush, CHECKOUT} from './tests/vsl_double.mjs';
// start the listening session the way a person does: one trusted click, then let promises settle
const listen = async (p) => { p.click(true); await flush(); await flush(); };
"""

def run(body):
    result = subprocess.run(['node', '--input-type=module', '-e', PRELUDE + body], cwd=ROOT, capture_output=True, text=True)
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
    def test_player_is_a_silent_preview_without_timeline_and_with_pause_and_sound(self):
        tag = re.search(r'<wistia-player\b(.*?)>', self.html, re.S).group(1)
        self.assertIn('autoplay="true"', tag)
        self.assertIn('muted="true"', tag)
        self.assertIn('silent-autoplay="true"', tag)
        self.assertIn('play-bar-control="false"', tag)
        self.assertIn('play-pause-control="true"', tag)
        self.assertIn('volume-control="true"', tag)
        self.assertIn('big-play-button="false"', tag)
        self.assertIn('playback-rate-control="false"', tag)
        self.assertNotIn('settings-control="false"', tag)
        self.assertNotRegex(tag, r'seo|branding|logo')
    def test_local_player_assets_are_versioned_so_cached_adapters_cannot_break_the_cta(self):
        refs = re.findall(r'(?:src|href)="(/assets/vsl/(?:vsl-player\.js|vsl-kit\.css|style\.css)[^"]*)"', self.html)
        self.assertEqual(len(refs), 3)
        for ref in refs:
            self.assertRegex(ref, r'\?v=wistia3')
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
    def test_overlay_markup_inside_video_box_with_accessible_button(self):
        box = self.html[self.html.index('id="video"'):self.html.index('id="player-status"')]
        self.assertIn('id="start-overlay"', box)
        button = re.search(r'<button\b[^>]*id="start-video"[^>]*>(.*?)</button>', box, re.S)
        self.assertIn('type="button"', button.group(0))
        self.assertIn('aria-label="Restart video with sound"', button.group(0))
        self.assertIn('disabled', button.group(0).split('>')[0])
        self.assertEqual(button.group(1).strip(), 'Click for sound')
        self.assertIn('Video restarts from the beginning', box)
        css = (ROOT / 'assets/vsl/style.css').read_text(encoding='utf-8')
        self.assertRegex(css, r'\.vsl-start\[hidden\]\s*\{[^}]*display:\s*none')
        self.assertRegex(css, r'\.vsl-start__button\s*\{[^}]*min-height:\s*(4[4-9]|[5-9]\d)px')
        self.assertIn('.vsl-start__button:focus-visible', css)
        self.assertNotIn(':hover', css[css.index('.vsl-start'):css.index('/* ---- Player status')])

class SilentPreview(unittest.TestCase):
    def test_preview_keeps_playing_muted_and_overlay_stays_visible(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush();
p.player.paused=false; p.player.emit('play'); p.at(5); p.at(6); p.player.emit('volume-change'); await flush();
console.log(JSON.stringify({log:p.player.log,overlayHidden:p.startOverlay.hidden,stage:p.body.classList.contains('is-stage'),enabled:!p.startButton.disabled}));
""")
        self.assertEqual(got['log'], [], 'the page must not pause, seek, unmute or play on its own')
        self.assertFalse(got['overlayHidden'])
        self.assertFalse(got['stage'])
        self.assertTrue(got['enabled'])
    def test_preview_past_2834_never_reveals_even_at_load_or_after_native_unmute(self):
        got = run("""
const a=loadPage({alreadyReady:true,startTime:2900}); await flush();
const atLoad=a.revealed();
a.at(2835); a.at(2840,'seeked'); a.player.emit('api-ready'); await flush();
const b=loadPage({alreadyReady:true}); await flush();
b.player._muted=false; b.player.paused=false; b.player.emit('volume-change'); b.at(3000); b.player.emit('play'); await flush();
console.log(JSON.stringify({atLoad,previewAfter:a.revealed(),nativeUnmute:b.revealed(),nativeUnmuteOverlayHidden:b.startOverlay.hidden,store:[...a.store.keys()]}));
""")
        self.assertFalse(got['atLoad'])
        self.assertFalse(got['previewAfter'])
        self.assertFalse(got['nativeUnmute'])
        self.assertFalse(got['nativeUnmuteOverlayHidden'], 'a preview is never treated as the listening session')
        self.assertEqual(got['store'], [])
    def test_nothing_plays_without_a_user_action(self):
        got = run("""
const p=loadPage({defined:'late'}); await flush();
p.player.makeReady(0); p.define(); p.player.emit('api-ready'); await flush(); await flush();
p.advance(10*3600*1000); await flush();
p.player.emit('volume-change'); p.player.emit('time-update'); await flush();
console.log(JSON.stringify({log:p.player.log,overlayHidden:p.startOverlay.hidden}));
""")
        self.assertEqual(got['log'], [])
        self.assertFalse(got['overlayHidden'])
    def test_button_is_disabled_until_the_player_is_ready(self):
        got = run("""
const p=loadPage({defined:'late'}); await flush();
const before=p.startButton.disabled;
p.player.makeReady(0); p.define(); await flush(); await flush();
console.log(JSON.stringify({before,after:p.startButton.disabled,plays:p.player.log.filter((x)=>x==='play').length}));
""")
        self.assertTrue(got['before'])
        self.assertFalse(got['after'])
        self.assertEqual(got['plays'], 0)

class RestartWithSound(unittest.TestCase):
    def test_trusted_click_pauses_resets_unmutes_and_plays_synchronously_in_order(self):
        got = run("""
const p=loadPage({alreadyReady:true,startTime:40}); await flush();
p.player.paused=false;
p.click(true);
const syncLog=[...p.player.log];
await flush(); await flush();
console.log(JSON.stringify({syncLog,hidden:p.startOverlay.hidden,t:p.player.currentTime}));
""")
        self.assertEqual(got['syncLog'], RESTART_ORDER)
        self.assertEqual(got['t'], 0)
        self.assertTrue(got['hidden'])
    def test_keyboard_enter_and_touch_tap_clicks_are_equivalent(self):
        got = run("""
const out={};
for (const [name,extra] of [['mouse',{detail:1}],['keyboard',{detail:0}],['touch',{detail:1,pointerType:'touch'}]]) {
  const p=loadPage({alreadyReady:true}); await flush(); p.click(true,extra); const sync=[...p.player.log]; await flush(); await flush();
  out[name]={sync,hidden:p.startOverlay.hidden};
}
console.log(JSON.stringify(out));
""")
        for name in ('mouse', 'keyboard', 'touch'):
            self.assertEqual(got[name]['sync'], RESTART_ORDER, name)
            self.assertTrue(got[name]['hidden'], name)
    def test_untrusted_or_disabled_clicks_do_nothing(self):
        got = run("""
const a=loadPage({alreadyReady:true}); await flush(); a.click(false);
const b=loadPage({defined:'never'}); await flush(); b.click(true);
console.log(JSON.stringify({untrusted:a.player.log,notReady:b.player.log}));
""")
        self.assertEqual(got['untrusted'], [])
        self.assertEqual(got['notReady'], [])
    def test_autoplay_blocked_still_leaves_a_usable_button(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush(); // paused at 0: the browser blocked the muted preview
const enabled=!p.startButton.disabled; await listen(p);
console.log(JSON.stringify({enabled,hidden:p.startOverlay.hidden,log:p.player.log}));
""")
        self.assertTrue(got['enabled'])
        self.assertTrue(got['hidden'])
        self.assertEqual(got['log'], RESTART_ORDER)
    def test_overlay_hides_only_after_position_is_near_zero_with_real_sound_playing(self):
        got = run("""
const p=loadPage({alreadyReady:true,startTime:2835}); await flush();
p.player.seekMode='stale'; p.player.paused=false;
p.click(true); await flush(); await flush();
const stillOld={hidden:p.startOverlay.hidden,t:p.player.currentTime};
p.player.settleSeek(); p.player.emit('seeked'); await flush();
console.log(JSON.stringify({stillOld,after:p.startOverlay.hidden,t:p.player.currentTime}));
""")
        self.assertFalse(got['stillOld']['hidden'])
        self.assertEqual(got['stillOld']['t'], 2835)
        self.assertTrue(got['after'])
        self.assertEqual(got['t'], 0)
    def test_play_that_resolves_without_sound_playing_keeps_overlay(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush(); p.player.playMode='resolve-silent';
p.click(true); await flush(); await flush();
const stuck={hidden:p.startOverlay.hidden,disabled:p.startButton.disabled};
p.player.paused=false; p.player.emit('play'); p.at(0.3); await flush();
console.log(JSON.stringify({stuck,after:p.startOverlay.hidden}));
""")
        self.assertFalse(got['stuck']['hidden'])
        self.assertFalse(got['stuck']['disabled'])
        self.assertTrue(got['after'])
    def test_rejected_or_thrown_play_keeps_overlay_retries_and_earns_nothing_meanwhile(self):
        got = run("""
const out={};
for (const mode of ['reject','throw']) {
  const p=loadPage({alreadyReady:true,startTime:2900}); await flush(); p.player.playMode=mode;
  p.click(true); await flush();
  p.at(2900); p.at(2950,'seeked');
  const failed={hidden:p.startOverlay.hidden,disabled:p.startButton.disabled,status:!p.status.hidden,text:p.status.textContent+p.status.innerHTML,revealed:p.revealed()};
  p.player.playMode='resolve'; p.click(true); await flush(); await flush();
  out[mode]={failed,retryPlays:p.player.log.filter((x)=>x==='play').length,hiddenAfterRetry:p.startOverlay.hidden};
}
console.log(JSON.stringify(out));
""")
        for mode in ('reject', 'throw'):
            r = got[mode]
            self.assertFalse(r['failed']['hidden'])
            self.assertFalse(r['failed']['disabled'])
            self.assertTrue(r['failed']['status'])
            self.assertIn('try again', r['failed']['text'].lower())
            self.assertFalse(r['failed']['revealed'])
            self.assertEqual(r['retryPlays'], 2)
            self.assertTrue(r['hiddenAfterRetry'])
    def test_repeated_clicks_while_starting_are_ignored(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush(); p.player.playMode='pending';
p.click(true); p.click(true); p.click(true); await flush();
console.log(JSON.stringify({plays:p.player.log.filter((x)=>x==='play').length,pauses:p.player.log.filter((x)=>x==='pause').length,disabled:p.startButton.disabled}));
""")
        self.assertEqual(got['plays'], 1)
        self.assertEqual(got['pauses'], 1)
        self.assertTrue(got['disabled'])
    def test_click_alone_does_not_unlock_the_offer(self):
        got = run("const p=loadPage({alreadyReady:true}); await flush(); await listen(p); console.log(JSON.stringify({r:p.revealed()}));")
        self.assertFalse(got['r'])

class StaleCallbacksDuringRestart(unittest.TestCase):
    def test_old_preview_position_cannot_unlock_while_the_seek_to_zero_is_in_flight(self):
        got = run("""
const p=loadPage({alreadyReady:true,startTime:2835}); await flush();
p.player.seekMode='stale'; p.player.paused=false;
p.click(true); await flush();
// callbacks still carry the preview's old position, now with sound on and playing
p.at(2835); p.at(2836,'seeked'); p.player.emit('play'); await flush();
const during={revealed:p.revealed(),hidden:p.startOverlay.hidden};
p.player.settleSeek(); p.at(0.2); await flush();
const afterSeek={revealed:p.revealed(),hidden:p.startOverlay.hidden};
p.at(2833.99); const before=p.revealed(); p.at(2834); await flush();
console.log(JSON.stringify({during,afterSeek,before,final:p.revealed(),store:[...p.store.keys()]}));
""")
        self.assertFalse(got['during']['revealed'])
        self.assertFalse(got['during']['hidden'])
        self.assertFalse(got['afterSeek']['revealed'])
        self.assertTrue(got['afterSeek']['hidden'])
        self.assertFalse(got['before'])
        self.assertTrue(got['final'])
        self.assertEqual(got['store'], [KEY])

class UnlockAtPlaybackSecond(unittest.TestCase):
    def test_listening_session_unlocks_exactly_at_2834(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush();
const before=p.revealed(); await listen(p);
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
const a=loadPage({alreadyReady:true}); await flush(); await listen(a); a.at(2000,'seeked'); await flush();
const b=loadPage({alreadyReady:true}); await flush(); await listen(b); b.at(2900,'seeked'); await flush();
console.log(JSON.stringify({early:a.revealed(),late:b.revealed()}));
""")
        self.assertFalse(got['early'])
        self.assertTrue(got['late'])
    def test_wall_clock_pause_and_play_events_never_unlock(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush(); await listen(p);
p.at(10,'play'); p.at(12,'pause'); p.player.paused=true; await flush();
p.advance(10*3600*1000); await flush();
console.log(JSON.stringify({revealed:p.revealed()}));
""")
        self.assertFalse(got['revealed'])
    def test_no_debug_query_shortcut(self):
        got = run("const p=loadPage({alreadyReady:true,search:'?test=true&debug=1&t=3000'}); await flush(); await listen(p); p.advance(1e8); await flush(); console.log(JSON.stringify({r:p.revealed()}));")
        self.assertFalse(got['r'])
    def test_api_ready_and_late_definition_enable_the_button_but_never_resume_an_unlock(self):
        got = run("""
const a=loadPage(); await flush(); a.player.makeReady(2950); a.player.emit('api-ready'); await flush();
const b=loadPage({defined:'late'}); await flush(); const beforeDefine={disabled:b.startButton.disabled};
b.player.makeReady(2950); b.define(); await flush(); await flush();
console.log(JSON.stringify({viaApiReady:a.revealed(),aEnabled:!a.startButton.disabled,beforeDefine,afterDefine:b.revealed(),bEnabled:!b.startButton.disabled}));
""")
        self.assertFalse(got['viaApiReady'])
        self.assertTrue(got['aEnabled'])
        self.assertTrue(got['beforeDefine']['disabled'])
        self.assertFalse(got['afterDefine'])
        self.assertTrue(got['bEnabled'])
    def test_listeners_are_attached_before_the_component_is_defined(self):
        got = run("""
const p=loadPage({defined:'never'}); await flush();
console.log(JSON.stringify({n:['api-ready','time-update','seeked','play','volume-change'].map((t)=>(p.player.listeners[t]||[]).length)}));
""")
        self.assertTrue(all(n >= 1 for n in got['n']), got)

class MalformedAndForeign(unittest.TestCase):
    def test_nonnumeric_current_time_does_not_unlock(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush(); await listen(p);
for (const bad of [null,undefined,'2900',NaN,Infinity,-5,true,{},[2900]]) { p.player._t=bad; p.player.emit('time-update'); p.player.emit('seeked'); }
await flush();
console.log(JSON.stringify({revealed:p.revealed()}));
""")
        self.assertFalse(got['revealed'])
    def test_event_detail_is_never_trusted_over_current_time(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush(); await listen(p);
p.player._t=10;
p.player.emit('time-update',{seconds:9999,currentTime:9999}); p.player.emit('seeked',{seconds:9999});
await flush();
console.log(JSON.stringify({revealed:p.revealed()}));
""")
        self.assertFalse(got['revealed'])
    def test_no_window_message_listener_so_foreign_frames_cannot_unlock(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush(); await listen(p);
const handlers=p.win.listeners.message||[];
for (const f of handlers) f({origin:'https://evil.example',data:{event:'time-update',currentTime:9999}});
console.log(JSON.stringify({listeners:handlers.length,revealed:p.revealed()}));
""")
        self.assertEqual(got['listeners'], 0)
        self.assertFalse(got['revealed'])

class SessionPersistence(unittest.TestCase):
    def test_earned_listening_reveal_persists_under_a_versioned_key_and_nothing_else_opens_it(self):
        got = run("""
const store=new Map();
const a=loadPage({store,alreadyReady:true}); await flush(); await listen(a); a.at(2840); await flush();
const keys=[...store.keys()];
const same=loadPage({store,alreadyReady:true}); await flush();
const legacy=loadPage({store:new Map([['lumivelle-vsl-unlock:dr4rq15xr1:2834','1']]),alreadyReady:true}); await flush();
const vimeo=loadPage({store:new Map([['lumivelle-vsl-unlock:1244806219:2834','1']]),alreadyReady:true}); await flush();
const other=loadPage({store:new Map([['lumivelle-vsl-listen-unlock:v2:dr4rq15xr1:2847','1']]),alreadyReady:true}); await flush();
console.log(JSON.stringify({keys,same:same.revealed(),legacy:legacy.revealed(),vimeo:vimeo.revealed(),other:other.revealed(),legacyStoreUntouched:[...legacy.store.entries()]}));
""")
        self.assertEqual(got['keys'], [KEY])
        self.assertTrue(got['same'])
        self.assertFalse(got['legacy'], 'a legacy/preview-era key must not unlock the listening flow')
        self.assertFalse(got['vimeo'])
        self.assertFalse(got['other'])
        self.assertEqual(got['legacyStoreUntouched'], [[LEGACY_KEY, '1']], 'old state is not transplanted')
    def test_preview_never_writes_a_remembered_unlock(self):
        got = run("const p=loadPage({alreadyReady:true,startTime:2900}); await flush(); p.at(3000); p.at(3100,'seeked'); await flush(); console.log(JSON.stringify({keys:[...p.store.keys()]}));")
        self.assertEqual(got['keys'], [])
    def test_denied_storage_does_not_break_the_unlock(self):
        got = run("""
const p=loadPage({storage:'denied',alreadyReady:true}); await flush(); await listen(p);
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
console.log(JSON.stringify({{error:p.error,revealed:p.revealed(),hidden:p.status.hidden,text:p.status.textContent,html:p.status.innerHTML,btnDisabled:p.startButton.disabled}}));
""")
    def assert_clear_failure(self, got):
        self.assertIsNone(got['error'])
        self.assertFalse(got['revealed'])
        self.assertFalse(got['hidden'])
        self.assertIn('reload', (got['text'] + got['html']).lower())
        self.assertTrue(got['btnDisabled'])
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
console.log(JSON.stringify({shown,hiddenAfter:p.status.hidden,revealed:p.revealed(),enabled:!p.startButton.disabled}));
""")
        self.assertTrue(got['shown'])
        self.assertTrue(got['hiddenAfter'])
        self.assertFalse(got['revealed'])
        self.assertTrue(got['enabled'])

class StageAndTracking(unittest.TestCase):
    def test_stage_only_in_the_listening_session_with_real_sound_and_escape_exits(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush();
p.player._muted=false; p.player.volume=1; p.player.emit('volume-change'); p.player.emit('play'); await flush();
const previewUnmute=p.body.classList.contains('is-stage');
const q=loadPage({alreadyReady:true}); await flush();
q.player.paused=false; q.player.emit('play'); await flush(); const previewPlay=q.body.classList.contains('is-stage');
await listen(q); q.player.emit('volume-change'); await flush();
const on=q.body.classList.contains('is-stage'), stripped=q.body.classList.contains('is-stripped');
q.player.muted='no'; q.player.emit('volume-change');
for (const f of q.docListeners.keydown||[]) f({key:'Escape'});
console.log(JSON.stringify({previewUnmute,previewPlay,on,stripped,afterEsc:q.body.classList.contains('is-stage'),stillStripped:q.body.classList.contains('is-stripped')}));
""")
        self.assertFalse(got['previewUnmute'])
        self.assertFalse(got['previewPlay'])
        self.assertTrue(got['on'])
        self.assertTrue(got['stripped'])
        self.assertFalse(got['afterEsc'])
        self.assertTrue(got['stillStripped'])
    def test_reveal_leaves_stage_and_marks_page_revealed(self):
        got = run("""
const p=loadPage({alreadyReady:true}); await flush(); await listen(p); p.player.emit('volume-change'); await flush();
const staged=p.body.classList.contains('is-stage');
p.at(2834); await flush();
console.log(JSON.stringify({staged,stage:p.body.classList.contains('is-stage'),revealed:p.body.classList.contains('is-revealed')}));
""")
        self.assertTrue(got['staged'])
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
