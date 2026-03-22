export default function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-400 flex items-center justify-center text-xl font-bold text-white">
        P
      </div>
      <span className="font-extrabold text-[22px] tracking-tight text-white" style={{ fontFamily: 'Syne, sans-serif' }}>
        Smart<span className="text-cyan-400">Park</span>
      </span>
    </div>
  )
}