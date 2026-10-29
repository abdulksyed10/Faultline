import type { Job } from '../types';
const active = (job: Job) => job.status === 'queued' || job.status === 'running';
/** Refresh result lists before publishing the transition that can stop polling. */
export async function processJobUpdate(previous: Job[], next: Job[], refresh: () => Promise<void>, signal: AbortSignal): Promise<Job[] | null> {
  const finished = previous.some(old => active(old) && next.some(current => current.id === old.id && !active(current)));
  if (finished) await refresh();
  return signal.aborted ? null : next;
}
