import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

interface ReportSectionProps {
  title: string
  total: string
  children: React.ReactNode
  className?: string
}

export function ReportSection({ title, total, children, className }: ReportSectionProps) {
  const [open, setOpen] = useState(true)

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className={className}>
        <CardHeader className="pb-2">
          <CollapsibleTrigger asChild>
            <button className="flex w-full items-center justify-between">
              <CardTitle className="text-base">{title}</CardTitle>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold tabular-nums">{total}</span>
                {open ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </div>
            </button>
          </CollapsibleTrigger>
        </CardHeader>
        <CollapsibleContent>
          <CardContent>{children}</CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}
