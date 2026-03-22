export default function OTPInput({ inputRefs, values, onChange, onKeyDown, hasError }) {
  return (
    <div className="flex gap-1.5 sm:gap-2.5">
      {values.map((val, i) => (
        <input
          key={i}
          ref={(el) => (inputRefs.current[i] = el)}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={val}
          onChange={(e) => onChange(e, i)}
          onKeyDown={(e) => onKeyDown(e, i)}
          className={`w-10 h-11 sm:w-12 sm:h-13 text-center text-lg sm:text-xl font-bold rounded-[10px] border bg-[#0D1B2A] text-white outline-none transition flex-1
            ${hasError
              ? 'border-red-500'
              : val
              ? 'border-cyan-400 shadow-[0_0_0_3px_rgba(0,212,255,0.10)]'
              : 'border-[#1E3550] focus:border-blue-500 focus:shadow-[0_0_0_3px_rgba(30,111,255,0.12)]'
            }`}
          style={{ fontFamily: 'Syne, sans-serif' }}
        />
      ))}
    </div>
  )
}