const STEPS = ['Details', 'Payment', 'Confirm']

export default function StepIndicator({ step }) {
  return (
    <div className="flex items-center mb-6">
      {STEPS.map((label, i) => {
        const n = i + 1
        const isDone   = n < step
        const isActive = n === step
        return (
          <div key={n} className="flex items-center">
            {/* Circle + label */}
            <div className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[12px] font-semibold border-[1.5px] transition-all
                ${isDone   ? 'bg-emerald-500 border-emerald-500 text-[#0D1B2A]' :
                  isActive ? 'bg-blue-600 border-blue-600 text-white' :
                             'bg-transparent border-[#1E3550] text-[#8DA4BF]'}`}>
                {isDone ? '✓' : n}
              </div>
              <span className={`text-[12px] font-medium
                ${isDone   ? 'text-emerald-400' :
                  isActive ? 'text-white' :
                             'text-[#8DA4BF]'}`}>
                {label}
              </span>
            </div>
            {/* Connector line */}
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-px mx-3 min-w-[24px] transition-all
                ${n < step ? 'bg-emerald-500' : 'bg-[#1E3550]'}`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}