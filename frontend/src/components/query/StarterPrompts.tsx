import { Card, CardContent } from '@/components/ui/card'

const STARTER_QUESTIONS = [
  'How much did Jay make this month?',
  'Show me all Airbnb bookings in January 2026',
  'What were the top expenses last quarter?',
  'What is the occupancy rate for Minnie in 2025?',
]

interface StarterPromptsProps {
  onSelect: (prompt: string) => void
}

export function StarterPrompts({ onSelect }: StarterPromptsProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-2xl">
        <h2 className="mb-2 text-center text-xl font-semibold">
          Ask a question about your properties
        </h2>
        <p className="mb-8 text-center text-sm text-muted-foreground">
          I can answer questions about revenue, expenses, bookings, and occupancy.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {STARTER_QUESTIONS.map((question) => (
            <button
              key={question}
              onClick={() => onSelect(question)}
              className="text-left transition-colors"
            >
              <Card className="cursor-pointer py-4 hover:border-primary hover:bg-muted/50">
                <CardContent className="px-4 py-0 text-sm">
                  {question}
                </CardContent>
              </Card>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
