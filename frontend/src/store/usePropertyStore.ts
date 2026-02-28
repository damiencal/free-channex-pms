import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface PropertyStore {
  selectedPropertyId: number | null
  setSelectedPropertyId: (id: number | null) => void
}

export const usePropertyStore = create<PropertyStore>()(
  persist(
    (set) => ({
      selectedPropertyId: null,
      setSelectedPropertyId: (id) => set({ selectedPropertyId: id }),
    }),
    {
      name: 'rental-dashboard-property',
    }
  )
)
