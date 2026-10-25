import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { Activity, Clock, FileCheck, AlertTriangle } from 'lucide-react'
import type { OpsStatus } from '@/types/api'

const COLORS = ['#0ea5e9', '#f43f5e', '#10b981', '#8b5cf6', '#64748b']

export default function MetricsDashboard() {
  const { data: ops } = useQuery({
    queryKey: ['ops-status'],
    queryFn: () => api.get<OpsStatus>('/v1/ops/status').then((r) => r.data),
    refetchInterval: 5000,
  })
  const { data: distribution } = useQuery({
    queryKey: ['doc-distribution'],
    queryFn: () => api.get('/v1/ops/distribution').then((r) => r.data),
    refetchInterval: 10000,
  })
  const { data: throughput } = useQuery({
    queryKey: ['throughput'],
    queryFn: () => api.get('/v1/ops/throughput').then((r) => r.data),
    refetchInterval: 10000,
  })

  const types = (distribution?.types || []) as { type: string; count: number }[]
  const history = (throughput?.history || []) as { time: string; count: number }[]

  const statCards = [
    { label: 'Throughput', value: ops?.throughput ?? 0, unit: 'docs/min', icon: Activity },
    { label: 'Accuracy', value: ops?.accuracy != null ? `${(ops.accuracy * 100).toFixed(1)}%` : '—', unit: 'Langfuse verdicts', icon: FileCheck },
    { label: 'Queue Depth', value: ops?.queue_depth ?? 0, unit: 'pending', icon: Clock },
    { label: 'Active Agents', value: ops?.active_agents ?? 0, unit: 'span names', icon: AlertTriangle },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Operations Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          /v1/ops snapshots derived from Langfuse runs{ops?.source ? ` (${ops.source})` : ''}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="border border-border rounded-lg p-4 bg-card">
              <div className="flex items-center gap-2 mb-2">
                <Icon className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">{stat.label}</span>
              </div>
              <p className="text-2xl font-semibold">{stat.value}</p>
              <p className="text-xs text-muted-foreground">{stat.unit}</p>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-border rounded-lg p-4 bg-card">
          <h3 className="text-sm font-medium mb-4">Throughput (last 24h)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#0ea5e9" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="border border-border rounded-lg p-4 bg-card">
          <h3 className="text-sm font-medium mb-4">Document type mix</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={types}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={4}
                dataKey="count"
                nameKey="type"
              >
                {types.map((row) => (
                  <Cell key={row.type} fill={COLORS[types.indexOf(row) % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
