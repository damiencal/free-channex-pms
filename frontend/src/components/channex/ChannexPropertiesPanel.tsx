import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Link2, Unlink, CheckCircle2, AlertCircle, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { ErrorAlert } from '@/components/shared/ErrorAlert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  fetchLocalChannexProperties,
  syncChannexProperties,
  linkChannexProperty,
  type LocalChannexProperty,
  type SyncResult,
} from '@/api/channex'
import { apiFetch } from '@/api/client'

interface LocalProperty {
  id: number
  slug: string
  display_name: string
}

const UNLINK_VALUE = '__unlink__'

function SyncResultBanner({ result, onDismiss }: { result: SyncResult; onDismiss: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg bg-muted px-4 py-3 text-sm">
      <div className="flex items-center gap-2 text-muted-foreground">
        <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
        <span>
          Sync complete — <strong>{result.upserted}</strong> properties pulled,{' '}
          <strong>{result.linked ?? 0}</strong> linked,{' '}
          <strong>{result.unlinked ?? 0}</strong> unlinked
        </span>
      </div>
      <Button variant="ghost" size="sm" onClick={onDismiss} className="shrink-0 h-7">
        Dismiss
      </Button>
    </div>
  )
}

function PropertyRow({
  row,
  localProperties,
}: {
  row: LocalChannexProperty
  localProperties: LocalProperty[]
}) {
  const queryClient = useQueryClient()
  const [selectValue, setSelectValue] = useState<string>(
    row.property_id != null ? String(row.property_id) : UNLINK_VALUE,
  )
  const [isDirty, setIsDirty] = useState(false)

  const linkMutation = useMutation({
    mutationFn: (propertyId: number | null) =>
      linkChannexProperty(row.channex_property_id, propertyId),
    onSuccess: () => {
      setIsDirty(false)
      void queryClient.invalidateQueries({ queryKey: ['channex', 'local-properties'] })
    },
  })

  function handleSelectChange(value: string) {
    setSelectValue(value)
    setIsDirty(value !== (row.property_id != null ? String(row.property_id) : UNLINK_VALUE))
  }

  function handleSave() {
    const propertyId = selectValue === UNLINK_VALUE ? null : parseInt(selectValue, 10)
    linkMutation.mutate(propertyId)
  }

  const isLinked = row.property_id != null

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 rounded-lg border bg-card px-4 py-3 shadow-sm">
      {/* Property info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm truncate">{row.channex_property_name}</span>
          {isLinked ? (
            <Badge variant="secondary" className="text-xs gap-1 shrink-0">
              <Link2 className="h-3 w-3" />
              {row.property_display_name}
            </Badge>
          ) : (
            <Badge variant="outline" className="text-xs gap-1 text-orange-600 border-orange-300 shrink-0">
              <Unlink className="h-3 w-3" />
              Unlinked
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
          <span className="font-mono truncate" title={row.channex_property_id}>
            {row.channex_property_id.slice(0, 8)}…
          </span>
          {row.synced_at && (
            <span className="flex items-center gap-1 shrink-0">
              <Clock className="h-3 w-3" />
              {new Date(row.synced_at).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>

      {/* Mapping controls */}
      <div className="flex items-center gap-2 shrink-0">
        <Select value={selectValue} onValueChange={handleSelectChange}>
          <SelectTrigger className="w-52 h-8 text-sm">
            <SelectValue placeholder="Select local property…" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={UNLINK_VALUE}>
              <span className="text-muted-foreground italic">— Unlinked —</span>
            </SelectItem>
            {localProperties.map((lp) => (
              <SelectItem key={lp.id} value={String(lp.id)}>
                {lp.display_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          size="sm"
          className="h-8"
          disabled={!isDirty || linkMutation.isPending}
          onClick={handleSave}
        >
          {linkMutation.isPending ? 'Saving…' : 'Save'}
        </Button>
      </div>

      {/* Inline error */}
      {linkMutation.isError && (
        <p className="text-xs text-destructive w-full">
          {linkMutation.error instanceof Error ? linkMutation.error.message : 'Save failed'}
        </p>
      )}
    </div>
  )
}

/**
 * Panel for listing locally-synced Channex properties and managing their
 * mapping to local property slugs.
 */
export function ChannexPropertiesPanel() {
  const queryClient = useQueryClient()
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)

  const { data: rows = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ['channex', 'local-properties'],
    queryFn: fetchLocalChannexProperties,
    staleTime: 60_000,
  })

  const { data: localProperties = [] } = useQuery<LocalProperty[]>({
    queryKey: ['dashboard', 'properties'],
    queryFn: () => apiFetch<LocalProperty[]>('/dashboard/properties'),
    staleTime: 5 * 60 * 1000,
  })

  const syncMutation = useMutation({
    mutationFn: syncChannexProperties,
    onSuccess: (result) => {
      setSyncResult(result)
      void queryClient.invalidateQueries({ queryKey: ['channex', 'local-properties'] })
    },
  })

  const linked = rows.filter((r) => r.property_id != null).length
  const unlinked = rows.length - linked

  return (
    <div className="rounded-xl border bg-card p-4 md:p-6 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Channex Properties</h2>
          <p className="text-sm text-muted-foreground">
            Map Channex listings to local properties. Run sync to pull the latest list from Channex.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="shrink-0 gap-2"
          disabled={syncMutation.isPending}
          onClick={() => syncMutation.mutate()}
        >
          <RefreshCw className={`h-4 w-4 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
          {syncMutation.isPending ? 'Syncing…' : 'Sync from Channex'}
        </Button>
      </div>

      {/* Sync error */}
      {syncMutation.isError && (
        <ErrorAlert
          message={
            syncMutation.error instanceof Error
              ? syncMutation.error.message
              : 'Sync failed'
          }
        />
      )}

      {/* Sync success banner */}
      {syncResult && (
        <SyncResultBanner result={syncResult} onDismiss={() => setSyncResult(null)} />
      )}

      <Separator />

      {/* Summary badges */}
      {rows.length > 0 && (
        <div className="flex gap-3 text-sm">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            {linked} linked
          </span>
          {unlinked > 0 && (
            <span className="flex items-center gap-1.5 text-orange-600">
              <AlertCircle className="h-4 w-4" />
              {unlinked} unlinked
            </span>
          )}
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <ErrorAlert
          message={error instanceof Error ? error.message : 'Failed to load properties.'}
          onRetry={() => void refetch()}
        />
      ) : rows.length === 0 ? (
        <div className="text-center py-8 text-sm text-muted-foreground">
          <p>No Channex properties synced yet.</p>
          <p className="mt-1">Click <strong>Sync from Channex</strong> to pull your properties.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {rows.map((row) => (
            <PropertyRow key={row.channex_property_id} row={row} localProperties={localProperties} />
          ))}
        </div>
      )}
    </div>
  )
}
