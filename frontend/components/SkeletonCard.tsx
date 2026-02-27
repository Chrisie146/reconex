'use client'

/**
 * Shimmer skeleton placeholders for loading states.
 * Usage:
 *   <KPICardSkeleton />         — for the three top KPI cards
 *   <SkeletonBlock h="h-4" />   — generic rect shimmer
 */

function SkeletonBlock({ h = 'h-4', w = 'w-full', className = '' }: { h?: string; w?: string; className?: string }) {
  return (
    <div
      className={`${h} ${w} rounded bg-neutral-200 dark:bg-neutral-700 overflow-hidden relative ${className}`}
    >
      <div className="absolute inset-0 -translate-x-full animate-[shimmerSlide_1.6s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/50 dark:via-white/10 to-transparent" />
    </div>
  )
}

export function KPICardSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="card p-6 space-y-3">
          <SkeletonBlock h="h-3" w="w-1/2" />
          <SkeletonBlock h="h-8" w="w-3/4" />
        </div>
      ))}
    </div>
  )
}

export function ChartSkeleton({ height = 'h-56' }: { height?: string }) {
  return (
    <div className={`card p-6 ${height} flex flex-col gap-3`}>
      <SkeletonBlock h="h-3" w="w-1/3" />
      <div className="flex-1 flex items-end gap-2">
        {[60, 80, 45, 90, 70, 55, 85].map((pct, i) => (
          <div key={i} className="flex-1 flex flex-col justify-end">
            <div
              className="rounded bg-neutral-200 dark:bg-neutral-700 overflow-hidden relative"
              style={{ height: `${pct}%` }}
            >
              <div className="absolute inset-0 -translate-x-full animate-[shimmerSlide_1.6s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/50 dark:via-white/10 to-transparent" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default SkeletonBlock
