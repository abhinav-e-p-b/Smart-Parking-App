import { useState } from 'react'
import SectionHeader from '../../components/admin/SectionHeader'
import { MOCK_LOGS, MOCK_VEHICLES } from '../../data/mockData'

const PERIODS = ['Today', 'This Week', 'All Time']

function ExportCard({ title, subtitle, onExport }) {
  const [period, setPeriod] = useState('Today')
  return (
    <div className="bg-[#132033] border border-[#1E3550] rounded-2xl p-6 mb-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <div className="text-[15px] font-semibold text-white mb-1" style={{ fontFamily: 'Syne, sans-serif' }}>
            {title}
          </div>
          <div className="text-[13px] text-[#8DA4BF]">{subtitle}</div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded-full text-[12px] border transition-all
                ${period === p
                  ? 'bg-blue-500/15 text-white border-blue-500/40'
                  : 'text-[#8DA4BF] border-[#1E3550] hover:text-white'
                }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>
      <button
        onClick={() => onExport(period)}
        className="px-7 py-3 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all"
      >
        ⬇ Export CSV
      </button>
    </div>
  )
}

export default function ExportSection({ showToast }) {

  function downloadCSV(rows, filename) {
    const blob = new Blob([rows.map((r) => r.join(',')).join('\n')], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    showToast('CSV exported successfully!', 'success')
  }

  function exportLogs() {
    const rows = [
      ['Timestamp', 'Vehicle No.', 'Event', 'Duration', 'Confidence'],
      ...MOCK_LOGS.map((l) => [l.timestamp, l.vehicleNumber, l.event, l.duration, l.confidence])
    ]
    downloadCSV(rows, `smartpark_logs_${new Date().toISOString().slice(0,10)}.csv`)
  }

  function exportBookings() {
    const rows = [
      ['Vehicle No.', 'Owner', 'Entry Time', 'Duration', 'Plan', 'Status'],
      ...MOCK_VEHICLES.map((v) => [v.vehicleNumber, v.owner, v.entryTime, v.duration, v.plan, v.status])
    ]
    downloadCSV(rows, `smartpark_bookings_${new Date().toISOString().slice(0,10)}.csv`)
  }

  return (
    <div>
      <SectionHeader title="Export Data" subtitle="Download logs as CSV" />
      <ExportCard
        title="Entry / Exit Logs"
        subtitle="All ANPR events with timestamps"
        onExport={exportLogs}
      />
      <ExportCard
        title="Booking & Payment Records"
        subtitle="All registrations with payment status"
        onExport={exportBookings}
      />
    </div>
  )
}