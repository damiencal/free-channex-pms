import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MarketOverview } from './MarketOverview'
import { CompSetManager } from './CompSetManager'

export function MarketTab() {
  const [subTab, setSubTab] = useState('overview')

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Market Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Market demand signals, supply trends, and competitive set benchmarking.
        </p>
      </div>

      <Tabs value={subTab} onValueChange={setSubTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="overview">Market Overview</TabsTrigger>
          <TabsTrigger value="compsets">Comp Sets</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <MarketOverview />
        </TabsContent>
        <TabsContent value="compsets">
          <CompSetManager />
        </TabsContent>
      </Tabs>
    </div>
  )
}
