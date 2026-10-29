import { useId, useMemo } from 'react';
import { extent, linePath, timeLabel } from '../lib/format';
interface Series { name: string; values: number[]; color: string; dashed?: boolean }
export function Chart({ series, cursor, fault, unit = 'ms', compact = false }: { series: Series[]; cursor?: number; fault?: { start: number; duration: number } | null; unit?: string; compact?: boolean }) {
  const id = useId().replaceAll(':', '');
  const width = 840, height = compact ? 135 : 180;
  const range = useMemo(() => extent(series.flatMap(s => s.values)), [series]);
  const length = Math.max(1, ...series.map(s => s.values.length - 1));
  const paths = series.map(s => linePath(s.values, width, height, range));
  return <div className={`chart ${compact ? 'compact' : ''}`}><div className="chart-plot"><div className="y-labels">{[1, .5, 0].map(n => <span key={n}>{(range[0] + (range[1] - range[0]) * n).toFixed(unit === 'loss' ? 2 : 0)}</span>)}</div>
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={series.map(s => s.name).join(' versus ') + ` in ${unit}`} preserveAspectRatio="none">
      <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={series[0]?.color} stopOpacity=".16"/><stop offset="100%" stopColor={series[0]?.color} stopOpacity="0"/></linearGradient></defs>
      {[0, .5, 1].map(n => <line key={n} x1="0" x2={width} y1={n * height} y2={n * height} stroke="#272c38" strokeDasharray="3 5" />)}
      {fault && <rect x={fault.start / length * width} width={Math.min(fault.duration, length - fault.start) / length * width} height={height} fill="#f9836b" opacity=".04" />}
      {paths[0] && <path d={`${paths[0]} L${width},${height} L0,${height} Z`} fill={`url(#${id})`} />}
      {series.map((s, i) => <path key={s.name} d={paths[i]} stroke={s.color} strokeWidth="2" vectorEffect="non-scaling-stroke" fill="none" strokeDasharray={s.dashed ? '5 5' : undefined} />)}
      {cursor !== undefined && <line x1={cursor / length * width} x2={cursor / length * width} y1="0" y2={height} stroke="#b1b7c8" strokeDasharray="4 4" opacity=".65"/>}
    </svg></div><div className="x-labels">{[0, .25, .5, .75, 1].map(n => <span key={n}>{unit === 'loss' ? Math.round(n * length + 1) : timeLabel(n * length)}</span>)}</div><div className="chart-legend">{series.map(s => <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>)}<span className="chart-unit">{unit === 'loss' ? 'epoch / normalized MSE' : `${unit} · simulation time`}</span></div></div>;
}
