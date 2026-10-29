export type ServiceId = 'gateway' | 'checkout' | 'catalog' | 'payments' | 'inventory' | 'orders' | 'cache' | 'database';
export const serviceIds: ServiceId[] = ['gateway', 'checkout', 'catalog', 'payments', 'inventory', 'orders', 'cache', 'database'];
export const serviceNames: Record<ServiceId, string> = { gateway: 'API Gateway', checkout: 'Checkout', catalog: 'Catalog', payments: 'Payments', inventory: 'Inventory', orders: 'Orders', cache: 'Redis Cache', database: 'Postgres' };
export interface Fault { service: ServiceId; kind: 'latency' | 'saturation' | 'errors'; start: number; duration: number; severity: number }
export interface Scenario { name: string; seed: number; steps: number; traffic: number; fault: Fault | null }
export interface Summary { peak_gateway_latency: number; mean_gateway_latency: number; flagged_services: number; steps: number }
export interface RunItem { id: string; model_id: string; scenario: Scenario; result: Summary; created_at: string }
export interface Evidence { service: ServiceId; evidence: number; onset: number | null; peak_score: number; tail_probability: number; callers: ServiceId[]; flagged: boolean }
export interface ServiceMetrics { latency: number[]; cpu: number[]; errors: number[]; requests: number[]; scores: number[]; peak_latency: number; mean_latency: number }
export interface Analysis { timeline: number[]; services: Record<ServiceId, ServiceMetrics>; quality?: {status: 'within-support' | 'outside-support' | 'unknown'; outside_fraction: number | null; message: string}; diagnosis: { status: 'detected' | 'inconclusive'; root_service: ServiceId | null; onset: number | null; ranking: Evidence[]; method: string; caveat: string }; summary: Summary; model: ModelMetadata; simulator_reference: { gateway_latency: number[]; label: string } }
export interface RunDetail extends Omit<RunItem, 'result'> { job_id: string; result: Analysis }
export interface ModelMetadata { name: string; version: string; seed: number; epochs: number; architecture: number[]; parameter_count: number; train_seeds: number[]; validation_seeds: number[]; calibration_seeds: number[]; training_samples: number; calibration_samples: number; data_fingerprint: string; curve: { epoch: number; loss: number; validation_loss: number }[]; created_at: string; calibration: string; limits: string }
export interface Model { id: string; sha256: string; metadata: ModelMetadata; created_at: string }
export interface BenchmarkMetrics { detection_recall: number; top1_accuracy: number; false_positive_rate: number; mean_detection_delay: number | null; latency_mae_ms: number; detected_count: number; localized_count: number; healthy_points: number; false_positive_points: number }
export interface Benchmark { model_id: string; seeds: number[]; case_count: number; metrics: { neural: BenchmarkMetrics; ewma: BenchmarkMetrics }; limits: string }
export interface Job { id: string; kind: 'train' | 'run' | 'benchmark'; status: 'queued' | 'running' | 'completed' | 'failed'; progress: number; error: string | null; result: ({ run_id?: string; model_id?: string } & Partial<Benchmark>) | null; created_at: string }
export interface Graph { services: { id: ServiceId; label: string; role: string; x: number; y: number }[]; edges: { source: ServiceId; target: ServiceId; weight: number }[]; semantics: string }
export interface Replay { repair: { service: ServiceId; at: number }; observed: number[]; replayed: number[]; latency_reduction_pct: number; observed_mean_ms: number; replayed_mean_ms: number; window: { start: number; end: number }; semantics: string }
export interface Preset { name: string; description: string; scenario: Partial<Scenario> }
