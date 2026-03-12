import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { RecommendationsView } from './RecommendationsView'
import { PricingRulesForm } from './PricingRulesForm'
import { EventCalendar } from './EventCalendar'
import { MinStayAdvisor } from './MinStayAdvisor'

export function PricingTab() {
  const [subTab, setSubTab] = useState('recommendations')

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dynamic Pricing</h2>
        <p className="text-sm text-muted-foreground">
          HLP algorithm — adjust, accept, or reject AI-generated price recommendations.
        </p>
      </div>

      <Tabs value={subTab} onValueChange={setSubTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
          <TabsTrigger value="rules">Pricing Rules</TabsTrigger>
          <TabsTrigger value="events">Market Events</TabsTrigger>
          <TabsTrigger value="minstay">Min Stay</TabsTrigger>
        </TabsList>

        <TabsContent value="recommendations">
          <RecommendationsView />
        </TabsContent>

        <TabsContent value="rules">
          <PricingRulesForm />
        </TabsContent>

        <TabsContent value="events">
          <EventCalendar />
        </TabsContent>

        <TabsContent value="minstay">
          <MinStayAdvisor />
        </TabsContent>
      </Tabs>
    </div>
  )
}
