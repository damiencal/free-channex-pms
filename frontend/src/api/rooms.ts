import { apiFetch } from './client'

export interface RoomType {
  id: number
  property_id: number
  name: string
  code: string | null
  description: string | null
  max_occupancy: number | null
  base_rate: string
  min_stay: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Room {
  id: number
  property_id: number
  room_type_id: number | null
  name: string
  number: string | null
  floor: string | null
  building: string | null
  status: 'clean' | 'dirty' | 'maintenance' | 'out_of_order'
  is_active: boolean
  is_online: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface RoomTypePayload {
  property_id: number
  name: string
  code?: string | null
  description?: string | null
  max_occupancy?: number | null
  base_rate?: number
  min_stay?: number | null
  is_active?: boolean
}

export interface RoomPayload {
  property_id: number
  room_type_id?: number | null
  name: string
  number?: string | null
  floor?: string | null
  building?: string | null
  status?: Room['status']
  is_active?: boolean
  is_online?: boolean
  notes?: string | null
}

// Room Types
export const fetchRoomTypes = (property_id?: number | null): Promise<RoomType[]> => {
  const qs = property_id != null ? `?property_id=${property_id}` : ''
  return apiFetch<RoomType[]>(`/room-types${qs}`)
}
export const createRoomType = (payload: RoomTypePayload): Promise<RoomType> =>
  apiFetch<RoomType>('/room-types', { method: 'POST', body: JSON.stringify(payload) })
export const updateRoomType = (id: number, payload: Partial<RoomTypePayload>): Promise<RoomType> =>
  apiFetch<RoomType>(`/room-types/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteRoomType = (id: number): Promise<void> =>
  apiFetch<void>(`/room-types/${id}`, { method: 'DELETE' })

// Rooms
export const fetchRooms = (property_id?: number | null): Promise<Room[]> => {
  const qs = property_id != null ? `?property_id=${property_id}` : ''
  return apiFetch<Room[]>(`/rooms${qs}`)
}
export const createRoom = (payload: RoomPayload): Promise<Room> =>
  apiFetch<Room>('/rooms', { method: 'POST', body: JSON.stringify(payload) })
export const updateRoom = (id: number, payload: Partial<RoomPayload>): Promise<Room> =>
  apiFetch<Room>(`/rooms/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteRoom = (id: number): Promise<void> =>
  apiFetch<void>(`/rooms/${id}`, { method: 'DELETE' })
export const setRoomStatus = (id: number, status: Room['status']): Promise<Room> =>
  apiFetch<Room>(`/rooms/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) })
