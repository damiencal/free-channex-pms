import { format, addMonths, startOfMonth } from 'date-fns'
import { useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { usePacingData } from '@/hooks/useAnalytics'
import { usePropertyStore } from '@/store/usePropertyStore'

export function PacingChart() {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  const [monthOffset, setMonthOffset] = useState(0)
  const targetDate = addMonths(startOfMonth(new Date()), monthOffset)
  const targetMonth = format(targetDate, 'yyyy-MM-dd')

  const { data, isLoading } = usePacingData(targetMonth)

  if (!propertyId) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Select a property to view pacing data.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon" onClick={() => setMonthOffset((o) => o - 1)}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="min-w-[12ch] text-center font-medium">
          {format(targetDate, 'MMMM yyyy')}
        </span>
        <Button variant="outline" size="icon" onClick={() => setMonthOffset((o) => o + 1)}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading pacing data…</div>
      ) : !data ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No pacing data available for this month.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {/* Summary cards */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">This Year Bookings</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{data.this_year_bookings}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">Last Year Bookings</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{data.last_year_bookings}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">Pace Index</CardTitle>
            </CardHeader>
            <CardContent>
              <p
                className={`text-3xl font-bold ${
                  data.pace_index >= 1 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {data.pace_index.toFixed(2)}×
              </p>
              <p className="text-xs text-muted-foreground">vs same time last year</p>
            </CardContent>
          </Card>

          {/* Weekly pickup chart */}
          <div className="lg:col-span-3">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Weekly Pickup — this year vs last year</CardTitle>
                <CardDescription>
                  Number of bookings received each week for {format(targetDate, 'MMMM yyyy')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={data.weekly_pickup}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="week_start"
                      tickFormatter={(v) => format(new Date(v + 'T12:00:00'), 'MMM d')}
                      className="text-xs"
                    />
                    <YAxis allowDecimals={false} className="text-xs" />
                    <Tooltip
                      labelFormatter={(v) => format(new Date(v + 'T12:00:00'), 'MMM d, yyyy')}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="this_year"
                      name="This Year"
                      stroke="hsl(var(--chart-1))"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="last_year"
                      name="Last Year"
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
