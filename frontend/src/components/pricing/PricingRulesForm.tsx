import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { usePropertyStore } from '@/store/usePropertyStore'
import { usePricingRule, useUpsertPricingRule } from '@/hooks/usePricing'
import type { PricingRulePayload } from '@/api/pricing'

type FormValues = {
  strategy: string
  min_price: string
  max_price: string
  weekend_markup_pct: string
  orphan_day_discount_pct: string
  last_minute_window_days: string
  last_minute_discount_pct: string
  early_bird_window_days: string
  early_bird_discount_pct: string
  demand_sensitivity: string
  min_stay: string
  weekend_min_stay: string
}

export function PricingRulesForm() {
  const propertyId = usePropertyStore((s) => s.selectedPropertyId)
  const { data: rule, isLoading } = usePricingRule(propertyId)
  const upsert = useUpsertPricingRule(propertyId)

  const { register, handleSubmit, reset, setValue, watch } = useForm<FormValues>({
    defaultValues: {
      strategy: 'dynamic',
      min_price: '',
      max_price: '',
      weekend_markup_pct: '15',
      orphan_day_discount_pct: '20',
      last_minute_window_days: '7',
      last_minute_discount_pct: '15',
      early_bird_window_days: '90',
      early_bird_discount_pct: '10',
      demand_sensitivity: '0.50',
      min_stay: '1',
      weekend_min_stay: '2',
    },
  })

  const strategy = watch('strategy')

  useEffect(() => {
    if (rule) {
      reset({
        strategy: rule.strategy,
        min_price: rule.min_price ? parseFloat(rule.min_price).toString() : '',
        max_price: rule.max_price ? parseFloat(rule.max_price).toString() : '',
        weekend_markup_pct: parseFloat(rule.weekend_markup_pct).toString(),
        orphan_day_discount_pct: parseFloat(rule.orphan_day_discount_pct).toString(),
        last_minute_window_days: rule.last_minute_window_days.toString(),
        last_minute_discount_pct: parseFloat(rule.last_minute_discount_pct).toString(),
        early_bird_window_days: rule.early_bird_window_days.toString(),
        early_bird_discount_pct: parseFloat(rule.early_bird_discount_pct).toString(),
        demand_sensitivity: parseFloat(rule.demand_sensitivity).toString(),
        min_stay: rule.min_stay.toString(),
        weekend_min_stay: rule.weekend_min_stay.toString(),
      })
    }
  }, [rule, reset])

  const onSubmit = (values: FormValues) => {
    const payload: PricingRulePayload = {
      strategy: values.strategy as 'manual' | 'dynamic' | 'hybrid',
      min_price: values.min_price ? parseFloat(values.min_price) : null,
      max_price: values.max_price ? parseFloat(values.max_price) : null,
      weekend_markup_pct: parseFloat(values.weekend_markup_pct),
      orphan_day_discount_pct: parseFloat(values.orphan_day_discount_pct),
      last_minute_window_days: parseInt(values.last_minute_window_days),
      last_minute_discount_pct: parseFloat(values.last_minute_discount_pct),
      early_bird_window_days: parseInt(values.early_bird_window_days),
      early_bird_discount_pct: parseFloat(values.early_bird_discount_pct),
      demand_sensitivity: parseFloat(values.demand_sensitivity),
      min_stay: parseInt(values.min_stay),
      weekend_min_stay: parseInt(values.weekend_min_stay),
    }
    upsert.mutate(payload)
  }

  if (!propertyId) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Select a property to configure pricing rules.
        </CardContent>
      </Card>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Pricing Strategy</CardTitle>
          <CardDescription>
            Control how prices are generated. Dynamic = fully automated. 
            Hybrid = automated with manual overrides. Manual = no automation.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Strategy</Label>
            <Select
              value={strategy}
              onValueChange={(v) => setValue('strategy', v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dynamic">Dynamic</SelectItem>
                <SelectItem value="hybrid">Hybrid</SelectItem>
                <SelectItem value="manual">Manual</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Min Price ($)</Label>
            <Input type="number" step="1" min="0" placeholder="No minimum" {...register('min_price')} />
          </div>

          <div className="space-y-1.5">
            <Label>Max Price ($)</Label>
            <Input type="number" step="1" min="0" placeholder="No maximum" {...register('max_price')} />
          </div>
        </CardContent>
      </Card>

      {strategy !== 'manual' && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Demand Modifiers</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label>Weekend Markup (%)</Label>
                <Input type="number" step="0.5" min="0" max="100" {...register('weekend_markup_pct')} />
              </div>
              <div className="space-y-1.5">
                <Label>Demand Sensitivity (0–1)</Label>
                <Input type="number" step="0.05" min="0" max="1" {...register('demand_sensitivity')} />
              </div>
              <div className="space-y-1.5">
                <Label>Orphan Day Discount (%)</Label>
                <Input type="number" step="0.5" min="0" max="80" {...register('orphan_day_discount_pct')} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Time-Based Discounts</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="space-y-1.5">
                <Label>Last-Minute Window (days)</Label>
                <Input type="number" step="1" min="1" max="30" {...register('last_minute_window_days')} />
              </div>
              <div className="space-y-1.5">
                <Label>Last-Minute Discount (%)</Label>
                <Input type="number" step="0.5" min="0" max="50" {...register('last_minute_discount_pct')} />
              </div>
              <div className="space-y-1.5">
                <Label>Early Bird Window (days)</Label>
                <Input type="number" step="1" min="30" max="365" {...register('early_bird_window_days')} />
              </div>
              <div className="space-y-1.5">
                <Label>Early Bird Discount (%)</Label>
                <Input type="number" step="0.5" min="0" max="30" {...register('early_bird_discount_pct')} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Min Stay Rules</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Default Min Stay (nights)</Label>
                <Input type="number" step="1" min="1" max="30" {...register('min_stay')} />
              </div>
              <div className="space-y-1.5">
                <Label>Weekend Min Stay (nights)</Label>
                <Input type="number" step="1" min="1" max="14" {...register('weekend_min_stay')} />
              </div>
            </CardContent>
          </Card>
        </>
      )}

      <Button type="submit" disabled={upsert.isPending || isLoading}>
        <Save className="mr-2 h-4 w-4" />
        {upsert.isPending ? 'Saving…' : 'Save Rules'}
      </Button>

      {upsert.isSuccess && (
        <p className="text-sm text-green-600 dark:text-green-400">Pricing rules saved.</p>
      )}
    </form>
  )
}
