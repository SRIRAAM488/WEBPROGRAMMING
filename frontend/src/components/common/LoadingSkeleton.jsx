/**
 * Loading skeletons - shown while data is being fetched.
 *
 * They mirror the real layout closely, so the page does not jump when the data
 * arrives (this is called "layout shift", and it feels janky).
 */

export function Skeleton({ width, height = 12, radius, className = '', style }) {
  return (
    <span
      className={`skeleton ${className}`}
      style={{
        display: 'block',
        width: width || '100%',
        height,
        borderRadius: radius,
        ...style,
      }}
      aria-hidden="true"
    />
  )
}

export function SkeletonText({ lines = 3, lastLineWidth = '60%' }) {
  return (
    <div>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          height={12}
          width={index === lines - 1 ? lastLineWidth : '100%'}
          className="skeleton--text"
        />
      ))}
    </div>
  )
}

export function SummaryCardSkeleton() {
  return (
    <div className="summary-card" aria-hidden="true">
      <div className="summary-card__top">
        <Skeleton width={40} height={40} radius={11} />
        <div style={{ flex: 1 }}>
          <Skeleton height={14} width="60%" className="skeleton--text" />
          <Skeleton height={10} width="80%" />
        </div>
      </div>
      <Skeleton height={30} width="55%" />
      <div className="summary-card__stats">
        <Skeleton height={10} width="100%" />
        <Skeleton height={10} width="85%" />
      </div>
    </div>
  )
}

export function CardSkeleton({ lines = 4, title = true }) {
  return (
    <div className="card" aria-hidden="true">
      <div className="card__header">
        <div style={{ flex: 1 }}>
          {title ? <Skeleton height={16} width="45%" className="skeleton--text" /> : null}
          <Skeleton height={10} width="65%" />
        </div>
      </div>
      <div className="card__body">
        <SkeletonText lines={lines} />
      </div>
    </div>
  )
}

export function RowSkeleton({ count = 4 }) {
  return (
    <div aria-hidden="true">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="item-row">
          <Skeleton width={38} height={38} radius={10} />
          <div style={{ flex: 1 }}>
            <Skeleton height={13} width={`${55 + (index % 3) * 12}%`} className="skeleton--text" />
            <Skeleton height={10} width="40%" />
          </div>
          <Skeleton width={64} height={22} radius={999} className="skeleton--pill" />
        </div>
      ))}
    </div>
  )
}

export function TableSkeleton({ rows = 5, columns = 5 }) {
  return (
    <div aria-hidden="true" style={{ padding: 'var(--sp-4)' }}>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${columns}, 1fr)`,
            gap: 'var(--sp-4)',
            alignItems: 'center',
            padding: '13px 0',
            borderBottom: rowIndex < rows - 1 ? '1px solid var(--border)' : 'none',
          }}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={colIndex}
              height={colIndex === 0 ? 13 : 11}
              width={colIndex === 0 ? '70%' : '55%'}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

export function ChartSkeleton({ height = 240 }) {
  return (
    <div
      aria-hidden="true"
      className="chart-box"
      style={{ height, display: 'flex', alignItems: 'flex-end', gap: 'var(--sp-3)', padding: 'var(--sp-4)' }}
    >
      {[55, 80, 40, 95, 65, 30, 72].map((percent, index) => (
        <Skeleton
          key={index}
          height={`${percent}%`}
          radius={8}
          style={{ flex: 1 }}
        />
      ))}
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <>
      <div className="grid grid--summary">
        {Array.from({ length: 4 }).map((_, index) => (
          <SummaryCardSkeleton key={index} />
        ))}
      </div>
      <div className="grid grid--dashboard">
        <div className="stack">
          <CardSkeleton lines={5} />
          <CardSkeleton lines={3} />
        </div>
        <div className="stack">
          <CardSkeleton lines={4} />
          <CardSkeleton lines={3} />
        </div>
      </div>
    </>
  )
}

/** Visible-to-screen-readers text while a skeleton is on screen. */
export function LoadingLabel({ children = 'Loading…' }) {
  return <span className="sr-only" role="status">{children}</span>
}