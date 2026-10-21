/**
 * AdherenceChart - the weekly "did I take my doses" bar chart.
 */

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ChartSkeleton } from '../common/LoadingSkeleton'
import EmptyState from '../common/EmptyState'

function AdherenceTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload

  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__label">{label}</div>
      <div className="chart-tooltip__row">
        <span className="chart-legend__swatch" style={{ background: 'var(--success)' }} aria-hidden="true" />
        Taken&nbsp;
        <span className="chart-tooltip__value">{point.taken}</span>
      </div>
      <div className="chart-tooltip__row">
        <span className="chart-legend__swatch" style={{ background: 'var(--text-faint)' }} aria-hidden="true" />
        Skipped&nbsp;
        <span className="chart-tooltip__value">{point.skipped}</span>
      </div>
      <div className="chart-tooltip__row">
        <span className="chart-legend__swatch" style={{ background: 'var(--danger)' }} aria-hidden="true" />
        Missed&nbsp;
        <span className="chart-tooltip__value">{point.missed}</span>
      </div>
      <div className="chart-tooltip__row" style={{ marginTop: 3 }}>
        Adherence&nbsp;
        <span className="chart-tooltip__value">{point.adherence_percent}%</span>
      </div>
    </div>
  )
}

export default function AdherenceChart({ data = [], loading = false, height = 240 }) {
  if (loading) return <ChartSkeleton height={height} />

  if (!data.some((point) => point.scheduled > 0)) {
    return (
      <EmptyState
        compact
        icon={<span aria-hidden="true">0%</span>}
        title="No doses scheduled in this period"
        description="Once you add a medication schedule, your weekly adherence will show here."
      />
    )
  }

  return (
    <div className="chart-box" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 4, left: -22, bottom: 0 }} barCategoryGap="22%">
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tickLine={false} axisLine={false} dy={4} />
          <YAxis tickLine={false} axisLine={false} width={38} allowDecimals={false} />
          <Tooltip content={<AdherenceTooltip />} cursor={{ fill: 'var(--surface-sunken)', opacity: 0.5 }} />
          <Legend
            verticalAlign="top"
            height={30}
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 'var(--fs-xs)' }}
          />
          <Bar dataKey="taken" name="Taken" stackId="doses" fill="var(--success)" radius={[0, 0, 0, 0]} maxBarSize={34} />
          <Bar dataKey="skipped" name="Skipped" stackId="doses" fill="var(--border-strong)" maxBarSize={34} />
          <Bar dataKey="missed" name="Missed" stackId="doses" fill="var(--danger)" radius={[5, 5, 0, 0]} maxBarSize={34} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}