import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { BookOpen, ExternalLink, Plus, Trash2, Eye, EyeOff, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'

export interface GuidebookSection {
  title: string
  body: string
  icon?: string
  order?: number
}

export interface Guidebook {
  id: number
  property_id: number
  title: string
  sections: GuidebookSection[]
  is_published: boolean
  created_at: string
  updated_at: string
}

function fetchGuidebook(propertyId: number): Promise<Guidebook> {
  return apiFetch<Guidebook>(`/guidebook/${propertyId}`)
}

function upsertGuidebook(
  propertyId: number,
  payload: { title: string; sections: GuidebookSection[]; is_published: boolean },
  existing?: Guidebook,
): Promise<Guidebook> {
  return apiFetch<Guidebook>(`/guidebook/${propertyId}`, {
    method: existing ? 'PUT' : 'POST',
    body: JSON.stringify(payload),
  })
}

// ---------------------------------------------------------------------------
// Section editor row
// ---------------------------------------------------------------------------

function SectionRow({
  section,
  onChange,
  onRemove,
}: {
  section: GuidebookSection
  idx?: number
  onChange: (s: GuidebookSection) => void
  onRemove: () => void
}) {
  return (
    <div className="border rounded-xl p-3 space-y-2 bg-card">
      <div className="grid grid-cols-3 gap-2">
        <div className="col-span-2 space-y-1">
          <Label className="text-xs">Section Title</Label>
          <Input
            value={section.title}
            onChange={(e) => onChange({ ...section, title: e.target.value })}
            placeholder="e.g. Check-in Instructions"
            className="h-8 text-sm"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Icon (emoji)</Label>
          <Input
            value={section.icon ?? ''}
            onChange={(e) => onChange({ ...section, icon: e.target.value })}
            placeholder="🔑"
            className="h-8 text-sm"
          />
        </div>
      </div>
      <div className="space-y-1">
        <Label className="text-xs">Content</Label>
        <Textarea
          value={section.body}
          onChange={(e) => onChange({ ...section, body: e.target.value })}
          className="text-sm min-h-[80px] resize-none"
          placeholder="Describe this section…"
        />
      </div>
      <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive h-7 px-2 text-xs" onClick={onRemove}>
        <Trash2 className="w-3 h-3 mr-1" /> Remove
      </Button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// GuidebooksTab
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Editor panel — only rendered once guidebook data (or absence thereof) is known
// Initialises local form state directly from props, no useEffect needed.
// ---------------------------------------------------------------------------

function EditorPanel({
  propertyId,
  existing,
  fetchError,
}: {
  propertyId: number
  existing: Guidebook | undefined
  fetchError: boolean
}) {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState(existing?.title ?? '')
  const [sections, setSections] = useState<GuidebookSection[]>(existing?.sections ?? [])
  const [isPublished, setIsPublished] = useState(existing?.is_published ?? false)

  const saveMutation = useMutation({
    mutationFn: () =>
      upsertGuidebook(propertyId, { title, sections, is_published: isPublished }, existing),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['guidebook'] }),
  })

  function addSection() {
    setSections((s) => [...s, { title: '', body: '', icon: '', order: s.length }])
  }

  function updateSection(idx: number, updated: GuidebookSection) {
    setSections((s) => s.map((sec, i) => (i === idx ? updated : sec)))
  }

  function removeSection(idx: number) {
    setSections((s) => s.filter((_, i) => i !== idx))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-semibold">Guest Guidebook</h2>
          <p className="text-sm text-muted-foreground">
            This guidebook is publicly accessible at{' '}
            <code className="text-xs bg-muted px-1 rounded">/public/guide/{'{property-slug}'}</code>
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsPublished((v) => !v)}
            className="gap-1.5"
          >
            {isPublished
              ? <><EyeOff className="w-3.5 h-3.5" /> Unpublish</>
              : <><Eye className="w-3.5 h-3.5" /> Publish</>}
          </Button>
          {existing && (
            <Button variant="outline" size="sm" asChild>
              <a href={`/public/guide/${propertyId}`} target="_blank" rel="noreferrer" className="gap-1.5">
                <ExternalLink className="w-3.5 h-3.5" /> Preview
              </a>
            </Button>
          )}
          <Button
            size="sm"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending || !title.trim()}
            className="gap-1.5"
          >
            <Save className="w-3.5 h-3.5" />
            {saveMutation.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Badge variant={isPublished ? 'default' : 'secondary'}>
          {isPublished ? 'Published' : 'Draft'}
        </Badge>
        {fetchError && <span className="text-xs text-muted-foreground">No guidebook yet — create one below</span>}
      </div>

      {saveMutation.isError && (
        <p className="text-sm text-destructive">
          {saveMutation.error instanceof Error ? saveMutation.error.message : 'Save failed'}
        </p>
      )}

      <div className="space-y-1">
        <Label>Guidebook Title</Label>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Welcome to your stay at…"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Sections</Label>
          <Button variant="outline" size="sm" onClick={addSection} className="gap-1.5 h-7 px-2 text-xs">
            <Plus className="w-3 h-3" /> Add Section
          </Button>
        </div>

        {sections.length === 0 ? (
          <div className="rounded-xl border-2 border-dashed p-8 text-center text-muted-foreground text-sm">
            No sections yet. Add one to get started.
          </div>
        ) : (
          <div className="space-y-2">
            {sections.map((sec, idx) => (
              <SectionRow
                key={idx}
                section={sec}
                onChange={(s) => updateSection(idx, s)}
                onRemove={() => removeSection(idx)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// GuidebooksTab
// ---------------------------------------------------------------------------

export function GuidebooksTab() {
  const { selectedPropertyId } = usePropertyStore()

  const { data: guidebook, isLoading, isError } = useQuery<Guidebook>({
    queryKey: ['guidebook', selectedPropertyId],
    queryFn: () => fetchGuidebook(selectedPropertyId!),
    enabled: selectedPropertyId != null,
    retry: false, // 404 means no guidebook yet — not an error we should retry
  })

  if (selectedPropertyId == null) {
    return (
      <div className="rounded-xl border-2 border-dashed p-12 text-center text-muted-foreground text-sm">
        <BookOpen className="w-10 h-10 opacity-30 mx-auto mb-2" />
        <p>Select a property to manage its guidebook.</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  // Use a key on EditorPanel so that switching properties re-mounts the editor,
  // resetting all local form state to the newly fetched guidebook.
  return (
    <EditorPanel
      key={selectedPropertyId}
      propertyId={selectedPropertyId}
      existing={guidebook}
      fetchError={isError}
    />
  )
}
