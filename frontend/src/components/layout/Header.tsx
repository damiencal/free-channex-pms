import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Moon, Sun, Menu } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { apiFetch } from '@/api/client'
import { usePropertyStore } from '@/store/usePropertyStore'
import { useAuth } from '@/store/useAuth'

interface Property {
  id: number
  slug: string
  display_name: string
}

const DARK_MODE_KEY = 'roost-dark-mode'

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
  const { logout } = useAuth()
  const [, setSearchParams] = useSearchParams()

  const { data: properties = [] } = useQuery<Property[]>({
    queryKey: ['dashboard', 'properties'],
    queryFn: () => apiFetch<Property[]>('/dashboard/properties'),
    staleTime: 5 * 60 * 1000,
  })

  return (
    <header className="border-b bg-card px-4 py-3 flex items-center justify-between gap-2">
      <div className="flex flex-col leading-tight shrink-0">
        <h1 className="text-lg font-bold">Roost</h1>
        <p className="text-xs text-muted-foreground">Rental Operations</p>
      </div>

      <div className="flex items-center gap-2 min-w-0">
        <Select
          value={selectedPropertyId === null ? 'all' : String(selectedPropertyId)}
          onValueChange={(val) =>
            setSelectedPropertyId(val === 'all' ? null : Number(val))
          }
        >
          <SelectTrigger className="w-36 sm:w-48">
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

        <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle dark mode" className="shrink-0">
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Menu" className="shrink-0">
              <Menu className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuItem onClick={() => setSearchParams({ tab: 'properties' })}>Properties</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSearchParams({ tab: 'automation' })}>Automation</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSearchParams({ tab: 'bookingsite' })}>Booking Site</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSearchParams({ tab: 'metrics' })}>Metrics</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSearchParams({ tab: 'accounts' })}>Connected Accounts</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSearchParams({ tab: 'settings' })}>Settings</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={logout}
            >
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
