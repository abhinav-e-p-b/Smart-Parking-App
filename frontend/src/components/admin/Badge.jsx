const styles = {
  inside:  'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
  exited:  'bg-slate-500/20   text-slate-400   border border-slate-500/30',
  online:  'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
  offline: 'bg-red-500/10     text-red-400     border border-red-500/30',
  flagged: 'bg-orange-500/10  text-orange-400  border border-orange-500/30',
}

export default function Badge({ type, children }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${styles[type] ?? ''}`}>
      {children}
    </span>
  )
}