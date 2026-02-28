import { PieChart, Pie, Cell } from 'recharts'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import { useOccupancy, type OccupancyProperty } from '@/hooks/useFinancials'

// Distinct property colors (not platform colors)
const PROPERTY_COLORS = [
  '#6366f1', // indigo
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ec4899', // pink
  '#8b5cf6', // violet
]

interface PieDataEntry {
  name: string
  slug: string
  value: number
  color: string
}

function getLatestOccupancyRate(prop: OccupancyProperty): number {
  if (prop.months.length === 0) return 0
  // Use most recent month that has some nights data
  const sorted = [...prop.months].reverse()
  const latest = sorted.find((m) => m.total_nights > 0)
  return latest ? latest.occupancy_rate : 0
}

function buildPieData(properties: OccupancyProperty[]): PieDataEntry[] {
  return properties.map((prop, i) => ({
    name: prop.property_display_name,
    slug: prop.property_slug,
    value: Math.round(getLatestOccupancyRate(prop) * 100),
    color: PROPERTY_COLORS[i % PROPERTY_COLORS.length],
  }))
}

/**
 * Donut chart showing current occupancy rate per property.
 */
export function OccupancyChart() {
  const { data, isLoading, error, refetch } = useOccupancy()

  if (isLoading) {
    return (
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <Skeleton className="mb-4 h-5 w-36" />
        <div className="flex justify-center">
          <Skeleton className="h-48 w-48 rounded-full" />
        </div>
      </div>
    )
  }

  if (error) {
    return <ErrorAlert message="Failed to load occupancy data." onRetry={() => refetch()} />
  }

  const properties = data ?? []
  const pieData = buildPieData(properties)
  const avgOccupancy =
    pieData.length > 0
      ? Math.round(pieData.reduce((sum, d) => sum + d.value, 0) / pieData.length)
      : 0

  const chartConfig: ChartConfig = Object.fromEntries(
    pieData.map((d) => [d.slug, { label: d.name, color: d.color }])
  )

  // If no data, show a placeholder
  if (pieData.length === 0) {
    return (
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold">Current Occupancy</h2>
        <p className="text-center text-sm text-muted-foreground py-8">No occupancy data available</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold">Current Occupancy</h2>
      <ChartContainer config={chartConfig} className="mx-auto h-52 w-full max-w-xs">
        <PieChart>
          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value) => [`${value}%`, '']}
                hideLabel
              />
            }
          />
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={88}
            paddingAngle={2}
            dataKey="value"
            nameKey="name"
          >
            {pieData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
        </PieChart>
      </ChartContainer>

      {/* Center text overlay */}
      <div className="-mt-32 mb-16 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-2xl font-bold">{avgOccupancy}%</span>
        <span className="text-xs text-muted-foreground">avg occupancy</span>
      </div>

      {/* Legend */}
      <div className="mt-4 space-y-1.5">
        {pieData.map((d) => (
          <div key={d.slug} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: d.color }} />
              <span className="text-muted-foreground">{d.name}</span>
            </div>
            <span className="font-medium tabular-nums">{d.value}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
