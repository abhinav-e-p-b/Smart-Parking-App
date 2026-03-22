import { useEffect } from 'react'

export default function Toast({ message, type = 'success', onClose }) {
  useEffect(() => {
    if (!message) return
    const t = setTimeout(onClose, 3500)
    return () => clearTimeout(t)
  }, [message, onClose])

  if (!message) return null

  return (
    <div className={`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl text-sm font-medium text-white animate-slide-up max-w-xs
      bg-[#132033] ${type === 'success' ? 'border border-emerald-500/60' : 'border border-red-500/60'}`}>
      {type === 'success' ? '✓ ' : '✕ '}{message}
    </div>
  )
}