import { describe, expect, it } from 'vitest';
import { parseCommand } from '../src/voice/commands';
import { pickVoice } from '../src/voice/speech';

describe('voice commands', () => {
  it('opens screens', () => {
    expect(parseCommand('Go to the security center')).toEqual({ kind: 'goto', screen: 'security' });
    expect(parseCommand('open audit log')).toEqual({ kind: 'goto', screen: 'audit' });
  });
  it('sets values with digits or words', () => {
    expect(parseCommand('set oxygen to 22.5')).toEqual({ kind: 'set', field: 'oxygen_percent', value: 22.5 });
    expect(parseCommand('set airflow to five')).toEqual({ kind: 'set', field: 'airflow_cm_s', value: 5 });
  });
  it('sets material and gravity', () => {
    expect(parseCommand('set material to nomex')).toEqual({ kind: 'material', value: 'Nomex fabric' });
    expect(parseCommand('set gravity to mars')).toEqual({ kind: 'gravity', value: 'mars' });
  });
  it('refuses to approve or execute by voice', () => {
    for (const t of ['approve the action', 'execute command', 'confirm approval', 'release suppression']) {
      expect(parseCommand(t)?.kind).toBe('refused');
    }
  });
  it('returns null for unrelated speech', () => {
    expect(parseCommand('what a nice day it is today')).toBeNull();
  });
});

describe('voice choice', () => {
  const v = (name: string, lang: string) => ({ name, lang }) as SpeechSynthesisVoice;
  it('prefers Indian English, then any English, else none', () => {
    expect(pickVoice([v('A', 'en-US'), v('B', 'en-IN')])?.name).toBe('B');
    expect(pickVoice([v('A', 'fr-FR'), v('B', 'en-GB')])?.name).toBe('B');
    expect(pickVoice([v('A', 'fr-FR')])).toBeNull();
  });
});
