/** Spoken output with an Indian-English voice when the device has one (falls back to any English voice). */
export function pickVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const pref = (v: SpeechSynthesisVoice) =>
    /en[-_]IN/i.test(v.lang) ? 0 : /india|heera|ravi|neerja|prabhat/i.test(v.name) ? 1 : /^en/i.test(v.lang) ? 2 : 9;
  return [...voices].sort((a, b) => pref(a) - pref(b)).find((v) => pref(v) < 9) ?? null;
}

export const speechSupported = (): boolean => typeof window !== 'undefined' && 'speechSynthesis' in window;

export function speak(text: string, opts: { rate?: number; urgent?: boolean } = {}): void {
  if (!speechSupported()) return;
  const synth = window.speechSynthesis;
  if (opts.urgent) synth.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const v = pickVoice(synth.getVoices());
  u.lang = v?.lang ?? 'en-IN';
  if (v) u.voice = v;
  u.rate = opts.rate ?? 0.92;
  synth.speak(u);
}

export function stopSpeaking(): void {
  if (speechSupported()) window.speechSynthesis.cancel();
}
