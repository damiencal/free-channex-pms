import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'
import { RECHARTS_PLATFORM_COLORS, getPlatformColor } from '@/lib/platformColors'

interface Booking {
  id: number
  platform: string
  check_in_date: string
  check_out_date: string
  property_slug: string
  property_display_name: string
  guest_name: string
  net_amount: string
}

interface MonthData {
  month: string
  [platform: string]: number | string
}

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function getLast12Months(): Array<{ year: number; month: number; label: string }> {
  const result = []
  const now = new Date()
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    result.push({
      year: d.getFullYear(),
      month: d.getMonth() + 1,
      label: `${MONTH_LABELS[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`,
    })
  }
  return result
}

function aggregateByMonth(bookings: Booking[], months: Array<{ year: number; month: number; label: string }>): { data: MonthData[]; platforms: string[] } {
  const platformSet = new Set<string>()

  // Count bookings per (year, month, platform) by check-in month
  const counts: Map<string, Map<string, number>> = new Map()

  for (const booking of bookings) {
    const [yearStr, monthStr] = booking.check_in_date.split('-')
    const yr = Number(yearStr)
    const mo = Number(monthStr)
    const key = `${yr}-${mo}`
    const platform = booking.platform.toLowerCase()
    platformSet.add(platform)

    if (!counts.has(key)) counts.set(key, new Map())
    const monthMap = counts.get(key)!
    monthMap.set(platform, (monthMap.get(platform) ?? 0) + 1)
  }

  const platforms = Array.from(platformSet).sort()

  const data: MonthData[] = months.map(({ year, month, label }) => {
    const key = `${year}-${month}`
    const monthMap = counts.get(key) ?? new Map<string, number>()
    const entry: MonthData = { month: label }
    for (const p of platforms) {
      entry[p] = monthMap.get(p) ?? 0
    }
    return entry
  })

  return { data, platforms }
}

const chartConfig = {
  airbnb: { label: 'Airbnb', color: RECHARTS_PLATFORM_COLORS['airbnb'] ?? '#f87171' },
  vrbo: { label: 'VRBO', color: RECHARTS_PLATFORM_COLORS['vrbo'] ?? '#60a5fa' },
  rvshare: { label: 'RVshare', color: RECHARTS_PLATFORM_COLORS['rvshare'] ?? '#38bdf8' },
} satisfies ChartConfig

/**
 * Stacked bar chart showing booking counts per platform for the last 12 months.
 */
export function BookingTrendChart() {
  const selectedPropertyId = usePropertyStore((s) => s.selectedPropertyId)
  const months = getLast12Months()
  const [earliest] = months
  const latest = months[months.length - 1]
  const startDate = `${earliest.year}-${String(earliest.month).padStart(2, '0')}-01`
  const endDate = `${latest.year}-${String(latest.month).padStart(2, '0')}-31`

  const params = new URLSearchParams({ start_date: startDate, end_date: endDate })
  if (selectedPropertyId !== null) params.set('property_id', String(selectedPropertyId))

  const { data, isLoading, error, refetch } = useQuery<Booking[]>({
    queryKey: ['dashboard', 'bookings-trend', selectedPropertyId],
    queryFn: () => apiFetch<Booking[]>(`/dashboard/bookings?${params.toString()}`),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <Skeleton className="mb-4 h-5 w-48" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (error) {
    return <ErrorAlert message="Failed to load booking trend data." onRetry={() => refetch()} />
  }

  const { data: chartData, platforms } = aggregateByMonth(data ?? [], months)

  // Build a dynamic config for any platforms found in the data
  const dynamicConfig: ChartConfig = { ...chartConfig }
  for (const p of platforms) {
    if (!(p in dynamicConfig)) {
      dynamicConfig[p] = { label: p, color: getPlatformColor(p) }
    }
  }

  const displayPlatforms = platforms.length > 0 ? platforms : ['airbnb', 'vrbo', 'rvshare']

  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold">Booking Trend (12 Months)</h2>
      <ChartContainer config={dynamicConfig} className="h-52 w-full">
        <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" />
          <XAxis
            dataKey="month"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11 }}
          />
          <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11 }} allowDecimals={false} />
          <ChartTooltip content={<ChartTooltipContent />} />
          {displayPlatforms.map((platform) => (
            <Bar
              key={platform}
              dataKey={platform}
              stackId="bookings"
              fill={`var(--color-${platform})`}
              radius={platform === displayPlatforms[displayPlatforms.length - 1] ? [4, 4, 0, 0] : [0, 0, 0, 0]}
            />
          ))}
        </BarChart>
      </ChartContainer>
    </div>
  )
}
