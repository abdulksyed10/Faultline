import { describe, expect, it } from 'vitest';
import { extent, linePath, timeLabel } from './format';
describe('chart geometry', () => {
  it('keeps a nonzero scale for empty and constant series', () => {
    expect(extent([])).toEqual([0, 1]);
    const [min, max] = extent([4, 4, 4]);
    expect(max).toBeGreaterThan(min);
    expect(min).toBeLessThanOrEqual(4);
  });
  it('places first and last samples at exact horizontal boundaries', () => {
    expect(linePath([0, 10], 100, 50, [0, 10])).toBe('M0.00,50.00 L100.00,0.00');
    expect(linePath([], 100, 50, [0, 1])).toBe('');
  });
  it('formats simulation time independently of wall clock', () => {
    expect(timeLabel(0)).toBe('00:00');
    expect(timeLabel(125)).toBe('02:05');
  });
});
