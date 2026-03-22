import Badge        from '../../components/admin/Badge'
import TableCard    from '../../components/admin/TableCard'
import SectionHeader from '../../components/admin/SectionHeader'
import { MOCK_VEHICLES } from '../../data/mockData'

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

export default function VehiclesSection() {
  return (
    <div>
      <SectionHeader title="Active Vehicles" subtitle="All vehicles currently tracked" />
      <TableCard title="Vehicle Status">
        <thead>
          <tr>
            <TH>Vehicle No.</TH>
            <TH>Owner</TH>
            <TH>Entry Time</TH>
            <TH>Duration</TH>
            <TH>Plan</TH>
            <TH>Status</TH>
            <TH>Action</TH>
          </tr>
        </thead>
        <tbody>
          {MOCK_VEHICLES.map((v) => (
            <tr key={v.id} className="border-b border-[#1E3550] last:border-0 hover:bg-blue-500/10 transition-colors">
              <TD><strong>{v.vehicleNumber}</strong></TD>
              <TD>{v.owner}</TD>
              <TD>{v.entryTime}</TD>
              <TD>{v.duration}</TD>
              <TD>{v.plan}</TD>
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