import type { PipelineQueue } from '@/types/api'

const ORDER = ['inbox', 'processing', 'classified', 'review', 'failed', 'archive'] as const

export default function ConveyorAnimation({ queue }: { queue: PipelineQueue }) {
  const total = ORDER.reduce((sum, key) => sum + (queue[key]?.length || 0), 0)
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground mb-3">
        Bin occupancy from Langfuse runs ({total} in window)
      </p>
      <div className="flex items-end gap-2 h-16">
        {ORDER.map((key) => {
          const count = queue[key]?.length || 0
          const height = total ? Math.max(8, Math.round((count / total) * 56)) : 8
          return (
            <div key={key} className="flex-1 flex flex-col items-center gap-1">
              <div
                className="w-full rounded-sm bg-primary/70"
                style={{ height }}
                title={`${key}: ${count}`}
              />
              <span className="text-[10px] text-muted-foreground capitalize">{key}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
