import { useCallback, useEffect, useRef, useState } from 'react';
import { MATERIALS } from '../api/types';
import { LEVELS } from '../lib/format';
import { useMission } from '../state/mission';
import { HELP_TEXT, parseCommand, type ScreenKey, type VoiceAction } from './commands';
import { speak, speechSupported, stopSpeaking } from './speech';

// The browser's recognition API is not in the standard TS lib.
type Rec = { lang: string; continuous: boolean; interimResults: boolean; start: () => void; stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> & { length: number } }) => void) | null; onend: (() => void) | null; onerror: (() => void) | null };
type RecCtor = new () => Rec;
const getRec = (): RecCtor | null => {
  const w = window as unknown as { SpeechRecognition?: RecCtor; webkitSpeechRecognition?: RecCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
};

export function VoicePanel({ go }: { go: (s: ScreenKey) => void }) {
  const { result, presets, setScenario } = useMission();
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState(true);
  const [listening, setListening] = useState(false);
  const [heard, setHeard] = useState('');
  const [reply, setReply] = useState('');
  const last = useRef<string | null>(null);
  const rec = useRef<Rec | null>(null);
  const supportsMic = typeof window !== 'undefined' && !!getRec();

  const say = useCallback((t: string, urgent = false) => { setReply(t); if (alerts) speak(t, { urgent }); }, [alerts]);

  // Spoken alert when the risk level changes.
  const level = result?.risk.level;
  useEffect(() => {
    if (!level) return;
    if (last.current && last.current !== level) {
      const worse = LEVELS.indexOf(level) > LEVELS.indexOf(last.current as typeof LEVELS[number]);
      say(worse ? `Warning. Fire risk is now ${level.toLowerCase()}.` : `Fire risk has eased to ${level.toLowerCase()}.`, level === 'CRITICAL' || level === 'HIGH');
    }
    last.current = level;
  }, [level, say]);

  const run = useCallback((a: VoiceAction | null) => {
    if (!a) return say('Sorry, I did not understand. Say help to hear what I can do.');
    switch (a.kind) {
      case 'goto': go(a.screen); return say(`Opening ${a.screen}.`);
      case 'preset': { const p = presets[a.index]; if (!p) return say('That scenario does not exist.'); setScenario(p.scenario); return say(`Loaded ${p.name}.`); }
      case 'set': setScenario({ [a.field]: a.value }); return say(`Set ${a.field.replace(/_/g, ' ')} to ${a.value}.`);
      case 'material': if (MATERIALS.includes(a.value)) setScenario({ material: a.value }); return say(`Material set to ${a.value}.`);
      case 'gravity': setScenario({ gravity: a.value }); return say(`Gravity set to ${a.value}.`);
      case 'status': return say(result ? `Fire risk is ${result.risk.level.toLowerCase()}, score ${result.risk.score}. Trust score ${result.trust.score}, ${result.trust.band.toLowerCase()}.` : 'No result yet.');
      case 'read_actions': return say(result ? `${result.decision.summary} ${result.decision.actions.map((x) => x.title).join('. ')}.` : 'No result yet.');
      case 'mute': setAlerts(!a.on); if (a.on) stopSpeaking(); return setReply(a.on ? 'Voice alerts muted.' : 'Voice alerts on.');
      case 'help': return say('You can say: go to council, set oxygen to twenty two, load scenario three, status, or recommended actions.');
      case 'refused': return say(a.reason, true);
    }
  }, [go, presets, result, say, setScenario]);

  function toggleMic() {
    if (listening) { rec.current?.stop(); return; }
    const C = getRec(); if (!C) return;
    const r = new C(); r.lang = 'en-IN'; r.continuous = false; r.interimResults = false;
    r.onresult = (e) => { const t = e.results[e.results.length - 1]?.[0]?.transcript ?? ''; setHeard(t); run(parseCommand(t)); };
    r.onend = () => setListening(false); r.onerror = () => setListening(false);
    rec.current = r; setListening(true); r.start();
  }

  return (
    <>
      <button className={`vfab ${listening ? 'live' : ''}`} onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="voicepanel">
        <span aria-hidden="true">🎙</span><span>Voice</span>
      </button>
      {open && (
        <section id="voicepanel" className="vpanel" aria-label="Voice control">
          <h2>Voice</h2>
          <div className="note">Alerts use an Indian-English voice when your device has one. Voice cannot approve or execute anything.</div>
          <label className="vrow"><input type="checkbox" checked={alerts} onChange={(e) => { setAlerts(e.target.checked); if (!e.target.checked) stopSpeaking(); }} /> Spoken alerts</label>
          {!speechSupported() && <div className="errbox">This browser cannot speak. Alerts stay on screen.</div>}
          <button className="btn primary" disabled={!supportsMic} onClick={toggleMic} title={supportsMic ? '' : 'Speech recognition is not available in this browser (try Chrome or Edge).'}>{listening ? 'Stop listening' : 'Start listening'}</button>
          <form onSubmit={(e) => { e.preventDefault(); const f = new FormData(e.currentTarget); const t = String(f.get('cmd') ?? ''); setHeard(t); run(parseCommand(t)); e.currentTarget.reset(); }} className="vform">
            <input name="cmd" aria-label="Type a voice command" placeholder="or type a command, e.g. set oxygen to 22" /><button className="btn">Run</button>
          </form>
          {heard && <div className="vstat">Heard: <b>{heard}</b></div>}
          {reply && <div className="vstat" role="status">{reply}</div>}
          <ul className="vhelp">{HELP_TEXT.map((h) => <li key={h}>{h}</li>)}</ul>
        </section>
      )}
    </>
  );
}
