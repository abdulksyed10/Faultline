import { LoaderCircle, AlertCircle } from 'lucide-react';
import type { ReactNode } from 'react';
export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) { return <span className={`badge ${tone}`}>{children}</span>; }
export function Empty({ title, children }: { title: string; children?: ReactNode }) { return <div className="empty"><div className="empty-glyph">↗</div><h2>{title}</h2><p>{children}</p></div>; }
export function Loading({ text = 'Loading the laboratory…' }: { text?: string }) { return <div className="loading" role="status"><LoaderCircle className="spin" size={22} />{text}</div>; }
export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) { return <div className="error-box" role="alert"><AlertCircle size={18} /><span>{message}</span>{onRetry && <button onClick={onRetry}>Retry</button>}</div>; }
export function SectionHeading({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) { return <div className="section-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2></div>{children}</div>; }
