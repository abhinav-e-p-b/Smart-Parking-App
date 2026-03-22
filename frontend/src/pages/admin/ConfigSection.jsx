import SectionHeader from '../../components/admin/SectionHeader'

const CONFIG_ITEMS = [
  { label: 'Confidence Threshold', value: '75%',           note: 'Minimum for gate open',  color: 'text-cyan-400',    barWidth: '75%',  barColor: 'bg-blue-500',    mono: false },
  { label: 'Debounce Time',         value: '3.0s',          note: 'Between plate reads',    color: 'text-blue-400',    barWidth: '30%',  barColor: 'bg-blue-500',    mono: false },
  { label: 'GPU Acceleration',      value: 'ON',            note: 'CUDA enabled',           color: 'text-emerald-400', barWidth: '100%', barColor: 'bg-emerald-500', mono: false },
  { label: 'Total Slots',           value: '50',            note: 'System capacity',        color: 'text-white',       barWidth: null,   barColor: null,             mono: false },
  { label: 'Log Retention',         value: '90 days',       note: 'Auto-delete old logs',   color: 'text-orange-400',  barWidth: null,   barColor: null,             mono: false },
  { label: 'API Endpoint',          value: '/api/v1/anpr/', note: 'ANPR webhook URL',       color: 'text-cyan-400',    barWidth: null,   barColor: null,             mono: true  },
]

export default function ConfigSection() {
  return (
    <div>
      <SectionHeader
        title="System Config"
        subtitle="ANPR parameters (display only)"
        action={
          <button className="px-4 py-2 bg-transparent border border-[#1E3550] rounded-lg text-[13px] text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition">
            Edit Config
          </button>
        }
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {CONFIG_ITEMS.map((item) => (
          <div key={item.label} className="bg-[#132033] border border-[#1E3550] rounded-2xl p-5">
            <div className="text-[11px] text-[#8DA4BF] uppercase tracking-wide mb-2">
              {item.label}
            </div>
            <div
              className={`font-bold mb-1 ${item.color} ${item.mono ? 'font-mono text-[13px]' : 'text-[20px]'}`}
              style={{ fontFamily: item.mono ? 'monospace' : 'Syne, sans-serif' }}
            >
              {item.value}
            </div>
            <div className="text-[12px] text-[#8DA4BF]">{item.note}</div>
            {item.barWidth && (
              <div className="h-1 bg-[#0D1B2A] rounded-full mt-3 overflow-hidden">
                <div className={`h-full rounded-full ${item.barColor}`} style={{ width: item.barWidth }} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}