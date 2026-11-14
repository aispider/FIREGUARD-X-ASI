import type { Gravity, Material } from '../api/types';

export type ScreenKey = 'mission' | 'twin' | 'council' | 'evidence' | 'debate' | 'trust' | 'security' | 'analytics' | 'audit';

export type VoiceAction =
  | { kind: 'goto'; screen: ScreenKey }
  | { kind: 'preset'; index: number }
  | { kind: 'set'; field: 'oxygen_percent' | 'airflow_cm_s' | 'pressure_kpa' | 'temperature_k'; value: number }
  | { kind: 'material'; value: Material }
  | { kind: 'gravity'; value: Gravity }
  | { kind: 'status' }
  | { kind: 'read_actions' }
  | { kind: 'mute'; on: boolean }
  | { kind: 'help' }
  | { kind: 'refused'; reason: string };

const SCREENS: [RegExp, ScreenKey][] = [
  [/mission|command|home/, 'mission'], [/twin|flame|fire view/, 'twin'], [/council|agents?/, 'council'],
  [/evidence|sources?/, 'evidence'], [/debate/, 'debate'], [/trust/, 'trust'], [/security|cyber/, 'security'],
  [/analytics|chart|graph/, 'analytics'], [/audit|log/, 'audit'],
];
const NUMBERS: Record<string, number> = { zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };
const FIELDS: [RegExp, 'oxygen_percent' | 'airflow_cm_s' | 'pressure_kpa' | 'temperature_k'][] = [
  [/oxygen|o2/, 'oxygen_percent'], [/air ?flow|flow|ventilation/, 'airflow_cm_s'], [/pressure/, 'pressure_kpa'], [/temperature|temp/, 'temperature_k'],
];
const MATERIALS: [RegExp, Material][] = [
  [/pmma|acrylic/, 'PMMA'], [/cotton|fiberglass|fibreglass/, 'Cotton-fiberglass fabric'], [/polyethylene/, 'Polyethylene'],
  [/silicone/, 'Silicone'], [/nomex/, 'Nomex fabric'],
];
const GRAVITIES: [RegExp, Gravity][] = [[/micro ?gravity|zero g/, 'microgravity'], [/lunar|moon/, 'lunar'], [/mars|martian/, 'mars'], [/earth/, 'earth']];

function numberIn(t: string): number | null {
  const m = t.match(/-?\d+(?:\.\d+)?/);
  if (m) return Number(m[0]);
  const w = t.split(/\s+/).find((x) => x in NUMBERS);
  return w ? (NUMBERS[w] ?? null) : null;
}

/** Turns a spoken phrase into one action. Voice can never approve, reject or execute anything. */
export function parseCommand(raw: string): VoiceAction | null {
  const t = raw.toLowerCase().replace(/[,!?]|\.(?!\d)/g, ' ').replace(/\s+/g, ' ').trim();
  if (!t) return null;
  if (/\b(approve|reject|execute|launch|release|confirm|suppress now)\b/.test(t)) {
    return { kind: 'refused', reason: 'Approvals and actions need a person to press the button on screen. Voice cannot approve or execute anything.' };
  }
  if (/\bhelp\b|what can i say/.test(t)) return { kind: 'help' };
  if (/\b(mute|silence|quiet)\b/.test(t)) return { kind: 'mute', on: true };
  if (/\b(unmute|speak|alerts on)\b/.test(t)) return { kind: 'mute', on: false };
  if (/status|how bad|situation|risk level|summary/.test(t)) return { kind: 'status' };
  if (/recommend|actions|what should/.test(t)) return { kind: 'read_actions' };
  const preset = t.match(/(?:scenario|preset|load)\s+(\w+)/);
  if (preset) { const n = numberIn(preset[1] ?? ''); if (n !== null && n >= 1 && n <= 9) return { kind: 'preset', index: n - 1 }; }
  if (/^(go to|open|show|switch to)\b/.test(t)) {
    const hit = SCREENS.find(([re]) => re.test(t));
    if (hit) return { kind: 'goto', screen: hit[1] };
  }
  if (/\b(set|change|make)\b/.test(t)) {
    const mat = MATERIALS.find(([re]) => re.test(t)); if (mat && /material|fuel/.test(t)) return { kind: 'material', value: mat[1] };
    const gr = GRAVITIES.find(([re]) => re.test(t)); if (gr && /gravity/.test(t)) return { kind: 'gravity', value: gr[1] };
    const f = FIELDS.find(([re]) => re.test(t)); const n = numberIn(t);
    if (f && n !== null) return { kind: 'set', field: f[1], value: n };
  }
  const hit = SCREENS.find(([re]) => re.test(t));
  return hit && t.split(' ').length <= 3 ? { kind: 'goto', screen: hit[1] } : null;
}

export const HELP_TEXT = [
  'Go to council, evidence, debate, trust, security, analytics, audit',
  'Set oxygen to 22   ·   set airflow to 5   ·   set material to nomex   ·   set gravity to mars',
  'Load scenario 3   ·   status   ·   recommended actions   ·   mute / unmute',
];
