import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'

interface Property {
  id: number
  slug: string
  display_name: string
}

const DARK_MODE_KEY = 'rental-dashboard-dark-mode'

function useDarkMode() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    const stored = localStorage.getItem(DARK_MODE_KEY)
    return stored === 'true'
  })

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem(DARK_MODE_KEY, String(isDark))
  }, [isDark])

  return { isDark, toggle: () => setIsDark((prev) => !prev) }
}

export function Header() {
  const { isDark, toggle } = useDarkMode()
  const { selectedPropertyId, setSelectedPropertyId } = usePropertyStore()

  const { data: properties = [] } = useQuery<Property[]>({
    queryKey: ['dashboard', 'properties'],
    queryFn: () => apiFetch<Property[]>('/dashboard/properties'),
    staleTime: 5 * 60 * 1000,
  })

  return (
    <header className="border-b bg-background px-4 py-3 flex items-center justify-between">
      <h1 className="text-lg font-semibold">Rental Dashboard</h1>

      <div className="flex items-center gap-3">
        <Select
          value={selectedPropertyId === null ? 'all' : String(selectedPropertyId)}
          onValueChange={(val) =>
            setSelectedPropertyId(val === 'all' ? null : Number(val))
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Properties" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Properties</SelectItem>
            {properties.map((p) => (
              <SelectItem key={p.id} value={String(p.id)}>
                {p.display_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle dark mode">
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  )
}
