interface EmptyStateProps {
  title: string
  description?: string
}

/**
 * Reusable empty state: centered muted text, no icons or illustrations.
 * Used when a list or view has no data to display.
 */
export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-1">
      <p className="text-sm font-medium text-muted-foreground">{title}</p>
      {description && (
        <p className="text-xs text-muted-foreground/70">{description}</p>
      )}
    </div>
  )
}
