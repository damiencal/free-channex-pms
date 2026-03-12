import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp, TrendingDown, DollarSign, Calendar,
  LogIn, LogOut, Home, DoorOpen, BarChart3, ArrowUpDown,
} from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  fetchRealtimeStats, fetchMonthlyReports, fetchIncomeExpenses,
  type RealtimeStats, type MonthlyReport, type IncomeExpenseEntry,
} from '@/api/platform'
import { usePropertyStore } from '@/store/usePropertyStore'

// ── Sub-tabs ───────────────────────────────────────────────────────
type SubTab = 'overview' | 'realtime' | 'monthly' | 'income-expenses'
const SUB_TABS: { key: SubTab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'realtime', label: 'Real-time Statistics' },
  { key: 'monthly', label: 'Monthly Report' },
  { key: 'income-expenses', label: 'Income & Expenses' },
]

// ── Formatters ─────────────────────────────────────────────────────
function fmtCurrency(v: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v)
}

// ── Overview page ──────────────────────────────────────────────────
function OverviewSection({ stats, monthly, loading }: {
  stats: RealtimeStats | undefined
  monthly: MonthlyReport[]
  loading: boolean
}) {
  const totalIncome = monthly.reduce((s, m) => s + m.total_income, 0)
  const totalExpense = monthly.reduce((s, m) => s + m.total_expense, 0)
  const totalProfit = totalIncome - totalExpense
  const totalReservations = monthly.reduce((s, m) => s + m.reservations, 0)

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard label="Total Income" value={fmtCurrency(totalIncome)} icon={TrendingUp} color="text-emerald-600" loading={loading} />
        <SummaryCard label="Total Expenses" value={fmtCurrency(totalExpense)} icon={TrendingDown} color="text-red-500" loading={loading} />
        <SummaryCard label="Net Profit" value={fmtCurrency(totalProfit)} icon={DollarSign} color={totalProfit >= 0 ? 'text-emerald-600' : 'text-red-500'} loading={loading} />
        <SummaryCard label="Reservations" value={String(totalReservations)} icon={Calendar} color="text-blue-600" loading={loading} />
      </div>

      {/* Today snapshot */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MiniStat icon={LogIn} label="Check-ins Today" value={stats.check_ins_today} />
          <MiniStat icon={LogOut} label="Check-outs Today" value={stats.check_outs_today} />
          <MiniStat icon={Home} label="In-stay" value={stats.in_stay} />
          <MiniStat icon={DoorOpen} label="Vacant" value={stats.vacant} />
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value, icon: Icon, color, loading }: {
  label: string; value: string; icon: React.ElementType; color: string; loading: boolean
}) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${color}`} />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      {loading ? <Skeleton className="h-7 w-24" /> : <p className="text-xl font-bold">{value}</p>}
    </div>
  )
}

function MiniStat({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: number }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border p-3">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <div>
        <p className="text-lg font-bold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}

// ── Realtime section ───────────────────────────────────────────────
function RealtimeSection({ stats, loading }: { stats: RealtimeStats | undefined; loading: boolean }) {
  if (loading || !stats) {
    return <div className="space-y-3">{[0,1,2].map(i => <Skeleton key={i} className="h-16" />)}</div>
  }

  const tiles: { label: string; value: number | string; icon: React.ElementType }[] = [
    { label: 'Check-ins Today', value: stats.check_ins_today, icon: LogIn },
    { label: 'Check-outs Today', value: stats.check_outs_today, icon: LogOut },
    { label: 'Currently In-stay', value: stats.in_stay, icon: Home },
    { label: 'Vacant Properties', value: stats.vacant, icon: DoorOpen },
    { label: 'Occupancy Rate', value: `${Math.round(stats.occupancy_rate)}%`, icon: BarChart3 },
    { label: 'Total Properties', value: stats.total_properties, icon: Calendar },
    { label: 'Inquiries Today', value: stats.inquiries_today, icon: ArrowUpDown },
    { label: 'Bookings Today', value: stats.bookings_today, icon: Calendar },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {tiles.map(t => (
        <div key={t.label} className="rounded-xl border bg-card p-4 text-center">
          <t.icon className="h-5 w-5 mx-auto mb-2 text-muted-foreground" />
          <p className="text-2xl font-bold">{t.value}</p>
          <p className="text-xs text-muted-foreground">{t.label}</p>
        </div>
      ))}
    </div>
  )
}

// ── Monthly report table ───────────────────────────────────────────
function MonthlyTable({ reports, loading }: { reports: MonthlyReport[]; loading: boolean }) {
  if (loading) {
    return <div className="space-y-2">{[0,1,2].map(i => <Skeleton key={i} className="h-10" />)}</div>
  }
  if (reports.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No monthly reports available.</p>
  }
  return (
    <div className="rounded-xl border overflow-hidden">
      <div className="grid grid-cols-5 gap-2 px-4 py-2 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground font-medium">
        <span>Month</span>
        <span className="text-right">Reservations</span>
        <span className="text-right">Income</span>
        <span className="text-right">Expenses</span>
        <span className="text-right">Net Profit</span>
      </div>
      {reports.map(r => (
        <div key={r.month} className="grid grid-cols-5 gap-2 px-4 py-2.5 border-t items-center text-sm">
          <span className="font-medium">{r.month}</span>
          <span className="text-right">{r.reservations}</span>
          <span className="text-right text-emerald-600">{fmtCurrency(r.total_income)}</span>
          <span className="text-right text-red-500">{fmtCurrency(r.total_expense)}</span>
          <span className={`text-right font-medium ${r.net_profit >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {fmtCurrency(r.net_profit)}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Income & Expenses ledger ───────────────────────────────────────
function IncomeExpensesTable({ entries, loading }: { entries: IncomeExpenseEntry[]; loading: boolean }) {
  if (loading) {
    return <div className="space-y-2">{[0,1,2].map(i => <Skeleton key={i} className="h-10" />)}</div>
  }
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No income/expense entries.</p>
  }
  return (
    <div className="rounded-xl border overflow-hidden">
      <div className="grid grid-cols-7 gap-2 px-4 py-2 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground font-medium">
        <span className="col-span-2">Item</span>
        <span className="text-right">Amount</span>
        <span>Payment</span>
        <span>Channel</span>
        <span>Property</span>
        <span>Date</span>
      </div>
      {entries.map(e => (
        <div key={e.id} className="grid grid-cols-7 gap-2 px-4 py-2.5 border-t items-center text-sm">
          <span className="col-span-2 truncate font-medium">{e.item}</span>
          <span className={`text-right font-medium ${e.amount >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {fmtCurrency(e.amount)}
          </span>
          <span className="text-muted-foreground">{e.payment_method}</span>
          <span className="text-muted-foreground">{e.channel || '—'}</span>
          <span className="text-muted-foreground truncate">{e.property_name || '—'}</span>
          <span className="text-muted-foreground">{new Date(e.time).toLocaleDateString()}</span>
        </div>
      ))}
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────
export function MetricsTab() {
  const { selectedPropertyId } = usePropertyStore()
  const [subTab, setSubTab] = useState<SubTab>('overview')
  const [month, setMonth] = useState<string>('')

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['realtime-stats', selectedPropertyId],
    queryFn: () => fetchRealtimeStats(selectedPropertyId),
    staleTime: 30_000,
    enabled: subTab === 'overview' || subTab === 'realtime',
  })

  const { data: monthly = [], isLoading: loadingMonthly } = useQuery({
    queryKey: ['monthly-reports', selectedPropertyId],
    queryFn: () => fetchMonthlyReports(selectedPropertyId),
    staleTime: 5 * 60_000,
    enabled: subTab === 'overview' || subTab === 'monthly',
  })

  const { data: incomeExpenses = [], isLoading: loadingIE } = useQuery({
    queryKey: ['income-expenses', selectedPropertyId, month],
    queryFn: () => fetchIncomeExpenses({ property_id: selectedPropertyId, month: month || undefined }),
    staleTime: 60_000,
    enabled: subTab === 'income-expenses',
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="text-lg font-semibold">Metrics</h2>
        {subTab === 'income-expenses' && (
          <div className="flex items-center gap-2">
            <Select value={month || 'all'} onValueChange={v => setMonth(v === 'all' ? '' : v)}>
              <SelectTrigger className="w-40 h-8 text-sm">
                <SelectValue placeholder="All months" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All months</SelectItem>
                {monthly.map(m => <SelectItem key={m.month} value={m.month}>{m.month}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {/* Sub-tab bar */}
      <div className="flex gap-1 overflow-x-auto rounded-lg bg-muted p-1">
        {SUB_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setSubTab(t.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-all ${
              subTab === t.key ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {subTab === 'overview' && (
        <OverviewSection stats={stats} monthly={monthly} loading={loadingStats || loadingMonthly} />
      )}
      {subTab === 'realtime' && (
        <RealtimeSection stats={stats} loading={loadingStats} />
      )}
      {subTab === 'monthly' && (
        <MonthlyTable reports={monthly} loading={loadingMonthly} />
      )}
      {subTab === 'income-expenses' && (
        <IncomeExpensesTable entries={incomeExpenses} loading={loadingIE} />
      )}
    </div>
  )
}
