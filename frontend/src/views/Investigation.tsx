import { useEffect, useRef, useState } from 'react';
import { Activity, ArrowDownRight, ArrowRight, Check, ChevronRight, Clock3, Download, FlaskConical, GitBranch, Info, Pause, Play, RotateCcw, ScanLine, ShieldCheck, Sparkles } from 'lucide-react';
import { post, errorMessage } from '../api';
import { serviceNames } from '../types';
import type { Graph, Replay, RunDetail, RunItem, ServiceId } from '../types';
import { timeLabel } from '../lib/format';
import { Badge, ErrorBox, SectionHeading } from '../components/Primitives';
import { Topology } from '../components/Topology';
import { Chart } from '../components/Chart';

export function Investigation({ run, runs, graph, onSelectRun, onNew }: { run: RunDetail; runs: RunItem[]; graph: Graph; onSelectRun: (id: string) => void; onNew: () => void }) {
  const [time, setTime] = useState(Math.min(run.scenario.steps - 1, (run.scenario.fault?.start ?? 80) + 35));
  const [playing, setPlaying] = useState(false);
  const [selected, setSelected] = useState<ServiceId>('gateway');
  const [metric, setMetric] = useState<'latency' | 'cpu' | 'errors' | 'scores'>('latency');
  const diagnosis = run.result.diagnosis, root = diagnosis.root_service;
  const [repairService, setRepairService] = useState<ServiceId>(root || 'database');
  const [repairAt, setRepairAt] = useState(Math.min(run.scenario.steps - 1, (diagnosis.onset ?? 80) + 35));
  const [replay, setReplay] = useState<Replay | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => { if (!playing) return; const timer = window.setInterval(() => setTime(t => { if (t >= run.scenario.steps - 1) { setPlaying(false); return t; } return t + 1; }), 250); return () => clearInterval(timer); }, [playing, run.scenario.steps]);
  function invalidateReplay() { request.current?.abort(); setReplay(null); setBusy(false); setError(''); }
  async function simulateRepair() {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setBusy(true); setError(''); setReplay(null);
    try { const value = await post<Replay>(`/runs/${run.id}/replay`, { service: repairService, at: repairAt }, controller.signal); if (!controller.signal.aborted) setReplay(value); }
    catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  const series = run.result.services[selected];
  const observed = series[metric];
  const units = metric === 'latency' ? 'ms' : metric === 'scores' ? '× threshold' : '%';
  const chartSeries = [{ name: serviceNames[selected], values: observed, color: '#f78e73' }];
  if (metric === 'latency' && selected === 'gateway') chartSeries.push({ name: 'Healthy simulator reference', values: run.result.simulator_reference.gateway_latency, color: '#626e89' });
  const affected = root ? diagnosis.ranking.find(r => r.service === root)?.callers.length ?? 0 : 0;
  return <>
    <div className="page-title"><div><div className="eyebrow"><span className="tiny-square"/> THE INCIDENT LABORATORY</div><h1>Incident investigation</h1><p>Review service telemetry, inspect the diagnosis, and compare a repair.</p></div><button className="button primary" onClick={onNew}><FlaskConical size={17}/>New experiment</button></div>
    <div className="experiment-bar"><div className="experiment-select"><span className="mini-icon"><GitBranch size={18}/></span><div><span className="micro-label">ACTIVE EXPERIMENT</span><select aria-label="Active experiment" value={run.id} onChange={e => onSelectRun(e.target.value)}>{runs.map(r => <option key={r.id} value={r.id}>{r.scenario.name}</option>)}</select></div></div><div className="experiment-meta"><Badge tone={root ? 'coral' : 'violet'}><span className="status-dot"/>{root ? 'Incident detected' : 'Inconclusive'}</Badge><span className="mono">seed {run.scenario.seed}</span><span className="separator"/><span>{run.scenario.steps}s capture</span><a className="icon-button" href={`/api/runs/${run.id}/report`} title="Download investigation report" aria-label="Download investigation report"><Download size={17}/></a></div></div>
    {run.result.quality?.status !== 'within-support' && <div className="error-box" role="status"><Info size={18}/><span>{run.result.quality?.message ?? 'Archived analysis predates workload support checks. Create a new experiment with a newly trained model before interpreting its origin diagnosis.'}</span></div>}
    <div className="stats-grid"><div className="stat-card"><span><Activity size={15}/>Peak gateway latency</span><strong>{run.result.summary.peak_gateway_latency.toFixed(0)}<small>ms</small></strong><p>Observed across the experiment</p><svg viewBox="0 0 100 25" className="stat-spark" aria-hidden="true"><path d="M0 23 10 22 18 24 28 21 32 4 40 6 48 2 58 8 64 5 72 4 76 23 90 21 100 23"/></svg></div>
    <div className="stat-card"><span><ScanLine size={15}/>Likely failure origin</span><strong className="text-value">{root ? serviceNames[root] : 'Inconclusive'}</strong><p><span className={root ? 'coral-text' : 'muted'}>{root ? 'Local residual evidence' : run.result.quality?.status === 'within-support' ? 'No sustained local signal' : 'Origin diagnosis withheld'}</span></p></div>
    <div className="stat-card"><span><GitBranch size={15}/>Potential blast radius</span><strong>{affected}<small>services</small></strong><p>Reachable callers of the likely origin</p></div>
    <div className="stat-card"><span><Clock3 size={15}/>Signal onset</span><strong>{diagnosis.onset !== null ? timeLabel(diagnosis.onset) : '—'}<small>{root ? 't+' : ''}</small></strong><p>Three consecutive threshold exceedances</p></div></div>
    <div className="investigation-grid"><div className="main-column"><section className="panel graph-panel"><SectionHeading title="System topology"><div className="panel-tools"><Badge>commerce / sandbox</Badge><span className="mono snapshot">t+{timeLabel(time)}</span></div></SectionHeading><div className="panel-subtitle">Select a service to inspect its telemetry at the current time.</div>
      <Topology graph={graph} run={run} time={time} selected={selected} onSelect={setSelected}/>
      <div className="graph-footer"><div className="legend"><span><i className="green-bg"/>Normal</span><span><i className="amber-bg"/>Affected</span><span><i className="coral-bg"/>Local anomaly</span></div><span className="graph-hint">Requests flow → · effects travel ←</span></div>
      <div className="playback"><button className="icon-button play-button" aria-label={playing ? 'Pause replay' : 'Play replay'} onClick={() => { if (time === run.scenario.steps - 1) setTime(0); setPlaying(p => !p); }}>{playing ? <Pause size={15}/> : <Play size={15}/>}</button><span className="mono">{timeLabel(time)}</span><input aria-label="Simulation timeline" type="range" min="0" max={run.scenario.steps - 1} value={time} onChange={e => { setPlaying(false); setTime(+e.target.value); }}/><span className="mono muted">{timeLabel(run.scenario.steps - 1)}</span><Badge>4×</Badge><button className="icon-button" aria-label="Reset replay" onClick={() => { setPlaying(false); setTime(0); }}><RotateCcw size={14}/></button></div>
    </section>
    <section className="panel telemetry-panel"><SectionHeading eyebrow="TELEMETRY" title={serviceNames[selected]}><div className="segmented" aria-label="Metric">{(['latency', 'cpu', 'errors', 'scores'] as const).map(m => <button key={m} aria-pressed={metric === m} className={m === metric ? 'active' : ''} onClick={() => setMetric(m)}>{m === 'scores' ? 'Anomaly' : m === 'cpu' ? 'CPU' : m[0].toUpperCase()+m.slice(1)}</button>)}</div></SectionHeading><div className="metric-now"><strong>{observed[time].toFixed(metric === 'errors' ? 2 : 1)}<small>{units}</small></strong><span>at t+{timeLabel(time)}</span></div><Chart series={chartSeries} cursor={time} fault={run.scenario.fault} unit={units}/><div className="panel-note"><Info size={13}/>{metric === 'scores' ? '1× is the empirical threshold. A sustained signal requires three consecutive points above it.' : 'All signals are generated by a seeded structural simulator. The healthy reference is excluded from diagnosis.'}</div></section>
    </div>
    <aside className="side-column"><section className="panel diagnosis-panel"><SectionHeading title="Diagnosis evidence"><span className="model-icon"><Sparkles size={17}/></span></SectionHeading><div className="diagnosis-intro"><Badge tone="violet">GRF-1 / NUMPY</Badge><p>Known-graph inversion separates inherited effects; a neural forecaster scores the remaining local deviations.</p></div>
    <div className="evidence-list">{diagnosis.ranking.slice(0,4).map((r, i) => <button key={r.service} onClick={() => setSelected(r.service)} className={`evidence-row ${i === 0 && r.flagged ? 'leading' : ''}`}><span className="rank">{String(i+1).padStart(2,'0')}</span><span className="evidence-info"><strong>{serviceNames[r.service]}</strong><span>{r.flagged ? `Signal at ${timeLabel(r.onset!)}` : 'Below sustained threshold'}</span><span className="evidence-track"><i style={{ width: `${Math.max(2,Math.min(100,r.evidence / Math.max(1,diagnosis.ranking[0].evidence)*100))}%` }}/></span></span><span className="evidence-value">{r.evidence.toFixed(1)}<small>×</small></span></button>)}</div>
    <div className="evidence-explainer"><ShieldCheck size={16}/><p>Diagnosis reads telemetry and topology only. Injected fault labels are held back.</p></div><p className="fine-print">Evidence is a residual ratio, not a causal probability. On this known graph, an inherited latency spike can coexist with low local evidence.</p></section>
    <section className="panel repair-panel"><div className="repair-kicker"><FlaskConical size={16}/>REPAIR REPLAY</div><h2>Compare a repair.</h2><p>Repair one service. Replay the same workload. Measure what changes.</p><label>Repair service<select aria-label="Repair service" value={repairService} onChange={e => { invalidateReplay(); setRepairService(e.target.value as ServiceId); }}>{graph.services.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}</select></label><label>Repair at <span className="value-label mono">t+{timeLabel(repairAt)}</span><input aria-label="Repair time" type="range" min="0" max={run.scenario.steps - 1} value={repairAt} onChange={e => { invalidateReplay(); setRepairAt(+e.target.value); }}/></label><button className="button repair-button" disabled={busy} onClick={simulateRepair}>{busy ? 'Replaying…' : replay ? 'Replay again' : 'Simulate repair'}<ArrowRight size={16}/></button>{error && <ErrorBox message={error}/>}
    {replay && <div className="repair-result" role="status"><span><Check size={14}/>Same seed · same workload</span><strong>{replay.latency_reduction_pct.toFixed(1)}%<ArrowDownRight size={24}/></strong><p>lower mean gateway latency after t+{timeLabel(repairAt)}</p><div className="repair-comparison"><span>{replay.observed_mean_ms.toFixed(1)}ms</span><ChevronRight size={14}/><b>{replay.replayed_mean_ms.toFixed(1)}ms</b></div></div>}
    <div className="fine-print">Simulator intervention removes the selected service’s injected fault. Results depend on this structural model.</div></section></aside></div>
    {replay && <section className="panel replay-chart"><SectionHeading eyebrow="PAIRED EXPERIMENT" title="Observed and replayed gateway latency"><Badge tone="green">repair at {timeLabel(replay.repair.at)}</Badge></SectionHeading><Chart series={[{ name:'Observed gateway', values:replay.observed, color:'#f78e73' },{ name:'Gateway after repair', values:replay.replayed, color:'#6fcda5' }]} fault={run.scenario.fault} cursor={replay.repair.at}/></section>}
    <div className="footnote"><span><span className="status-dot"/>Local laboratory · no external model APIs</span><span>Learn → Detect → Investigate → Replay</span></div>
  </>;
}
