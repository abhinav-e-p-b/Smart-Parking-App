import StatCard  from '../../components/admin/StatCard'
import Badge     from '../../components/admin/Badge'
import TableCard from '../../components/admin/TableCard'
import { MOCK_STATS, MOCK_VEHICLES } from '../../data/mockData'

const TH = ({ children }) => (
  <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-[#8DA4BF] uppercase tracking-wide bg-[#0D1B2A] whitespace-nowrap">
    {children}
  </th>
)
const TD = ({ children }) => (
  <td className="px-4 py-3 text-[13px] text-white whitespace-nowrap">
    {children}
  </td>
)

export default function DashboardSection({ onViewAll }) {
  const today = new Date().toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  })

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-[22px] font-bold text-white" style={{ fontFamily: 'Syne, sans-serif' }}>
            Dashboard
          </h2>
          <p className="text-[13px] text-[#8DA4BF] mt-1">Live overview — updated every 30 seconds</p>
        </div>
        <span className="self-start sm:self-auto px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-[11px] font-semibold whitespace-nowrap">
          Today: {today}
        </span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-5">
        <StatCard label="Total Vehicles Today" value={MOCK_STATS.totalToday}       color="text-cyan-400"     trend="↑ 12% vs yesterday" trendUp />
        <StatCard label="Currently Inside"      value={MOCK_STATS.currentlyInside} color="text-blue-400"    trend="Occupying slots" />
        <StatCard label="Available Slots"       value={MOCK_STATS.availableSlots}  color="text-emerald-400" trend={`of ${MOCK_STATS.totalSlots} total`} />
        <StatCard label="Total Revenue"         value={MOCK_STATS.revenue}         color="text-orange-400"  trend="↑ Today's earnings" trendUp />
      </div>

      {/* Occupancy bar */}
      <div className="bg-[#132033] border border-[#1E3550] rounded-2xl p-5 mb-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[15px] font-semibold text-white" style={{ fontFamily: 'Syne, sans-serif' }}>
            Live Parking Occupancy
          </h3>
          <span className="text-[22px] font-bold text-cyan-400" style={{ fontFamily: 'Syne, sans-serif' }}>
            {MOCK_STATS.occupancyPercent}%
          </span>
        </div>
        <div className="h-2.5 bg-[#0D1B2A] rounded-full overflow-hidden mb-2">
          <div
            className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-400 transition-all duration-700"
            style={{ width: `${MOCK_STATS.occupancyPercent}%` }}
          />
        </div>
        <div className="flex justify-between text-[11px] text-[#8DA4BF]">
          <span>0</span>
          <span>{MOCK_STATS.currentlyInside} / {MOCK_STATS.totalSlots} occupied</span>
          <span>{MOCK_STATS.totalSlots}</span>
        </div>
      </div>

      {/* Recent entries table */}
      <TableCard
        title="Recent Entries"
        action={
          <button
            onClick={onViewAll}
            className="px-4 py-1.5 bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg text-white text-[12px] font-semibold hover:-translate-y-px transition-all"
          >
            View All
          </button>
        }
      >
        <thead>
          <tr>
            <TH>Vehicle No.</TH>
            <TH>Entry Time</TH>
            <TH>Type</TH>
            <TH>Status</TH>
            <TH>Action</TH>
          </tr>
        </thead>
        <tbody>
          {MOCK_VEHICLES.slice(0, 3).map((v) => (
            <tr key={v.id} className="border-b border-[#1E3550] last:border-0 hover:bg-blue-500/10 transition-colors">
              <TD><strong>{v.vehicleNumber}</strong></TD>
              <TD>{v.entryTime}</TD>
              <TD>{v.type}</TD>
              <TD>
                <Badge type={v.status}>
                  {v.status === 'inside' ? '● Inside' : 'Exited'}
                </Badge>
              </TD>
              <TD>
                {v.status === 'inside'
                  ? <button className="px-3 py-1 bg-gradient-to-r from-red-500 to-red-700 rounded-lg text-white text-[11px] font-semibold hover:-translate-y-px transition-all">Force Exit</button>
                  : <span className="text-[#8DA4BF] text-[12px]">—</span>
                }
              </TD>
            </tr>
          ))}
        </tbody>
      </TableCard>
    </div>
  )
}