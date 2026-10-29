import { useCallback, useEffect, useState } from 'react';
import { Activity, ArrowUpRight, BookOpen, BrainCircuit, ChevronRight, FlaskConical, FolderClock, GitBranch, LoaderCircle, Plus, Radio, X, Zap } from 'lucide-react';
import type { Graph, Job, Model, RunDetail, RunItem } from './types';
import { api, errorMessage } from './api';
import { shortId } from './lib/format';
import { processJobUpdate } from './lib/jobUpdates';
import { Investigation } from './views/Investigation';
import { Archive } from './views/Archive';
import { ModelLab } from './views/ModelLab';
import { NewExperiment } from './components/NewExperiment';
import { Landing } from './views/Landing';
import { Badge, Empty, ErrorBox, Loading } from './components/Primitives';

type View = 'investigation' | 'archive' | 'models';
const navigation = [{ id: 'investigation' as const, label: 'Investigation', icon: Activity }, { id: 'archive' as const, label: 'Experiments', icon: FolderClock }, { id: 'models' as const, label: 'Model lab', icon: BrainCircuit }];
export default function App() {
  const [view, setView] = useState<View>('investigation');
  const [home, setHome] = useState(true);
  const [runs, setRuns] = useState<RunItem[]>([]), [models, setModels] = useState<Model[]>([]), [jobs, setJobs] = useState<Job[]>([]), [graph, setGraph] = useState<Graph | null>(null);
  const [selectedId, setSelectedId] = useState(''), [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true), [runLoading, setRunLoading] = useState(false), [error, setError] = useState(''), [runError, setRunError] = useState('');
  const [modal, setModal] = useState(false), [notice, setNotice] = useState<Job | null>(null), [refreshToken, setRefreshToken] = useState(0);
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }); }, [home, view]);
  const load = useCallback(async (signal?: AbortSignal) => {
    const [r, m, j, g] = await Promise.all([api<RunItem[]>('/runs', { signal }), api<Model[]>('/models', { signal }), api<Job[]>('/jobs', { signal }), api<Graph>('/topology', { signal })]);
    if (!signal?.aborted) { setRuns(r); setModels(m); setJobs(j); setGraph(g); setSelectedId(id => id || r[0]?.id || ''); }
  }, []);
  useEffect(() => { const controller = new AbortController(); setLoading(true); setError(''); load(controller.signal).catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); }); return () => controller.abort(); }, [load, refreshToken]);
  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController(); setRun(null); setRunLoading(true); setRunError('');
    api<RunDetail>(`/runs/${selectedId}`, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) setRun(value); }).catch(e => { if (!controller.signal.aborted) setRunError(errorMessage(e)); }).finally(() => { if (!controller.signal.aborted) setRunLoading(false); });
    return () => controller.abort();
  }, [selectedId, refreshToken]);
  useEffect(() => {
    const active = jobs.some(j => ['running','queued'].includes(j.status));
    if (!active && !notice) return;
    const controller = new AbortController();
    const timer = window.setInterval(async () => {
      try {
        const next = await api<Job[]>('/jobs', { signal: controller.signal });
        if (controller.signal.aborted) return;
        const update = await processJobUpdate(jobs,next,() => load(controller.signal),controller.signal);
        if (!update) return;
        setJobs(update);
        const current = notice && next.find(j => j.id === notice.id);
        if (current) {
          setNotice(current);
          if (current.status === 'completed') {
            await load(controller.signal);
            if (controller.signal.aborted) return;
            if (current.result?.run_id) { setSelectedId(current.result.run_id); setView('investigation'); }
            // Result lists are refreshed before a terminal state stops polling.
            setNotice(null);
          }
          if (current.status === 'failed') { setError(current.error || 'Job failed.'); setNotice(null); }
        } else if (!next.some(j => ['running','queued'].includes(j.status))) await load(controller.signal);
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
    }, 800);
    return () => { controller.abort(); clearInterval(timer); };
  }, [jobs.some(j => ['running','queued'].includes(j.status)), notice?.id, load]);
  function created(job: Job) { setModal(false); setNotice(job); setJobs(old => [job, ...old.filter(j => j.id !== job.id)]); }
  function open(id: string) { setSelectedId(id); setView('investigation'); }
  const activeJobs = jobs.filter(j => ['running','queued'].includes(j.status));
  if (home) return <Landing onOpenLab={() => { setView('investigation'); setHome(false); }} onOpenModels={() => { setView('models'); setHome(false); }}/>;
  return <div className="app-shell"><a className="skip-link" href="#main">Skip to content</a><aside className="sidebar"><a className="brand" href="#" onClick={e => { e.preventDefault(); setHome(true); }} aria-label="Faultline home"><span className="brand-mark"><Zap size={23} fill="currentColor"/></span><span>faultline<span className="brand-period">.</span></span></a><div className="workspace"><span className="workspace-icon"><GitBranch size={16}/></span><div><strong>Commerce sandbox</strong><span>Local workspace</span></div><Badge>01</Badge></div>
    <div className="nav-caption">WORKSPACE</div><nav aria-label="Main navigation">{navigation.map(item => <button key={item.id} className={`nav-item ${view === item.id ? 'active' : ''}`} onClick={() => setView(item.id)} aria-current={view === item.id ? 'page' : undefined}><item.icon size={18}/><span>{item.label}</span>{item.id === 'archive' && <small>{runs.length.toString().padStart(2,'0')}</small>}{item.id === view && <span className="nav-active-dot"/>}</button>)}</nav>
    <div className="sidebar-lab"><span className="outline-icon"><FlaskConical size={22}/></span><strong>Run an experiment</strong><p>Configure a simulated failure and compare its effects across services.</p><button onClick={() => setModal(true)}><Plus size={14}/>Create an experiment</button></div>
    <div className="sidebar-bottom"><button className="overview-link" onClick={() => setHome(true)}><BookOpen size={16}/>About Faultline</button><a href="/docs" target="_blank" rel="noreferrer"><BookOpen size={16}/>API documentation<ArrowUpRight size={13}/></a><div className="local-status"><span className="status-dot"/><span>LOCAL ENGINE</span><code>v0.1.0</code></div></div>
    </aside><div className="app-content"><header className="topbar"><div className="breadcrumbs"><span>Workspace</span><ChevronRight size={13}/><strong>{navigation.find(n => n.id === view)?.label}</strong></div><div className="topbar-right"><span><Radio size={13}/>Synthetic environment</span><span className="topbar-model"><BrainCircuit size={14}/>GRF-1</span><span className="avatar">FL</span></div></header>
    <main id="main"><div className="mobile-nav"><button onClick={() => setHome(true)}>About</button>{navigation.map(n => <button key={n.id} className={view === n.id ? 'active' : ''} onClick={() => setView(n.id)}><n.icon size={16}/>{n.label}</button>)}</div>
      {error && <ErrorBox message={error} onRetry={() => setRefreshToken(x => x+1)}/>}
      {activeJobs.length > 0 && <div className="job-banner" role="status"><LoaderCircle size={17} className="spin"/><span>{activeJobs[0].kind === 'train' ? 'Training a neural model' : activeJobs[0].kind === 'benchmark' ? 'Evaluating held-out scenarios' : 'Running your experiment'}<small>{activeJobs[0].status} · {Math.round(activeJobs[0].progress*100)}%</small></span><div className="progress-track"><i style={{ width: `${activeJobs[0].progress*100}%` }}/></div></div>}
      {loading ? <Loading/> : view === 'archive' ? <Archive runs={runs} jobs={jobs} onOpen={open} onNew={() => setModal(true)}/> : view === 'models' ? <ModelLab models={models} jobs={jobs} onJob={created}/> : runLoading ? <Loading text="Opening experiment…"/> : runError ? <ErrorBox message={runError} onRetry={() => setRefreshToken(x => x+1)}/> : run && run.id === selectedId && graph ? <Investigation key={run.id} run={run} runs={runs} graph={graph} onSelectRun={setSelectedId} onNew={() => setModal(true)}/> : !error ? <Empty title="Your laboratory is ready"><button className="button primary" onClick={() => setModal(true)}>Create your first experiment</button></Empty> : null}
    </main></div>{modal && <NewExperiment models={models} onClose={() => setModal(false)} onCreated={created}/>}
    {notice?.status === 'failed' && <div className="toast" role="alert">{notice.error}<button aria-label="Dismiss notification" onClick={() => setNotice(null)}><X size={15}/></button></div>}
    <div className="version-tag mono" aria-hidden="true">{models[0] ? `model ${shortId(models[0].id)}` : 'bootstrapping'}</div>
  </div>;
}
