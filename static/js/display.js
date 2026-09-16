export const FONT_SCALE_KEYS = ["clock", "status", "notice", "meal", "timetable"];

export function normalizeFontScales(scales = {}) {
  return Object.fromEntries(
    FONT_SCALE_KEYS.map((key) => {
      const value = Number(scales[key]);
      const normalized = Number.isFinite(value) ? Math.round(value) : 100;
      return [key, Math.min(150, Math.max(75, normalized))];
    }),
  );
}

export function applyFontScales(scales, root = document.documentElement) {
  const normalized = normalizeFontScales(scales);
  for (const [key, value] of Object.entries(normalized)) {
    root.style.setProperty(`--font-${key}-scale`, `${value}%`);
  }
  return normalized;
}
