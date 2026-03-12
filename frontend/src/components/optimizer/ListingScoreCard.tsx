import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { ListingAnalysis } from '@/api/listingOptimizer'
import { format } from 'date-fns'

const SCORE_COLOR = (score: number | null) => {
  if (!score) return 'text-muted-foreground'
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

function ScoreRing({ score, label }: { score: number | null; label: string }) {
  const pct = score ?? 0
  const circumference = 2 * Math.PI * 30
  const filled = (pct / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative inline-flex items-center justify-center">
        <svg width="70" height="70" className="-rotate-90">
          <circle cx="35" cy="35" r="30" fill="none" stroke="hsl(var(--muted))" strokeWidth="6" />
          <circle
            cx="35"
            cy="35"
            r="30"
            fill="none"
            stroke={pct >= 80 ? '#16a34a' : pct >= 60 ? '#ca8a04' : '#dc2626'}
            strokeWidth="6"
            strokeDasharray={`${filled} ${circumference}`}
            strokeLinecap="round"
          />
        </svg>
        <span className={`absolute text-sm font-bold tabular-nums ${SCORE_COLOR(score)}`}>
          {score ?? '—'}
        </span>
      </div>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}

interface Props {
  analysis: ListingAnalysis
}

export function ListingScoreCard({ analysis }: Props) {
  return (
    <Card className="h-fit">
      <CardHeader>
        <CardTitle className="text-base">Listing Scores</CardTitle>
        <p className="text-xs text-muted-foreground">
          Analyzed {format(new Date(analysis.analyzed_at), 'MMM d, yyyy h:mm a')}
          {analysis.model_used && ` · ${analysis.model_used}`}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall score — large */}
        <div className="flex flex-col items-center py-2">
          <ScoreRing score={analysis.overall_score} label="Overall" />
        </div>

        {/* Sub-scores grid */}
        <div className="grid grid-cols-2 gap-4">
          <ScoreRing score={analysis.title_score} label="Title" />
          <ScoreRing score={analysis.description_score} label="Description" />
          <ScoreRing score={analysis.photos_score} label="Photos" />
          <ScoreRing score={analysis.amenities_score} label="Amenities" />
          <ScoreRing score={analysis.pricing_score} label="Pricing" />
        </div>
      </CardContent>
    </Card>
  )
}
