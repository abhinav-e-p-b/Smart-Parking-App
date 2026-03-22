import { useState } from 'react'
import SectionHeader from '../../components/admin/SectionHeader'

export default function ManualSection({ showToast }) {
  const [addVnum,   setAddVnum]   = useState('')
  const [addOwner,  setAddOwner]  = useState('')
  const [addType,   setAddType]   = useState('2-Wheeler')
  const [remVnum,   setRemVnum]   = useState('')
  const [remReason, setRemReason] = useState('Overstayed — Force Exit')

  const inputCls = "w-full bg-[#0D1B2A] border border-[#1E3550] rounded-[10px] py-3 pl-4 text-sm text-white placeholder-[#8DA4BF] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition"
  const labelCls = "block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2"

  function handleAdd() {
    if (!addVnum.trim()) { showToast('Enter a vehicle number', 'error'); return }
    showToast(`Vehicle ${addVnum.toUpperCase()} added to system`, 'success')
    setAddVnum(''); setAddOwner('')
  }

  function handleRemove() {
    if (!remVnum.trim()) { showToast('Enter a vehicle number', 'error'); return }
    showToast(`Vehicle ${remVnum.toUpperCase()} force exited`, 'success')
    setRemVnum('')
  }

  return (
    <div>
      <SectionHeader title="Manual Controls" subtitle="Override and manage vehicles manually" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

        {/* Add vehicle */}
        <div className="bg-[#132033] border border-[#1E3550] rounded-2xl p-6">
          <h3 className="text-[15px] font-semibold text-white mb-5" style={{ fontFamily: 'Syne, sans-serif' }}>
            ➕ Add Vehicle Manually
          </h3>
          <div className="space-y-4">
            <div>
              <label className={labelCls}>Vehicle Number</label>
              <input
                value={addVnum}
                onChange={(e) => setAddVnum(e.target.value.toUpperCase())}
                placeholder="e.g. KL 22 AA 9999"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Owner Name</label>
              <input
                value={addOwner}
                onChange={(e) => setAddOwner(e.target.value)}
                placeholder="Owner's name"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Vehicle Type</label>
              <select
                value={addType}
                onChange={(e) => setAddType(e.target.value)}
                className={inputCls + ' cursor-pointer'}
                style={{ WebkitAppearance: 'none' }}
              >
                <option>2-Wheeler</option>
                <option>4-Wheeler</option>
                <option>SUV / Van</option>
              </select>
            </div>
            <button
              onClick={handleAdd}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all"
            >
              Add to System
            </button>
          </div>
        </div>

        {/* Force exit */}
        <div className="bg-[#132033] border border-[#1E3550] rounded-2xl p-6">
          <h3 className="text-[15px] font-semibold text-white mb-5" style={{ fontFamily: 'Syne, sans-serif' }}>
            ❌ Remove / Force Exit
          </h3>
          <div className="space-y-4">
            <div>
              <label className={labelCls}>Vehicle Number</label>
              <input
                value={remVnum}
                onChange={(e) => setRemVnum(e.target.value.toUpperCase())}
                placeholder="e.g. KL 11 AB 1234"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Reason</label>
              <select
                value={remReason}
                onChange={(e) => setRemReason(e.target.value)}
                className={inputCls + ' cursor-pointer'}
                style={{ WebkitAppearance: 'none' }}
              >
                <option>Overstayed — Force Exit</option>
                <option>Emergency removal</option>
                <option>Wrong vehicle detected</option>
                <option>Payment issue resolved</option>
              </select>
            </div>
            <div className="h-[18px]" />
            <button
              onClick={handleRemove}
              className="w-full py-3 bg-gradient-to-r from-red-500 to-red-700 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px hover:shadow-lg transition-all"
            >
              Force Exit Vehicle
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}