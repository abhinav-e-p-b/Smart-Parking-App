export default function SectionHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h2 className="text-[22px] font-bold text-white"
          style={{ fontFamily: 'Syne, sans-serif' }}>
          {title}
        </h2>
        {subtitle && (
          <p className="text-[13px] text-[#8DA4BF] mt-1">{subtitle}</p>
        )}
      </div>
      {action && action}
    </div>
  )
}