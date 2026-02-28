import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card'

const REPORTS = [
  {
    title: 'Profit & Loss',
    description: 'Revenue by platform, expenses by category',
    endpoint: '/api/reports/pl',
  },
  {
    title: 'Balance Sheet',
    description: 'Assets, liabilities, and equity snapshot',
    endpoint: '/api/reports/balance-sheet',
  },
  {
    title: 'Income Statement',
    description: 'Revenue and expense breakdown',
    endpoint: '/api/reports/income-statement',
  },
]

/**
 * Reports tab placeholder. Shows the three available report types with their
 * API endpoints. Full UI views are deferred to a future development phase.
 */
export function ReportsTab() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Reports</h2>

      <div className="space-y-3">
        {REPORTS.map((report) => (
          <Card key={report.title}>
            <CardHeader>
              <CardTitle className="text-base">{report.title}</CardTitle>
              <CardDescription>{report.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground font-mono">
                Available via API at {report.endpoint}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <p className="text-sm text-muted-foreground text-center pt-2">
        Full report views coming soon
      </p>
    </div>
  )
}
