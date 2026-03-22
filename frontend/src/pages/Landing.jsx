import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Brand from '../components/Brand'
import PasswordInput from '../components/PasswordInput'
import Toast from '../components/Toast'

// ─── Mock data — swap with real API call later ───────────────────────────────
import { MOCK_USER, MOCK_ADMIN } from '../data/mockData'
// ─────────────────────────────────────────────────────────────────────────────

// Left panel features list
const FEATURES = [
  { icon: '📷', title: 'Automatic Entry & Exit', desc: 'ANPR reads your plate — gate opens instantly' },
  { icon: '🔒', title: 'Secure & Verified',      desc: 'Only registered, paid vehicles get access' },
  { icon: '📊', title: 'Live Slot Tracking',     desc: 'Real-time slot availability, always accurate' },
]

const SLOTS = [
  { occupied: true,  emoji: '🚗' },
  { occupied: true,  emoji: '🚙' },
  { occupied: false, emoji: ''   },
  { occupied: false, emoji: ''   },
  { occupied: true,  emoji: '🚗' },
]

export default function Landing() {
  const navigate = useNavigate()

  // which login tab is active
  const [mode, setMode] = useState('user') // 'user' | 'admin'

  // form fields
  const [phone,     setPhone]     = useState('')
  const [password,  setPassword]  = useState('')
  const [adminId,   setAdminId]   = useState('')
  const [adminPass, setAdminPass] = useState('')

  // toast
  const [toast, setToast] = useState({ message: '', type: 'success' })
  const showToast = (message, type = 'success') => setToast({ message, type })
  const clearToast = () => setToast({ message: '', type: 'success' })

  // ── User login handler ────────────────────────────────────────────────────
  function handleUserLogin(e) {
    e.preventDefault()
    if (!phone || !password) {
      showToast('Enter phone number and password', 'error'); return
    }
    if (!/^\d{10}$/.test(phone)) {
      showToast('Enter a valid 10-digit phone number', 'error'); return
    }
    // ── API-READY ──────────────────────────────────────────────────────────
    // const { data, error } = await supabase.auth.signInWithPassword({
    //   phone: '+91' + phone, password
    // })
    // if (error) { showToast(error.message, 'error'); return }
    // ──────────────────────────────────────────────────────────────────────
    if (phone === MOCK_USER.phone && password === MOCK_USER.password) {
      // Store user in sessionStorage so Register page can read it
      sessionStorage.setItem('user', JSON.stringify({ name: MOCK_USER.name, phone }))
      showToast('Signed in! Redirecting...', 'success')
      setTimeout(() => navigate('/register'), 1000)
    } else {
      showToast('Incorrect phone number or password', 'error')
    }
  }

  // ── Admin login handler ───────────────────────────────────────────────────
  function handleAdminLogin(e) {
    e.preventDefault()
    // ── API-READY: replace with real admin auth ────────────────────────────
    if (adminId === MOCK_ADMIN.id && adminPass === MOCK_ADMIN.password) {
      showToast('Welcome, Admin!', 'success')
      setTimeout(() => navigate('/admin'), 1000)
    } else {
      showToast('Invalid admin credentials', 'error')
    }
  }

  return (
    <>
      {/* Grid background */}
      <div className="fixed inset-0 bg-[#0D1B2A] z-0"
        style={{
          backgroundImage: `linear-gradient(rgba(30,111,255,0.04) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(30,111,255,0.04) 1px, transparent 1px)`,
          backgroundSize: '48px 48px'
        }}
      />
      {/* Glow orbs */}
      <div className="fixed top-[-120px] right-[-80px] w-[500px] h-[500px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(30,111,255,0.18)', filter: 'blur(120px)' }} />
      <div className="fixed bottom-0 left-[-100px] w-[400px] h-[400px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(0,212,255,0.10)', filter: 'blur(120px)' }} />

      {/* Page center */}
      <div className="relative z-10 min-h-screen flex items-center justify-center p-8">
        <div className="w-full max-w-[960px] grid grid-cols-1 md:grid-cols-[1.1fr_1fr] bg-[#132033] ...">

          {/* ── LEFT INFO PANEL ── */}
          <div className="hidden md:flex p-14 border-r border-[#1E3550] flex-col justify-center">
            <div className="mb-11"><Brand /></div>

            <h1 className="text-[36px] font-extrabold leading-tight tracking-tight text-white mb-3"
              style={{ fontFamily: 'Syne, sans-serif' }}>
              Skip the Queue,<br />Park <span className="text-cyan-400">instantly.</span>
            </h1>
            <p className="text-sm text-[#8DA4BF] leading-relaxed mb-9">
              Register once, pay digitally, and let our ANPR cameras handle entry &amp; exit — no tickets, no queues.
            </p>

            {/* Features */}
            <div className="flex flex-col gap-4 mb-8">
              {FEATURES.map((f) => (
                <div key={f.title} className="flex items-start gap-3">
                  <div className="w-9 h-9 shrink-0 rounded-[9px] bg-[#0D1B2A] border border-[#1E3550] flex items-center justify-center text-sm">
                    {f.icon}
                  </div>
                  <div>
                    <strong className="block text-[13px] font-medium text-white mb-0.5">{f.title}</strong>
                    <span className="text-[11px] text-[#8DA4BF]">{f.desc}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Animated parking slots */}
            <div className="flex gap-2 items-end">
              {SLOTS.map((s, i) => (
                <div
                  key={i}
                  className={`w-10 h-13 rounded-md border flex items-center justify-center text-base
                    ${s.occupied
                      ? 'bg-blue-500/15 border-blue-500'
                      : 'bg-emerald-500/8 border-emerald-500/30'}`}
                  style={{ animation: `pulse-slot 3s ease-in-out ${i * 0.4}s infinite` }}
                >
                  {s.emoji}
                </div>
              ))}
              <span className="text-[11px] text-[#8DA4BF] ml-2 self-center">2 slots free</span>
            </div>
          </div>

          {/* ── RIGHT LOGIN PANEL ── */}
          <div className="p-10 flex flex-col justify-center">

            {/* Mode toggle */}
            <div className="flex bg-[#0D1B2A] border border-[#1E3550] rounded-[10px] p-1 mb-6 gap-1">
              {['user', 'admin'].map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`flex-1 py-2 rounded-[7px] text-[13px] font-medium transition-all
                    ${mode === m ? 'bg-blue-600 text-white' : 'text-[#8DA4BF] hover:text-white'}`}
                >
                  {m === 'user' ? 'User Login' : 'Admin Login'}
                </button>
              ))}
            </div>

            {/* ── USER LOGIN FORM ── */}
            {mode === 'user' && (
              <form onSubmit={handleUserLogin} noValidate>
                <h2 className="text-xl font-bold text-white mb-1" style={{ fontFamily: 'Syne, sans-serif' }}>
                  Welcome back
                </h2>
                <p className="text-[13px] text-[#8DA4BF] mb-5">Sign in with your phone number</p>

                {/* Phone */}
                <div className="mb-4">
                  <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
                    Phone Number{' '}
                    <span className="text-cyan-400 normal-case tracking-normal text-[10px]">
                      — Your User ID
                    </span>
                  </label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">📱</span>
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                      placeholder="10-digit mobile number"
                      className="w-full bg-[#0D1B2A] border border-[#1E3550] rounded-[10px] py-3 pl-10 text-sm text-white placeholder-[#8DA4BF] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition"
                    />
                  </div>
                </div>

                {/* Password */}
                <div className="mb-2">
                  <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
                    Password
                  </label>
                  <PasswordInput
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Your password"
                  />
                </div>

                {/* Forgot password */}
                <div className="text-right mb-4">
                  <button
                    type="button"
                    onClick={() => navigate('/forgot-password')}
                    className="text-[12px] text-cyan-400 hover:underline"
                  >
                    Forgot password?
                  </button>
                </div>

                <button
                  type="submit"
                  className="w-full py-[15px] bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[15px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all"
                >
                  Sign In →
                </button>

                <div className="flex items-center gap-3 my-4">
                  <div className="flex-1 h-px bg-[#1E3550]" />
                  <span className="text-[12px] text-[#8DA4BF]">or</span>
                  <div className="flex-1 h-px bg-[#1E3550]" />
                </div>

                <button
                  type="button"
                  onClick={() => navigate('/signup')}
                  className="w-full py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition"
                >
                  Create New Account
                </button>

                <p className="text-center text-[13px] text-[#8DA4BF] mt-3">
                  New here?{' '}
                  <button type="button" onClick={() => navigate('/signup')} className="text-cyan-400 font-medium hover:underline">
                    Register for free
                  </button>
                </p>
              </form>
            )}

            {/* ── ADMIN LOGIN FORM ── */}
            {mode === 'admin' && (
              <form onSubmit={handleAdminLogin} noValidate>
                <h2 className="text-xl font-bold text-white mb-1" style={{ fontFamily: 'Syne, sans-serif' }}>
                  Admin Access
                </h2>
                <p className="text-[13px] text-[#8DA4BF] mb-5">Restricted — authorized personnel only</p>

                <div className="mb-4">
                  <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
                    Admin Phone / ID
                  </label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">🛡</span>
                    <input
                      type="text"
                      value={adminId}
                      onChange={(e) => setAdminId(e.target.value)}
                      placeholder="Admin phone or ID"
                      className="w-full bg-[#0D1B2A] border border-[#1E3550] rounded-[10px] py-3 pl-10 text-sm text-white placeholder-[#8DA4BF] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition"
                    />
                  </div>
                </div>

                <div className="mb-6">
                  <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
                    Password
                  </label>
                  <PasswordInput
                    value={adminPass}
                    onChange={(e) => setAdminPass(e.target.value)}
                    placeholder="Admin password"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-[15px] bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[15px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all"
                >
                  Access Dashboard →
                </button>
              </form>
            )}
          </div>

        </div>
      </div>

      <Toast message={toast.message} type={toast.type} onClose={clearToast} />

      {/* Slot animation keyframe */}
      <style>{`
        @keyframes pulse-slot {
          0%, 100% { transform: translateY(0); }
          50%       { transform: translateY(-4px); }
        }
      `}</style>
    </>
  )
}