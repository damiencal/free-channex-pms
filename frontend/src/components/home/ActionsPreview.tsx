import { useSearchParams } from 'react-router-dom'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useActions } from '@/hooks/useActions'

/**
 * Preview card showing pending action counts by type.
 * Clicking navigates to the Actions tab via URL search param.
 */
export function ActionsPreview() {
  const [, setSearchParams] = useSearchParams()
  const { data, isLoading } = useActions()

  function goToActions() {
    setSearchParams({ tab: 'actions' })
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-4 w-64" />
        </CardContent>
      </Card>
    )
  }

  const total = data?.total ?? 0
  const actions = data?.actions ?? []

  const resortForms = actions.filter((a) => a.type === 'resort_form').length
  const messages = actions.filter((a) => a.type === 'vrbo_message').length
  const unreconciled = actions.filter((a) => a.type === 'unreconciled').length

  if (total === 0) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 py-6">
          <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 shrink-0" />
          <p className="text-muted-foreground text-sm">All caught up — no pending actions</p>
        </CardContent>
      </Card>
    )
  }

  const parts: string[] = []
  if (resortForms > 0) parts.push(`${resortForms} resort form${resortForms > 1 ? 's' : ''}`)
  if (messages > 0) parts.push(`${messages} message${messages > 1 ? 's' : ''} to send`)
  if (unreconciled > 0) parts.push(`${unreconciled} unreconciled booking${unreconciled > 1 ? 's' : ''}`)

  const breakdown = parts.join(', ')

  return (
    <Card className="cursor-pointer transition-colors hover:bg-accent/30" onClick={goToActions}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
          {total} item{total > 1 ? 's' : ''} need attention
        </CardTitle>
      </CardHeader>
      <CardContent className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{breakdown}</p>
        <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); goToActions() }}>
          View all
        </Button>
      </CardContent>
    </Card>
  )
}
