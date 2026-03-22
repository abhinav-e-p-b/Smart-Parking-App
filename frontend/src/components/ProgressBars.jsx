export default function ProgressBars({ step, total = 3 }) {
  return (
    <div className="flex gap-1.5 mb-6">
      {Array.from({ length: total }, (_, i) => i + 1).map((n) => (
        <div
          key={n}
          className={`flex-1 h-[3px] rounded-full transition-all duration-500
            ${n < step ? 'bg-emerald-500' : n === step ? 'bg-blue-500' : 'bg-[#1E3550]'}`}
        />
      ))}
    </div>
  )
}