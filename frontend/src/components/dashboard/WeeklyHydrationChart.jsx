/**
 * WeeklyHydrationChart - seven days of water intake from the database.
 *
 * The dashed goal line makes it obvious at a glance which days hit the target.
 */

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ChartSkeleton } from '../common/LoadingSkeleton'
import EmptyState from '../common/EmptyState'
import { formatMl } from '../../utils/format'

/** Matches the app's tooltip styling (defined in index.css). */
function ChartTooltip({ active, payload, label, goal }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload

  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__label">{label}</div>
      <div className="chart-tooltip__row">
        <span
          className="chart-legend__swatch"
          style={{ background: 'var(--aquahabit)' }}
          aria-hidden="true"
        />
        Consumed&nbsp;
        <span className="chart-tooltip__value">{formatMl(point.total_ml)}</span>
      </div>
      {goal ? (
        <div className="chart-tooltip__row" style={{ marginTop: 2 }}>
          Goal&nbsp;
          <span className="chart-tooltip__value">{formatMl(goal)}</span>
        </div>
      ) : null}
      <div className="chart-tooltip__row" style={{ marginTop: 2 }}>
        Entries&nbsp;
        <span className="chart-tooltip__value">{point.entry_count}</span>
      </div>
    </div>
  )
}

export default function WeeklyHydrationChart({ data = [], loading = false, height = 240 }) {
  if (loading) return <ChartSkeleton height={height} />

  const goal = data.find((point) => point.goal_ml)?.goal_ml || 0
  const hasAnyWater = data.some((point) => point.total_ml > 0)

  if (!hasAnyWater) {
    return (
      <EmptyState
        compact
        icon={<span aria-hidden="true">0</span>}
        title="No water logged this week"
        description="Log your first glass on the AquaHabit page and this chart will fill in."
      />
    )
  }

  return (
    <div className="stack stack--sm">
      <div className="chart-legend">
        <span className="chart-legend__item">
          <span className="chart-legend__swatch" style={{ background: 'var(--aquahabit)' }} />
          Water consumed
        </span>
        <span className="chart-legend__item">
          <span className="chart-legend__swatch chart-legend__swatch--line" style={{ background: 'var(--text-muted)' }} />
          Daily goal ({formatMl(goal)})
        </span>
      </div>

      <div className="chart-box" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, left: -18, bottom: 0 }} barCategoryGap="26%">
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={false} dy={4} />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={46}
              tickFormatter={(value) => (value >= 1000 ? `${value / 1000}L` : value)}
            />
            <Tooltip content={<ChartTooltip goal={goal} />} cursor={{ fill: 'var(--surface-sunken)', opacity: 0.5 }} />

            {goal > 0 ? (
              <ReferenceLine
                y={goal}
                stroke="var(--text-muted)"
                strokeDasharray="5 4"
                label={{
                  value: 'Goal',
                  position: 'insideTopRight',
                  fill: 'var(--text-muted)',
                  fontSize: 11,
                }}
              />
            ) : null}

            <Bar dataKey="total_ml" radius={[6, 6, 0, 0]} maxBarSize={42}>
              {data.map((point) => (
                <Cell
                  key={point.date}
                  fill={point.goal_reached ? 'var(--aquahabit)' : 'var(--aquahabit)'}
                  opacity={point.goal_reached ? 1 : 0.55}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}