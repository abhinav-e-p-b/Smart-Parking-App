import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Brand from '../components/Brand'
import StepIndicator from '../components/StepIndicator'
import SuccessScreen from '../components/SuccessScreen'
import Toast from '../components/Toast'
import { PARKING_PLANS } from '../data/mockData'

// ── Vehicle types ─────────────────────────────────────────────
const VEHICLE_TYPES = [
  { id: '2-Wheeler', emoji: '🛵', label: '2-Wheeler' },
  { id: '4-Wheeler', emoji: '🚗', label: '4-Wheeler' },
  { id: 'SUV / Van', emoji: '🚙', label: 'SUV / Van' },
]

// ── Payment methods ───────────────────────────────────────────
const PAY_METHODS = [
  { id: 'UPI',         icon: '📲', label: 'UPI'         },
  { id: 'Card',        icon: '💳', label: 'Card'        },
  { id: 'Net Banking', icon: '🏦', label: 'Net Banking' },
]

// ── Left panel info items ─────────────────────────────────────
const INFO_STEPS = [
  { icon: '✅', color: 'emerald', title: 'Step 1 — Vehicle Details', desc: 'Number, type & arrival date'       },
  { icon: '💳', color: 'blue',    title: 'Step 2 — Choose Plan',     desc: 'Daily, weekly, monthly or yearly' },
  { icon: '🚗', color: 'cyan',    title: 'Step 3 — Confirm & Pay',   desc: 'Gate opens automatically on arrival' },
]

// ── Summary row ───────────────────────────────────────────────
function SummaryRow({ label, value, highlight }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-[#1E3550] last:border-0 text-[13px]">
      <span className="text-[#8DA4BF]">{label}</span>
      <span className={`font-medium ${highlight ? 'text-cyan-400 text-[15px] font-bold' : 'text-white'}`}
        style={highlight ? { fontFamily: 'Syne, sans-serif' } : {}}>
        {value}
      </span>
    </div>
  )
}

// ════════════════════════════════════════════════════════════
export default function Register() {
  const navigate = useNavigate()

  // Read logged-in user from sessionStorage (set during login)
  const user = JSON.parse(sessionStorage.getItem('user') || '{"name":"User","phone":"0000000000"}')

  // ── Step state ───────────────────────────────────────────
  const [step,    setStep]    = useState(1)
  const [success, setSuccess] = useState(false)
  const [bookingId, setBookingId] = useState('')

  // ── Step 1 fields ────────────────────────────────────────
  const [vehicleNumber, setVehicleNumber] = useState('')
  const [arrivalDate,   setArrivalDate]   = useState(new Date().toISOString().slice(0, 10))
  const [vehicleType,   setVehicleType]   = useState('2-Wheeler')
  const [vnumError,     setVnumError]     = useState('')

  // ── Step 2 fields ────────────────────────────────────────
  const [selectedPlan, setSelectedPlan] = useState(PARKING_PLANS[0])
  const [payMethod,    setPayMethod]    = useState('UPI')
  const [upiId,        setUpiId]        = useState('')

  // ── Toast ─────────────────────────────────────────────────
  const [toast, setToast] = useState({ message: '', type: 'success' })
  const showToast  = (message, type = 'success') => setToast({ message, type })
  const clearToast = () => setToast({ message: '', type: 'success' })

  // ─────────────────────────────────────────────────────────
  // STEP 1 — validate vehicle details
  // ─────────────────────────────────────────────────────────
  function handleStep1() {
    if (vehicleNumber.trim().length < 4) {
      setVnumError('Enter a valid vehicle number (min 4 characters)')
      return
    }
    setVnumError('')
    setStep(2)
  }

  // ─────────────────────────────────────────────────────────
  // STEP 2 — proceed to confirm
  // ─────────────────────────────────────────────────────────
  function handleStep2() {
  // If UPI is selected, UPI ID must be filled
    if (payMethod === 'UPI' && !upiId.trim()) {
      showToast('Please enter your UPI ID to continue', 'error')
      return
    }
    setStep(3)
  }

  // ─────────────────────────────────────────────────────────
  // STEP 3 — submit registration
  // ─────────────────────────────────────────────────────────
  function handleSubmit() {
    // ── API-READY ──────────────────────────────────────────
    // await supabase.from('vehicles').upsert({
    //   vehicle_number: vehicleNumber,
    //   type: vehicleType,
    //   user_id: user.id
    // })
    // await supabase.from('bookings').insert({
    //   vehicle_number: vehicleNumber,
    //   date: arrivalDate,
    //   plan: selectedPlan.label,
    //   amount: selectedPlan.price,
    //   payment_method: payMethod,
    //   payment_status: 'paid'
    // })
    // ──────────────────────────────────────────────────────
    const id = 'SP-' + Math.floor(100000 + Math.random() * 900000)
    setBookingId(id)
    setSuccess(true)
    showToast(`Payment confirmed! Booking: ${id}`, 'success')
  }

  // ─────────────────────────────────────────────────────────
  // Reset for "Register Another"
  // ─────────────────────────────────────────────────────────
  function handleRegisterAnother() {
    setStep(1)
    setSuccess(false)
    setBookingId('')
    setVehicleNumber('')
    setVnumError('')
    setArrivalDate(new Date().toISOString().slice(0, 10))
    setVehicleType('2-Wheeler')
    setSelectedPlan(PARKING_PLANS[0])
    setPayMethod('UPI')
    setUpiId('')
  }

  // ─────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────
  return (
    <>
      {/* Background */}
      <div className="fixed inset-0 bg-[#0D1B2A] z-0"
        style={{
          backgroundImage: `linear-gradient(rgba(30,111,255,0.04) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(30,111,255,0.04) 1px, transparent 1px)`,
          backgroundSize: '48px 48px',
        }}
      />
      <div className="fixed top-[-120px] right-[-80px] w-[500px] h-[500px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(30,111,255,0.18)', filter: 'blur(120px)' }} />
      <div className="fixed bottom-0 left-[-100px] w-[400px] h-[400px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(0,212,255,0.10)', filter: 'blur(120px)' }} />

      {/* Split layout */}
      <div className="relative z-10 min-h-screen grid grid-cols-1 lg:grid-cols-[1fr_1.15fr]">

        {/* ── LEFT PANEL ── */}
        <div className="hidden lg:flex p-16 border-r border-[#1E3550] flex-col justify-center">
          <div className="mb-11"><Brand /></div>

          <h1 className="text-[34px] font-extrabold leading-tight tracking-tight text-white mb-3"
            style={{ fontFamily: 'Syne, sans-serif' }}>
            Register your<br /><span className="text-cyan-400">vehicle.</span>
          </h1>
          <p className="text-sm text-[#8DA4BF] leading-relaxed mb-9 max-w-xs">
            Complete registration and payment to activate your smart parking pass. Our ANPR system handles the rest.
          </p>

          {/* Info steps */}
          <div className="flex flex-col gap-4 mb-10">
            {INFO_STEPS.map((s) => (
              <div key={s.title} className="flex items-start gap-3">
                <div className={`w-9 h-9 shrink-0 rounded-[9px] flex items-center justify-center text-sm
                  ${s.color === 'emerald' ? 'bg-emerald-500/8 border border-emerald-500/30' :
                    s.color === 'blue'    ? 'bg-blue-500/8   border border-blue-500/30'    :
                                           'bg-cyan-500/8    border border-cyan-500/30'    }`}>
                  {s.icon}
                </div>
                <div>
                  <strong className="block text-[13px] font-medium text-white mb-0.5">{s.title}</strong>
                  <span className="text-[11px] text-[#8DA4BF]">{s.desc}</span>
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={() => navigate('/')}
            className="w-fit py-2.5 px-5 bg-transparent border border-[#1E3550] rounded-xl text-[13px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition"
          >
            ← Back to Home
          </button>
        </div>

        {/* ── RIGHT PANEL (Form) ── */}
        <div className="p-6 md:p-14 flex items-center justify-center overflow-y-auto">
          <div className="w-full max-w-[500px]">

            {/* Success screen */}
            {success ? (
              <SuccessScreen
                bookingId={bookingId}
                onRegisterAnother={handleRegisterAnother}
              />
            ) : (
              <>
                <h2 className="text-[22px] font-bold text-white mb-1"
                  style={{ fontFamily: 'Syne, sans-serif' }}>
                  Vehicle Registration
                </h2>
                <p className="text-[13px] text-[#8DA4BF] mb-6">
                  Logged in as:{' '}
                  <strong className="text-cyan-400">
                    +91 {user.phone}
                  </strong>
                </p>

                <StepIndicator step={step} />

                {/* ══ STEP 1: Vehicle Details ══ */}
                {step === 1 && (
                  <div className="space-y-5 animate-fade-in">

                    {/* Vehicle number */}
                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
                        Vehicle Number
                      </label>
                      <div className="relative">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">🔢</span>
                        <input
                          type="text"
                          value={vehicleNumber}
                          onChange={(e) => {
                            setVehicleNumber(e.target.value.toUpperCase())
                            setVnumError('')
                          }}
                          placeholder="e.g. KL 11 AB 1234"
                          className={`w-full bg-[#0D1B2A] border rounded-[10px] py-3 pl-10 text-sm text-white placeholder-[#8DA4BF] outline-none transition uppercase
                            ${vnumError
                              ? 'border-red-500'
                              : 'border-[#1E3550] focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10'
                            }`}
                        />
                      </div>
                      {vnumError && <p className="text-[11px] text-red-400 mt-1.5">{vnumError}</p>}
                    </div>

                    {/* Arrival date */}
                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
                        Date of Arrival
                      </label>
                      <div className="relative">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">📅</span>
                        <input
                          type="date"
                          value={arrivalDate}
                          onChange={(e) => setArrivalDate(e.target.value)}
                          className="w-full bg-[#0D1B2A] border border-[#1E3550] rounded-[10px] py-3 pl-10 text-sm text-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition"
                          style={{ colorScheme: 'dark' }}
                        />
                      </div>
                    </div>

                    {/* Vehicle type */}
                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
                        Vehicle Type
                      </label>
                      <div className="grid grid-cols-3 gap-3">
                        {VEHICLE_TYPES.map((v) => (
                          <button
                            key={v.id}
                            onClick={() => setVehicleType(v.id)}
                            className={`border rounded-[10px] py-3 px-2 text-center transition-all
                              ${vehicleType === v.id
                                ? 'border-blue-500 bg-blue-500/10'
                                : 'border-[#1E3550] bg-[#0D1B2A] hover:border-blue-500/50'
                              }`}
                          >
                            <span className="text-[22px] block mb-1">{v.emoji}</span>
                            <span className={`text-[11px] ${vehicleType === v.id ? 'text-white' : 'text-[#8DA4BF]'}`}>
                              {v.label}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>

                    <button
                      onClick={handleStep1}
                      className="w-full py-[15px] bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[15px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all"
                    >
                      Continue to Payment →
                    </button>
                  </div>
                )}

                {/* ══ STEP 2: Plan + Payment ══ */}
                {step === 2 && (
                  <div className="space-y-5 animate-fade-in">

                    {/* Plans */}
                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-3">
                        Select Plan
                      </label>
                      <div className="grid grid-cols-2 gap-3">
                        {PARKING_PLANS.map((plan) => (
                          <button
                            key={plan.id}
                            onClick={() => setSelectedPlan(plan)}
                            className={`relative border rounded-xl p-3.5 text-left transition-all
                              ${selectedPlan.id === plan.id
                                ? 'border-cyan-400 bg-cyan-400/6'
                                : 'border-[#1E3550] bg-[#0D1B2A] hover:border-blue-500/50'
                              }`}
                          >
                            {plan.popular && (
                              <span className="absolute -top-2 right-2 bg-blue-600 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide">
                                Popular
                              </span>
                            )}
                            <div className="text-[13px] font-semibold text-white mb-0.5">{plan.label}</div>
                            <div className="text-[20px] font-bold text-cyan-400" style={{ fontFamily: 'Syne, sans-serif' }}>
                              ₹{plan.price}
                            </div>
                            <div className="text-[11px] text-[#8DA4BF]">{plan.period}</div>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Amount display */}
                    <div className="bg-[#0D1B2A] border border-[#1E3550] rounded-xl px-5 py-4 flex items-center justify-between">
                      <div>
                        <div className="text-[13px] text-[#8DA4BF]">Amount to Pay</div>
                        <div className="text-[12px] text-[#8DA4BF] mt-0.5">{selectedPlan.label}</div>
                      </div>
                      <div className="text-[26px] font-bold text-cyan-400" style={{ fontFamily: 'Syne, sans-serif' }}>
                        ₹{selectedPlan.price}
                      </div>
                    </div>

                    {/* Payment method */}
                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-3">
                        Payment Method
                      </label>
                      <div className="flex gap-3">
                        {PAY_METHODS.map((m) => (
                          <button
                            key={m.id}
                            onClick={() => setPayMethod(m.id)}
                            className={`flex-1 border rounded-[10px] py-3 text-center transition-all
                              ${payMethod === m.id
                                ? 'border-blue-500 bg-blue-500/10 text-white'
                                : 'border-[#1E3550] bg-[#0D1B2A] text-[#8DA4BF] hover:border-blue-500/50 hover:text-white'
                              }`}
                          >
                            <span className="text-xl block mb-1">{m.icon}</span>
                            <span className="text-[12px]">{m.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* UPI ID field — only shows when UPI selected */}
                    {payMethod === 'UPI' && (
                      <div className="animate-fade-in">
                        <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
                          UPI ID
                        </label>
                        <div className="relative">
                          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-[#8DA4BF] pointer-events-none">@</span>
                          <input
                            type="text"
                            value={upiId}
                            onChange={(e) => setUpiId(e.target.value)}
                            placeholder="e.g. yourname@upi"
                            className={`w-full bg-[#0D1B2A] border rounded-[10px] py-3 pl-9 text-sm text-white placeholder-[#8DA4BF] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition
                              ${payMethod === 'UPI' && !upiId.trim() && upiId !== '' ? 'border-red-500' : 'border-[#1E3550]'}`}
                          />
                        </div>
                        {/* Helper text */}
                        <p className="text-[11px] text-[#8DA4BF] mt-1.5">
                          Enter your UPI ID to proceed with payment
                        </p>
                      </div>
                    )}

                    <div className="flex gap-3 pt-1">
                      <button
                        onClick={() => setStep(1)}
                        className="flex-1 py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition"
                      >
                        ← Back
                      </button>
                      <button
                        onClick={handleStep2}
                        className="flex-[2] py-3.5 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all"
                      >
                        Review & Confirm →
                      </button>
                    </div>
                  </div>
                )}

                {/* ══ STEP 3: Confirm ══ */}
                {step === 3 && (
                  <div className="animate-fade-in">
                    <div className="bg-[#0D1B2A] border border-[#1E3550] rounded-xl p-4 mb-5">
                      <SummaryRow label="Name"           value={user.name} />
                      <SummaryRow label="Phone"          value={`+91 ${user.phone}`} />
                      <SummaryRow label="Vehicle Number" value={vehicleNumber} />
                      <SummaryRow label="Vehicle Type"   value={vehicleType} />
                      <SummaryRow label="Date of Arrival" value={arrivalDate} />
                      <SummaryRow label="Plan"           value={selectedPlan.label} />
                      <SummaryRow label="Payment Method" value={payMethod} />
                      <SummaryRow label="Total Amount"   value={`₹${selectedPlan.price}`} highlight />
                    </div>

                    <div className="flex gap-3">
                      <button
                        onClick={() => setStep(2)}
                        className="flex-1 py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition"
                      >
                        ← Back
                      </button>
                      <button
                        onClick={handleSubmit}
                        className="flex-[2] py-3.5 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all"
                      >
                        ✓ Confirm & Pay
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

      </div>

      <Toast message={toast.message} type={toast.type} onClose={clearToast} />
    </>
  )
}