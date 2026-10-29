import { useEffect, useRef, useState } from 'react';
import { ArrowRight, FlaskConical, X } from 'lucide-react';
import { api, errorMessage } from '../api';
import { serviceIds, serviceNames } from '../types';
import type { Job, Model, Preset, Scenario, ServiceId } from '../types';
import { ErrorBox } from './Primitives';
const initial: Scenario = { name: 'Database saturation experiment', seed: 42, steps: 240, traffic: 1, fault: { service: 'database', kind: 'saturation', start: 80, duration: 100, severity: 1.2 } };
export function NewExperiment({ models, onClose, onCreated }: { models: Model[]; onClose: () => void; onCreated: (job: Job) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [scenario, setScenario] = useState<Scenario>(initial);
  const [model, setModel] = useState(models[0]?.id || '');
  const [presets, setPresets] = useState<Preset[]>([]);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const key = useRef(crypto.randomUUID());
  useEffect(() => { const prior = document.activeElement as HTMLElement; dialog.current?.showModal(); const controller = new AbortController(); api<Preset[]>('/presets', { signal: controller.signal }).then(setPresets).catch(() => {}); return () => { controller.abort(); prior?.focus(); }; }, []);
  const update = (value: Partial<Scenario>) => { key.current = crypto.randomUUID(); setScenario(s => ({ ...s, ...value })); };
  const fault = scenario.fault;
  async function submit(e: React.FormEvent) { e.preventDefault(); setBusy(true); setError(''); try { const job = await api<Job>('/runs', { method: 'POST', headers: { 'Idempotency-Key': key.current }, body: JSON.stringify({ scenario, model_id: model }) }); onCreated(job); } catch (e) { setError(errorMessage(e)); setBusy(false); } }
  return <dialog ref={dialog} className="experiment-modal" onCancel={onClose} aria-labelledby="experiment-title"><form onSubmit={submit}><div className="modal-head"><div className="icon-tile"><FlaskConical size={23}/></div><button type="button" className="icon-button" aria-label="Close new experiment" onClick={onClose}><X size={20}/></button></div><div className="eyebrow">EXPERIMENT CONFIGURATION</div><h2 id="experiment-title">Configure an experiment</h2><p className="muted">Choose a service, failure mode, and workload to simulate.</p>
    <div className="preset-row">{presets.map(p => <button key={p.name} type="button" onClick={() => update({ ...initial, ...p.scenario, fault: p.scenario.fault ? { ...initial.fault!, ...p.scenario.fault } : null })}>{p.name}</button>)}</div>
    <label>Experiment name<input required maxLength={100} value={scenario.name} onChange={e => update({ name: e.target.value })}/></label>
    <div className="form-grid"><label>Target service<select value={fault?.service || 'healthy'} onChange={e => update({ fault: e.target.value === 'healthy' ? null : { ...(fault || initial.fault!), service: e.target.value as ServiceId } })}><option value="healthy">Healthy control / no fault</option>{serviceIds.map(s => <option key={s} value={s}>{serviceNames[s]}</option>)}</select></label><label>Failure mode<select disabled={!fault} value={fault?.kind || 'saturation'} onChange={e => fault && update({ fault: { ...fault, kind: e.target.value as NonNullable<Scenario['fault']>['kind'] } })}><option value="saturation">Resource saturation</option><option value="latency">Latency spike</option><option value="errors">Error burst</option></select></label></div>
    <div className="form-grid three"><label>Fault onset (s)<input type="number" disabled={!fault} required={!!fault} min={20} max={scenario.steps - (fault?.duration || 5)} value={fault?.start ?? 80} onChange={e => fault && update({ fault: { ...fault, start: +e.target.value } })}/></label><label>Duration (s)<input type="number" disabled={!fault} required={!!fault} min={5} max={scenario.steps - (fault?.start || 20)} value={fault?.duration ?? 100} onChange={e => fault && update({ fault: { ...fault, duration: +e.target.value } })}/></label><label>Seed<input type="number" required min={0} max={2147483647} value={scenario.seed} onChange={e => update({ seed: +e.target.value })}/></label></div>
    <div className="form-grid"><label>Fault severity <span className="value-label">{(fault?.severity || 1).toFixed(1)}×</span><input type="range" disabled={!fault} min="0.2" max="3" step="0.1" value={fault?.severity || 1} onChange={e => fault && update({ fault: { ...fault, severity: +e.target.value } })}/></label><label>Traffic multiplier <span className="value-label">{scenario.traffic.toFixed(1)}×</span><input type="range" min="0.5" max="2" step="0.1" value={scenario.traffic} onChange={e => update({ traffic: +e.target.value })}/></label></div>
    <label>Detector model<select value={model} onChange={e => { key.current = crypto.randomUUID(); setModel(e.target.value); }}>{models.map(m => <option key={m.id} value={m.id}>GRF-1 · {m.metadata.epochs} epochs · {m.id.slice(0,8)}</option>)}</select></label>
    {error && <ErrorBox message={error}/>}<div className="modal-footer"><span>240 simulation steps · reproducible seed</span><button className="button primary" disabled={busy || !model} type="submit">{busy ? 'Submitting…' : 'Launch experiment'}<ArrowRight size={16}/></button></div>
  </form></dialog>;
}
