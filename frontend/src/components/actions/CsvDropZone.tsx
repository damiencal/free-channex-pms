import { useRef, useState } from 'react'
import { Upload, X, FileText } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export interface ImportResult {
  platform: string        // "airbnb" | "vrbo" | "mercury"
  filename: string
  inserted: number
  updated: number
  skipped: number
  inserted_ids: string[]
  updated_ids: string[]
}

type UploadState =
  | { phase: 'idle' }
  | { phase: 'file-selected'; file: File; platform: string | null }
  | { phase: 'uploading'; progress: number }
  | { phase: 'success'; result: ImportResult }
  | { phase: 'error'; message: string }

interface CsvDropZoneProps {
  onResult: (result: ImportResult | null, error: string | null) => void
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function uploadCsv(
  platform: string,
  file: File,
  onProgress: (pct: number) => void,
): Promise<ImportResult> {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append('file', file)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `/ingestion/${platform}/upload`)
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as ImportResult)
      } else {
        try {
          const body = JSON.parse(xhr.responseText) as { detail?: string }
          reject(new Error(
            typeof body.detail === 'string'
              ? body.detail
              : JSON.stringify(body.detail)
          ))
        } catch {
          reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`))
        }
      }
    }
    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.send(formData)
  })
}

export function CsvDropZone({ onResult }: CsvDropZoneProps) {
  const [state, setState] = useState<UploadState>({ phase: 'idle' })
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  function handleFileSelected(file: File) {
    setState({ phase: 'file-selected', file, platform: null })
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragOver(true)
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragOver(false)
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileSelected(file)
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFileSelected(file)
    // Reset input so same file can be re-selected if needed
    e.target.value = ''
  }

  function handleCancel() {
    setState({ phase: 'idle' })
  }

  async function handleUpload() {
    if (state.phase !== 'file-selected' || !state.platform) return
    const { file, platform } = state

    setState({ phase: 'uploading', progress: 0 })

    try {
      const result = await uploadCsv(platform, file, (pct) => {
        setState({ phase: 'uploading', progress: pct })
      })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['ingestion', 'history'] })
      setState({ phase: 'success', result })
      onResult(result, null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setState({ phase: 'error', message })
      onResult(null, message)
    }
  }

  // Idle state
  if (state.phase === 'idle') {
    return (
      <div
        className={`rounded-xl border-2 border-dashed p-8 flex flex-col items-center gap-3 cursor-pointer transition-colors select-none ${
          isDragOver
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/30 hover:border-muted-foreground/50 hover:bg-muted/30'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload className="h-8 w-8 text-muted-foreground" />
        <div className="text-center">
          <p className="text-sm font-medium">Drop CSV here or click to browse</p>
          <p className="text-xs text-muted-foreground mt-1">Airbnb, VRBO, or Mercury exports</p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleInputChange}
        />
      </div>
    )
  }

  // File-selected state
  if (state.phase === 'file-selected') {
    return (
      <div className="rounded-xl border bg-card p-4 shadow-sm space-y-4">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{state.file.name}</p>
            <p className="text-xs text-muted-foreground">{formatBytes(state.file.size)}</p>
          </div>
          <button
            className="text-muted-foreground hover:text-foreground transition-colors"
            onClick={handleCancel}
            aria-label="Cancel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs text-muted-foreground font-medium">Platform</label>
          <Select
            value={state.platform ?? ''}
            onValueChange={(value) =>
              setState({ phase: 'file-selected', file: state.file, platform: value })
            }
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select platform..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="airbnb">Airbnb</SelectItem>
              <SelectItem value="vrbo">VRBO</SelectItem>
              <SelectItem value="mercury">Mercury</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            disabled={!state.platform}
            onClick={() => void handleUpload()}
            className="flex-1"
          >
            Upload
          </Button>
          <Button size="sm" variant="ghost" onClick={handleCancel}>
            Cancel
          </Button>
        </div>
      </div>
    )
  }

  // Uploading state
  if (state.phase === 'uploading') {
    const isProcessing = state.progress >= 100
    return (
      <div className="rounded-xl border bg-card p-4 shadow-sm space-y-3">
        <p className="text-sm font-medium text-center">
          {isProcessing ? 'Processing...' : `Uploading... ${state.progress}%`}
        </p>
        <Progress value={state.progress} />
      </div>
    )
  }

  // Success/error states — delegated to parent via onResult; render nothing here
  return null
}
