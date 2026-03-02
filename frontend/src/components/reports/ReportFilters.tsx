import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

type Preset = 'this-month' | 'this-quarter' | 'ytd' | 'last-year' | 'custom' | null

interface RangeParams {
  start_date: string
  end_date: string
}

interface SnapshotParams {
  as_of: string
}

interface ReportFiltersProps {
  mode: 'range' | 'snapshot'
  onGenerate: (params: RangeParams | SnapshotParams) => void
  isFetching: boolean
  className?: string
}

function padMonth(m: number): string {
  return String(m).padStart(2, '0')
}

function getPresetDates(preset: Exclude<Preset, 'custom' | null>): { start: string; end: string } {
  const today = new Date()
  const year = today.getFullYear()
  const month = today.getMonth() + 1 // 1-indexed

  switch (preset) {
    case 'this-month': {
      const lastDay = new Date(year, month, 0).getDate()
      return {
        start: `${year}-${padMonth(month)}-01`,
        end: `${year}-${padMonth(month)}-${lastDay}`,
      }
    }
    case 'this-quarter': {
      const q = Math.ceil(month / 3)
      const qStart = (q - 1) * 3 + 1
      const qEnd = q * 3
      const lastDay = new Date(year, qEnd, 0).getDate()
      return {
        start: `${year}-${padMonth(qStart)}-01`,
        end: `${year}-${padMonth(qEnd)}-${lastDay}`,
      }
    }
    case 'ytd': {
      const todayStr = today.toISOString().split('T')[0]
      return { start: `${year}-01-01`, end: todayStr }
    }
    case 'last-year': {
      return { start: `${year - 1}-01-01`, end: `${year - 1}-12-31` }
    }
  }
}

export function ReportFilters({ mode, onGenerate, isFetching, className }: ReportFiltersProps) {
  const [activePreset, setActivePreset] = useState<Preset>(null)
  const [customStart, setCustomStart] = useState('')
  const [customEnd, setCustomEnd] = useState('')

  function handlePreset(preset: Exclude<Preset, null>) {
    setActivePreset(preset)
    if (preset !== 'custom') {
      setCustomStart('')
      setCustomEnd('')
    }
  }

  function canGenerate(): boolean {
    if (activePreset === null) return false
    if (activePreset === 'custom') {
      if (mode === 'range') return Boolean(customStart && customEnd)
      return Boolean(customStart)
    }
    return true
  }

  function handleGenerate() {
    if (!canGenerate()) return

    if (activePreset === 'custom') {
      if (mode === 'range') {
        onGenerate({ start_date: customStart, end_date: customEnd })
      } else {
        // snapshot: use customStart as the as_of date
        onGenerate({ as_of: customStart })
      }
      return
    }

    const preset = activePreset as Exclude<Preset, 'custom' | null>
    const { start, end } = getPresetDates(preset)

    if (mode === 'range') {
      onGenerate({ start_date: start, end_date: end })
    } else {
      // snapshot: use the end date of the preset period as the as_of date
      onGenerate({ as_of: end })
    }
  }

  const presets: Array<{ key: Exclude<Preset, 'custom' | null>; label: string }> = [
    { key: 'this-month', label: 'This Month' },
    { key: 'this-quarter', label: 'This Quarter' },
    { key: 'ytd', label: 'YTD' },
    { key: 'last-year', label: 'Last Year' },
  ]

  return (
    <div className={className}>
      <div className="flex flex-wrap items-center gap-2">
        {presets.map(({ key, label }) => (
          <Button
            key={key}
            variant={activePreset === key ? 'default' : 'outline'}
            size="sm"
            onClick={() => handlePreset(key)}
            type="button"
          >
            {label}
          </Button>
        ))}

        <Button
          variant={activePreset === 'custom' ? 'default' : 'outline'}
          size="sm"
          onClick={() => handlePreset('custom')}
          type="button"
        >
          Custom
        </Button>

        {activePreset === 'custom' && mode === 'range' && (
          <>
            <Input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="w-auto"
              aria-label="Start Date"
            />
            <Input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="w-auto"
              aria-label="End Date"
            />
          </>
        )}

        {activePreset === 'custom' && mode === 'snapshot' && (
          <Input
            type="date"
            value={customStart}
            onChange={(e) => setCustomStart(e.target.value)}
            className="w-auto"
            aria-label="As Of Date"
          />
        )}

        <Button
          variant="default"
          size="sm"
          onClick={handleGenerate}
          disabled={isFetching || !canGenerate()}
          type="button"
        >
          {isFetching ? 'Generating...' : 'Generate'}
        </Button>
      </div>
    </div>
  )
}
