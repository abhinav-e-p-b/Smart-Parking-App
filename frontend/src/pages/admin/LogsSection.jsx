import { useState } from 'react'
import Badge         from '../../components/admin/Badge'
import TableCard     from '../../components/admin/TableCard'
import SectionHeader from '../../components/admin/SectionHeader'
import { MOCK_LOGS } from '../../data/mockData'

const FILTERS = ['All', 'Entry', 'Exit', 'Flagged']

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

export default function LogsSection() {
  const [filter, setFilter] = useState('All')

  const filtered = MOCK_LOGS.filter((log) => {
    if (filter === 'All')     return true
    if (filter === 'Flagged') return !!log.flag
    return log.event === filter
  })

  return (
    <div>
      <SectionHeader title="Event Log" subtitle="Full ANPR entry & exit history" />
      <TableCard
        title="All Events"
        action={
          <div className="flex gap-1.5 flex-wrap">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-full text-[12px] border transition-all
                  ${filter === f
                    ? 'bg-blue-500/15 text-white border-blue-500/40'
                    : 'text-[#8DA4BF] border-[#1E3550] hover:text-white'
                  }`}
              >
                {f}
              </button>
            ))}
          </div>
        }
      >
        <thead>
          <tr>
            <TH>Timestamp</TH>
            <TH>Vehicle No.</TH>
            <TH>Event</TH>
            <TH>Duration</TH>
            <TH>Confidence</TH>
            <TH>Flag</TH>
          </tr>
        </thead>
        <tbody>
          {filtered.map((log) => (
            <tr key={log.id} className="border-b border-[#1E3550] last:border-0 hover:bg-blue-500/10 transition-colors">
              <TD>{log.timestamp}</TD>
              <TD><strong>{log.vehicleNumber}</strong></TD>
              <TD>{log.event}</TD>
              <TD>{log.duration}</TD>
              <TD>{log.confidence}</TD>
              <TD>
                {log.flag
                  ? <Badge type="flagged">⚠ {log.flag}</Badge>
                  : <span className="text-[#8DA4BF]">—</span>
                }
              </TD>
            </tr>
          ))}
        </tbody>
      </TableCard>
    </div>
  )
}