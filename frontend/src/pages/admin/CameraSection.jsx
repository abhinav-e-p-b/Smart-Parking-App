import Badge         from '../../components/admin/Badge'
import TableCard     from '../../components/admin/TableCard'
import SectionHeader from '../../components/admin/SectionHeader'
import { MOCK_CAMERAS, MOCK_LOGS } from '../../data/mockData'

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

export default function CameraSection() {
  return (
    <div>
      <SectionHeader title="Camera Status" subtitle="ANPR camera health and feed preview" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        {MOCK_CAMERAS.map((cam) => (
          <div key={cam.id} className="bg-[#132033] border border-[#1E3550] rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="text-[14px] font-semibold text-white" style={{ fontFamily: 'Syne, sans-serif' }}>
                {cam.name}
              </span>
              <Badge type={cam.status === 'online' ? 'online' : 'offline'}>
                ● {cam.status === 'online' ? 'Online' : 'Offline'}
              </Badge>
            </div>

            {/* Feed placeholder */}
            <div
              className="aspect-video bg-[#0D1B2A] border border-[#1E3550] rounded-xl flex items-center justify-center mb-4"
              style={{
                backgroundImage: 'repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(30,111,255,0.03) 2px,rgba(30,111,255,0.03) 4px)'
              }}
            >
              <div className="text-center">
                <div className="text-3xl mb-2 opacity-40">📷</div>
                <p className="text-[13px] text-[#8DA4BF]">Live feed here</p>
                <p className="text-[11px] text-[#8DA4BF] opacity-50 mt-1">Connect ANPR to stream</p>
              </div>
            </div>

            <div className="flex gap-5">
              <div className="text-[12px] text-[#8DA4BF]">
                <strong className="block text-white font-semibold mb-0.5">{cam.fps} FPS</strong>
                Frame Rate
              </div>
              <div className="text-[12px] text-[#8DA4BF]">
                <strong className="block text-white font-semibold mb-0.5">{cam.confidence}</strong>
                Avg Confidence
              </div>
              <div className="text-[12px] text-[#8DA4BF]">
                <strong className="block text-white font-semibold mb-0.5">{cam.resolution}</strong>
                Resolution
              </div>
            </div>
          </div>
        ))}
      </div>

      <TableCard title="Last Detected Plates">
        <thead>
          <tr>
            <TH>Camera</TH>
            <TH>Plate</TH>
            <TH>Time</TH>
            <TH>Confidence</TH>
            <TH>Result</TH>
          </tr>
        </thead>
        <tbody>
          {MOCK_LOGS.slice(0, 3).map((log) => (
            <tr key={log.id} className="border-b border-[#1E3550] last:border-0 hover:bg-blue-500/10 transition-colors">
              <TD>{log.event === 'Entry' ? 'Entry' : 'Exit'}</TD>
              <TD><strong>{log.vehicleNumber}</strong></TD>
              <TD>{log.timestamp}</TD>
              <TD>{log.confidence}</TD>
              <TD>
                {log.flag
                  ? <Badge type="flagged">⚠ Flagged</Badge>
                  : <Badge type="inside">✓ Granted</Badge>
                }
              </TD>
            </tr>
          ))}
        </tbody>
      </TableCard>
    </div>
  )
}