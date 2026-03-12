import { AlertTriangle, Info, Zap } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { ListingRecommendation } from '@/api/listingOptimizer'

const PRIORITY_CONFIG = {
  high: {
    icon: AlertTriangle,
    badgeClass: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    label: 'High Impact',
  },
  medium: {
    icon: Zap,
    badgeClass: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    label: 'Medium Impact',
  },
  low: {
    icon: Info,
    badgeClass: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    label: 'Low Impact',
  },
}

const CATEGORY_LABELS: Record<string, string> = {
  title: 'Title',
  description: 'Description',
  photos: 'Photos',
  amenities: 'Amenities',
  pricing: 'Pricing',
}

interface Props {
  recommendations: ListingRecommendation[]
}

export function RecommendationsList({ recommendations }: Props) {
  if (!recommendations.length) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No recommendations generated.
        </CardContent>
      </Card>
    )
  }

  const grouped = recommendations.reduce<Record<string, ListingRecommendation[]>>(
    (acc, r) => {
      if (!acc[r.priority]) acc[r.priority] = []
      acc[r.priority].push(r)
      return acc
    },
    {}
  )

  const order = ['high', 'medium', 'low']

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">Recommendations ({recommendations.length})</h3>

      {order.map((priority) => {
        const recs = grouped[priority]
        if (!recs?.length) return null
        const config = PRIORITY_CONFIG[priority as keyof typeof PRIORITY_CONFIG]
        const Icon = config.icon

        return (
          <div key={priority}>
            <h4 className="mb-2 flex items-center gap-1.5 text-sm font-medium">
              <Icon className="h-4 w-4" />
              {config.label}
            </h4>
            <div className="space-y-2">
              {recs.map((rec, i) => (
                <Card key={i} className="border-l-4 border-l-current">
                  <CardContent className="py-3 px-4 space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge
                        variant="outline"
                        className={`text-[10px] h-4 ${config.badgeClass}`}
                      >
                        {config.label}
                      </Badge>
                      <Badge variant="secondary" className="text-[10px] h-4">
                        {CATEGORY_LABELS[rec.category] ?? rec.category}
                      </Badge>
                    </div>
                    <p className="text-sm font-medium">{rec.finding}</p>
                    <p className="text-sm text-muted-foreground">
                      <strong>Action:</strong> {rec.action}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      <strong>Impact:</strong> {rec.impact}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
