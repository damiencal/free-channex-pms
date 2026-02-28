/**
 * Platform color definitions for Airbnb, VRBO, and RVshare.
 * Provides light/dark variants and Recharts-compatible chart fill colors.
 */

export type Platform = 'airbnb' | 'vrbo' | 'rvshare' | string

interface PlatformColorEntry {
  light: string
  dark: string
  chart: string
}

export const PLATFORM_COLORS: Record<string, PlatformColorEntry> = {
  airbnb: {
    light: '#fca5a5',
    dark: '#7f1d1d',
    chart: '#f87171',
  },
  vrbo: {
    light: '#93c5fd',
    dark: '#1e3a8a',
    chart: '#60a5fa',
  },
  rvshare: {
    light: '#7dd3fc',
    dark: '#0c4a6e',
    chart: '#38bdf8',
  },
}

const FALLBACK_COLOR: PlatformColorEntry = {
  light: '#d1d5db',
  dark: '#374151',
  chart: '#9ca3af',
}

/**
 * Get color entry for a platform (case-insensitive).
 */
export function getPlatformColorEntry(platform: Platform): PlatformColorEntry {
  const key = platform.toLowerCase()
  return PLATFORM_COLORS[key] ?? FALLBACK_COLOR
}

/**
 * Get the Recharts-compatible chart fill color for a platform.
 */
export function getPlatformColor(platform: Platform): string {
  return getPlatformColorEntry(platform).chart
}

/**
 * Recharts color map keyed by platform name — use as dataKey for chart fills.
 */
export const RECHARTS_PLATFORM_COLORS: Record<string, string> = Object.fromEntries(
  Object.entries(PLATFORM_COLORS).map(([key, val]) => [key, val.chart])
)
