import { TrendingUp, TrendingDown, Info } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { SkeletonCard } from '@/components/shared/SkeletonCard'

interface StatCardProps {
  title: string
  value: string
  yoyChange: string | null
  tooltipText: string
  isLoading?: boolean
}

/**
 * Stat card with large number display, YoY change indicator, and tooltip explanation.
 */
export function StatCard({ title, value, yoyChange, tooltipText, isLoading }: StatCardProps) {
  if (isLoading) {
    return <SkeletonCard />
  }

  const isPositive = yoyChange !== null && yoyChange.startsWith('+')
  const isNegative = yoyChange !== null && yoyChange.startsWith('-')

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
          {title}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-3.5 w-3.5 cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-48">
                {tooltipText}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold tabular-nums">{value}</p>
        {yoyChange !== null ? (
          <div
            className={`mt-1 flex items-center gap-1 text-sm font-medium ${
              isPositive
                ? 'text-green-600 dark:text-green-400'
                : isNegative
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-muted-foreground'
            }`}
          >
            {isPositive && <TrendingUp className="h-3.5 w-3.5" />}
            {isNegative && <TrendingDown className="h-3.5 w-3.5" />}
            <span>{yoyChange} vs last year</span>
          </div>
        ) : (
          <div className="mt-1 text-sm text-muted-foreground">No prior year data</div>
        )}
      </CardContent>
    </Card>
  )
}
