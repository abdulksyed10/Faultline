import { describe, it, expect } from 'vitest';
import type { Job } from '../types';
import { processJobUpdate } from './jobUpdates';
const active: Job = { id:'job',kind:'train',status:'running',progress:.5,error:null,result:null,created_at:'2026-10-29' };
const completed: Job = { ...active,status:'completed',progress:1,result:{model_id:'new-model'} };
describe('job completion across a reloaded app', () => {
  it('does not release terminal state until delayed result lists refresh', async () => {
    let finish!: () => void;
    let refreshed = false, released = false;
    const pending = processJobUpdate([active],[completed],async () => { await new Promise<void>(resolve => { finish = resolve; }); refreshed = true; },new AbortController().signal).then(jobs => { released = true; return jobs; });
    await Promise.resolve();
    expect(released).toBe(false);
    finish();
    expect(await pending).toEqual([completed]);
    expect(refreshed).toBe(true);
  });
  it('ignores a response cancelled during refresh', async () => {
    const controller = new AbortController();
    const result = await processJobUpdate([active],[completed],async () => { controller.abort(); },controller.signal);
    expect(result).toBeNull();
  });
});
