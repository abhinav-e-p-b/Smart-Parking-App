export default function TableCard({ title, action, children }) {
  return (
    <div className="bg-[#132033] border border-[#1E3550] rounded-2xl overflow-hidden mb-5">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[#1E3550]">
        <h3 className="text-[15px] font-semibold text-white"
          style={{ fontFamily: 'Syne, sans-serif' }}>
          {title}
        </h3>
        {action && action}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          {children}
        </table>
      </div>
    </div>
  )
}