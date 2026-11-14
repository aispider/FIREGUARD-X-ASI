import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { AnalysisResult, PresetOut, ScenarioIn } from '../api/types';
import { isAbortError } from '../api/client';
import { explainError, type FriendlyError } from '../lib/errors';
import { useAuth } from './auth';

export const DEFAULT_SCENARIO: ScenarioIn = {
  name: 'Mission Day 183', oxygen_percent: 20.4, airflow_cm_s: 3.2, pressure_kpa: 101, temperature_k: 420,
  external_heating_kw_m2: 10, material: 'PMMA', fuel_geometry: 'thin_sheet', gravity: 'microgravity', sensor_flags: null,
};

interface MissionCtx {
  scenario: ScenarioIn;
  setScenario: (patch: Partial<ScenarioIn>) => void;
  presets: PresetOut[];
  result: AnalysisResult | null;
  loading: boolean;
  error: FriendlyError | null;
  retry: () => void;
  /** Store the current assessment (needs risk:assess) and return its ID. */
  persist: () => Promise<AnalysisResult | null>;
  refreshKey: number;
  bump: () => void;
}

const Ctx = createContext<MissionCtx | null>(null);

export function MissionProvider({ children }: { children: ReactNode }) {
  const { api, user } = useAuth();
  const [scenario, setS] = useState<ScenarioIn>(DEFAULT_SCENARIO);
  const [presets, setPresets] = useState<PresetOut[]>([]);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<FriendlyError | null>(null);
  const [refreshKey, setRefresh] = useState(0);
  const ctl = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!user) return;
    api.presets().then(setPresets).catch(() => undefined);
  }, [api, user]);

  useEffect(() => {
    if (!user) return;
    const t = setTimeout(() => {
      ctl.current?.abort();
      const c = new AbortController();
      ctl.current = c;
      setLoading(true);
      api
        .analyze(scenario, false, { signal: c.signal })
        .then((r) => { setResult(r); setError(null); })
        .catch((e) => { if (!isAbortError(e)) setError(explainError(e)); })
        .finally(() => { if (ctl.current === c) setLoading(false); });
    }, 300);
    return () => clearTimeout(t);
  }, [api, user, scenario, refreshKey]);

  const setScenario = useCallback((p: Partial<ScenarioIn>) => setS((s) => ({ ...s, ...p })), []);
  const persist = useCallback(async () => {
    try { const r = await api.analyze(scenario, true); setResult(r); setError(null); return r; }
    catch (e) { setError(explainError(e)); return null; }
  }, [api, scenario]);

  const value = useMemo(
    () => ({ scenario, setScenario, presets, result, loading, error, retry: () => setRefresh((n) => n + 1), persist,
      refreshKey, bump: () => setRefresh((n) => n + 1) }),
    [scenario, setScenario, presets, result, loading, error, persist, refreshKey],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useMission(): MissionCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useMission outside MissionProvider');
  return c;
}
