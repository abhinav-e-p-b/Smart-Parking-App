import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Brand from '../components/Brand'
import Toast from '../components/Toast'
import DashboardSection from './admin/DashboardSection'
import VehiclesSection  from './admin/VehiclesSection'
import LogsSection      from './admin/LogsSection'
import ManualSection    from './admin/ManualSection'
import ExportSection    from './admin/ExportSection'
import CameraSection    from './admin/CameraSection'
import ConfigSection    from './admin/ConfigSection'

const NAV_ITEMS = [
  { id: 'dashboard', icon: '📊', label: 'Dashboard',       group: 'Overview'   },
  { id: 'vehicles',  icon: '🚗', label: 'Active Vehicles', group: 'Overview'   },
  { id: 'logs',      icon: '📋', label: 'Event Log',       group: 'Overview'   },
  { id: 'manual',    icon: '🎛', label: 'Manual Controls', group: 'Management' },
  { id: 'export',    icon: '📤', label: 'Export Data',     group: 'Management' },
  { id: 'cameras',   icon: '📷', label: 'Camera Status',   group: 'System'     },
  { id: 'config',    icon: '⚙',  label: 'System Config',   group: 'System'     },
]

const GROUPS = ['Overview', 'Management', 'System']

export default function AdminDashboard() {
  const navigate     = useNavigate()
  const [section,     setSection]     = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [toast,       setToast]       = useState({ message: '', type: 'success' })

  const showToast  = (message, type = 'success') => setToast({ message, type })
  const clearToast = () => setToast({ message: '', type: 'success' })

  function handleNavClick(id) {
    setSection(id)
    setSidebarOpen(false)
  }

  function renderSection() {
    switch (section) {
      case 'dashboard': return <DashboardSection onViewAll={() => setSection('vehicles')} />
      case 'vehicles':  return <VehiclesSection />
      case 'logs':      return <LogsSection />
      case 'manual':    return <ManualSection  showToast={showToast} />
      case 'export':    return <ExportSection  showToast={showToast} />
      case 'cameras':   return <CameraSection />
      case 'config':    return <ConfigSection />
      default:          return <DashboardSection onViewAll={() => setSection('vehicles')} />
    }
  }

  return (
    <>
      {/* Background */}
      <div
        className="fixed inset-0 bg-[#0D1B2A] z-0"
        style={{
          backgroundImage: `linear-gradient(rgba(30,111,255,0.04) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(30,111,255,0.04) 1px, transparent 1px)`,
          backgroundSize: '48px 48px',
        }}
      />

      {/* ── MOBILE SIDEBAR OVERLAY (behind sidebar, above content) ── */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── MOBILE SIDEBAR (above overlay) ── */}
      <aside className={`
        fixed top-0 left-0 h-full z-50
        w-[240px] bg-[#132033] border-r border-[#1E3550] p-3.5
        flex flex-col gap-1 overflow-y-auto
        transition-transform duration-300
        lg:hidden
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Close button */}
        <div className="flex items-center justify-between px-2 py-3 mb-2">
          <Brand />
          <button
            onClick={() => setSidebarOpen(false)}
            className="text-[#8DA4BF] hover:text-white text-xl ml-2"
          >
            ✕
          </button>
        </div>

        {GROUPS.map((group) => (
          <div key={group}>
            <div className="text-[10px] font-semibold text-[#8DA4BF] uppercase tracking-widest px-2 pt-3 pb-1.5">
              {group}
            </div>
            {NAV_ITEMS.filter((n) => n.group === group).map((item) => (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-[9px] text-[13px] font-medium text-left transition-all
                  ${section === item.id
                    ? 'bg-blue-500/15 text-white border border-blue-500/25'
                    : 'text-[#8DA4BF] hover:bg-[#1A2D42] hover:text-white border border-transparent'
                  }`}
              >
                <span className="text-[15px] w-[18px] text-center">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        ))}
      </aside>

      {/* ── MAIN LAYOUT ── */}
      <div className="relative z-10 min-h-screen flex flex-col">

        {/* NAVBAR */}
        <nav className="sticky top-0 z-30 h-16 bg-[#0D1B2A]/90 backdrop-blur-md border-b border-[#1E3550] px-4 md:px-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Hamburger — mobile only */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-[#8DA4BF] hover:text-white text-2xl p-1 leading-none"
            >
              ☰
            </button>
            <Brand />
          </div>
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-[11px] font-semibold">
              ● Live
            </span>
            <span className="hidden md:block text-[13px] text-[#8DA4BF]">Admin Panel</span>
            <button
              onClick={() => navigate('/')}
              className="px-3 md:px-4 py-1.5 bg-transparent border border-[#1E3550] rounded-lg text-[13px] text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition"
            >
              Logout
            </button>
          </div>
        </nav>

        {/* BODY */}
        <div className="flex flex-1">

          {/* DESKTOP SIDEBAR — always visible on lg+ */}
          <aside className="hidden lg:flex w-[220px] shrink-0 bg-[#132033] border-r border-[#1E3550] p-3.5 flex-col gap-1">
            {GROUPS.map((group) => (
              <div key={group}>
                <div className="text-[10px] font-semibold text-[#8DA4BF] uppercase tracking-widest px-2 pt-3 pb-1.5">
                  {group}
                </div>
                {NAV_ITEMS.filter((n) => n.group === group).map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleNavClick(item.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-[9px] text-[13px] font-medium text-left transition-all
                      ${section === item.id
                        ? 'bg-blue-500/15 text-white border border-blue-500/25'
                        : 'text-[#8DA4BF] hover:bg-[#1A2D42] hover:text-white border border-transparent'
                      }`}
                  >
                    <span className="text-[15px] w-[18px] text-center">{item.icon}</span>
                    {item.label}
                  </button>
                ))}
              </div>
            ))}
          </aside>

          {/* MAIN CONTENT */}
          <main className="flex-1 p-4 md:p-8 overflow-y-auto">
            <div className="animate-fade-in" key={section}>
              {renderSection()}
            </div>
          </main>

        </div>
      </div>

      <Toast message={toast.message} type={toast.type} onClose={clearToast} />
    </>
  )
}