/** Mapping between the template's display labels and the backend's enum values. */
import type { Geometry, Gravity, Material } from '../api/types';
import { GEOMETRIES, GRAVITIES, MATERIALS } from '../api/types';

export const GEOMETRY_LABEL: Record<Geometry, string> = {
  thin_sheet: 'Thin sheet',
  cylinder: 'Cylinder',
  thick_slab: 'Thick slab',
};

export const GRAVITY_LABEL: Record<Gravity, string> = {
  microgravity: 'Microgravity',
  lunar: 'Lunar (0.16 g)',
  mars: 'Mars (0.38 g)',
  earth: 'Earth (1 g)',
};

/** Fraction of 1 g, used by the flame canvas to bend the plume. */
export const GRAVITY_G: Record<Gravity, number> = { microgravity: 0, lunar: 0.16, mars: 0.38, earth: 1 };

/** Short material names for chips and sentences. */
export const MATERIAL_SHORT: Record<Material, string> = {
  PMMA: 'PMMA',
  'Cotton-fiberglass fabric': 'Cotton-fiberglass',
  Polyethylene: 'Polyethylene',
  Silicone: 'Silicone',
  'Nomex fabric': 'Nomex fabric',
};

/** Flame canvas sample colour per material (template FUELS.hue). */
export const MATERIAL_HUE: Record<Material, [number, number, number]> = {
  PMMA: [120, 170, 220],
  'Cotton-fiberglass fabric': [190, 170, 130],
  Polyethylene: [200, 200, 205],
  Silicone: [150, 150, 160],
  'Nomex fabric': [190, 160, 110],
};

/** Sample thickness in canvas units per geometry (template GEOM.t). */
export const GEOMETRY_THICKNESS: Record<Geometry, number> = { thin_sheet: 6, cylinder: 16, thick_slab: 24 };

const norm = (s: string): string => s.trim().toLowerCase();

/** Template label (or API value) -> API geometry. Returns null when unknown. */
export function geometryFromLabel(label: string): Geometry | null {
  const n = norm(label);
  return GEOMETRIES.find((g) => g === n || norm(GEOMETRY_LABEL[g]) === n) ?? null;
}

/** Template label (or API value) -> API gravity. Returns null when unknown. */
export function gravityFromLabel(label: string): Gravity | null {
  const n = norm(label);
  return GRAVITIES.find((g) => g === n || norm(GRAVITY_LABEL[g]) === n) ?? null;
}

export function materialFromLabel(label: string): Material | null {
  const n = norm(label);
  return MATERIALS.find((m) => norm(m) === n || norm(MATERIAL_SHORT[m]) === n) ?? null;
}
