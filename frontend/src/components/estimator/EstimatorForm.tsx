import { useState } from 'react'
import { Calculator } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { RevenueEstimate, EstimatorRequest } from '@/api/estimator'
import { useEstimator } from '@/hooks/useEstimator'

interface EstimatorFormProps {
  onResult: (result: RevenueEstimate) => void
}

export function EstimatorForm({ onResult }: EstimatorFormProps) {
  const { estimate, isLoading } = useEstimator()
  const [bedrooms, setBedrooms] = useState('2')
  const [propertyType, setPropertyType] = useState('house')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [monthsAhead, setMonthsAhead] = useState('12')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: EstimatorRequest = {
      bedrooms: parseInt(bedrooms),
      property_type: propertyType,
      latitude: latitude ? parseFloat(latitude) : null,
      longitude: longitude ? parseFloat(longitude) : null,
      months_ahead: parseInt(monthsAhead),
    }
    estimate(payload, { onSuccess: onResult })
  }

  return (
    <Card className="h-fit">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calculator className="h-5 w-5" />
          Property Details
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Bedrooms</Label>
            <Select value={bedrooms} onValueChange={setBedrooms}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[0, 1, 2, 3, 4, 5, 6].map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    {n === 0 ? 'Studio' : `${n} bedroom${n > 1 ? 's' : ''}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Property Type</Label>
            <Select value={propertyType} onValueChange={setPropertyType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="house">House</SelectItem>
                <SelectItem value="condo">Condo/Apartment</SelectItem>
                <SelectItem value="villa">Villa</SelectItem>
                <SelectItem value="cabin">Cabin</SelectItem>
                <SelectItem value="townhouse">Townhouse</SelectItem>
                <SelectItem value="cottage">Cottage</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Latitude (optional)</Label>
              <Input
                type="number"
                step="0.0001"
                min="-90"
                max="90"
                value={latitude}
                onChange={(e) => setLatitude(e.target.value)}
                placeholder="18.4696"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Longitude (optional)</Label>
              <Input
                type="number"
                step="0.0001"
                min="-180"
                max="180"
                value={longitude}
                onChange={(e) => setLongitude(e.target.value)}
                placeholder="-66.1057"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Projection Period</Label>
            <Select value={monthsAhead} onValueChange={setMonthsAhead}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="6">6 months</SelectItem>
                <SelectItem value="12">12 months</SelectItem>
                <SelectItem value="24">24 months</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Calculating…' : 'Calculate Revenue'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
