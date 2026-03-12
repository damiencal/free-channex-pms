import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { KPIDashboard } from './KPIDashboard'
import { PacingChart } from './PacingChart'
import { TrendCharts } from './TrendCharts'
import { PerformanceTable } from './PerformanceTable'

export function AnalyticsTab() {
  const [subTab, setSubTab] = useState('kpis')

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Portfolio Analytics</h2>
        <p className="text-sm text-muted-foreground">
          Occupancy, ADR, RevPAR, pacing, and performance trends.
        </p>
      </div>

      <Tabs value={subTab} onValueChange={setSubTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="kpis">KPI Summary</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="pacing">Pacing</TabsTrigger>
          <TabsTrigger value="table">Monthly Table</TabsTrigger>
        </TabsList>

        <TabsContent value="kpis">
          <KPIDashboard />
        </TabsContent>
        <TabsContent value="trends">
          <TrendCharts />
        </TabsContent>
        <TabsContent value="pacing">
          <PacingChart />
        </TabsContent>
        <TabsContent value="table">
          <PerformanceTable />
        </TabsContent>
      </Tabs>
    </div>
  )
}
