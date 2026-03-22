export default function StatCard({ label, value, trend, trendUp, color }) {
  return (
    <div className="bg-[#132033] border border-[#1E3550] rounded-2xl p-5">
      <div className="text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
        {label}
      </div>
      <div className={`text-[26px] font-bold mb-1 ${color}`}
        style={{ fontFamily: 'Syne, sans-serif' }}>
        {value}
      </div>
      {trend && (
        <div className={`text-[12px] ${trendUp ? 'text-emerald-400' : 'text-[#8DA4BF]'}`}>
          {trend}
        </div>
      )}
    </div>
  )
}