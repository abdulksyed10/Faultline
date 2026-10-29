import { Database, Globe2, ShoppingBag, CreditCard, Boxes, Layers3, Zap, Server } from 'lucide-react';
import type { Graph, RunDetail, ServiceId } from '../types';
const icons = { gateway: Globe2, checkout: ShoppingBag, catalog: Layers3, payments: CreditCard, inventory: Boxes, orders: Server, cache: Zap, database: Database };
export function Topology({ graph, run, time, selected, onSelect }: { graph: Graph; run: RunDetail; time: number; selected: ServiceId; onSelect: (s: ServiceId) => void }) {
  const nodes = Object.fromEntries(graph.services.map(s => [s.id, s]));
  const state = (id: ServiceId) => {
    const m = run.result.services[id];
    if (m.scores[time] > 1) return 'origin';
    const initial = m.latency.slice(0, 20).reduce((a, b) => a + b, 0) / 20;
    return m.latency[time] > initial * 1.25 || m.errors[time] > 1 ? 'affected' : 'healthy';
  };
  return <div className="topology-scroll"><div className="topology"><div className="graph-layer layer-1">EDGE</div><div className="graph-layer layer-2">APPLICATION</div><div className="graph-layer layer-3">SERVICES</div><div className="graph-layer layer-4">DATA</div>
    <svg viewBox="0 0 850 410" className="graph-lines" aria-hidden="true"><defs><marker id="arrow" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5" fill="#565c6b"/></marker></defs>{graph.edges.map(edge => {
      const a = nodes[edge.source], b = nodes[edge.target]; const x = a.x + 64, end = b.x - 66, middle = (x + end) / 2;
      const active = state(edge.target) !== 'healthy';
      return <g key={`${edge.source}-${edge.target}`}><path d={`M${x},${a.y} C${middle},${a.y} ${middle},${b.y} ${end},${b.y}`} fill="none" stroke={active ? '#a76d56' : '#343b49'} strokeWidth="1.4" markerEnd="url(#arrow)"/><circle r="2.4" fill={active ? '#fb9d77' : '#7e889c'}><animateMotion dur="4s" repeatCount="indefinite" path={`M${x},${a.y} C${middle},${a.y} ${middle},${b.y} ${end},${b.y}`}/></circle></g>;
    })}</svg>
    {graph.services.map(service => { const Icon = icons[service.id], status = state(service.id); return <button key={service.id} className={`service-node ${status} ${selected === service.id ? 'selected' : ''}`} style={{ left: `${service.x / 850 * 100}%`, top: `${service.y / 410 * 100}%` }} onClick={() => onSelect(service.id)} aria-pressed={selected === service.id} aria-label={`${service.label}, ${status}, ${run.result.services[service.id].latency[time].toFixed(0)} milliseconds`}>
      <span className="node-top"><span className="node-icon"><Icon size={16}/></span><span className="status-dot"/></span><strong>{service.label}</strong><span className="node-bottom"><span>{run.result.services[service.id].latency[time].toFixed(0)}<small>ms</small></span><span>{status === 'origin' ? 'anomaly' : status === 'affected' ? 'affected' : 'normal'}</span></span>
    </button>; })}
  </div></div>;
}
