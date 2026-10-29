export function extent(values: number[]): [number, number] {
  if (!values.length) return [0, 1];
  const max = Math.max(...values), min = Math.min(...values);
  return [Math.max(0, min - (max - min) * .15), Math.max(max * 1.12, min + 1)];
}
export function linePath(values: number[], width: number, height: number, [min, max]: [number, number]): string {
  return values.map((v, i) => `${i === 0 ? 'M' : 'L'}${(i * width / Math.max(1, values.length - 1)).toFixed(2)},${(height - (v - min) * height / (max - min)).toFixed(2)}`).join(' ');
}
export const timeLabel = (value: number) => `${Math.floor(value / 60).toString().padStart(2, '0')}:${Math.floor(value % 60).toString().padStart(2, '0')}`;
export const pct = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;
export const shortId = (value: string) => value.slice(0, 8);
export const dateLabel = (value: string) => new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(value));
