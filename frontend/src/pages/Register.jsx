import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Brand from '../components/Brand'
import StepIndicator from '../components/StepIndicator'
import SuccessScreen from '../components/SuccessScreen'
import Toast from '../components/Toast'
import { PARKING_PLANS } from '../data/mockData'
import supabase from '../supabase'

const VEHICLE_TYPES = [
  { id: '2-wheeler', emoji: '🛵', label: '2-Wheeler' },
  { id: '4-wheeler', emoji: '🚗', label: '4-Wheeler' },
  { id: 'suv-van',   emoji: '🚙', label: 'SUV / Van' },
]

const PAY_METHODS = [
  { id: 'upi',         icon: '📲', label: 'UPI'         },
  { id: 'card',        icon: '💳', label: 'Card'        },
  { id: 'net-banking', icon: '🏦', label: 'Net Banking' },
]

const INFO_STEPS = [
  { icon: '✅', color: 'emerald', title: 'Step 1 — Vehicle Details', desc: 'Number, type & arrival date'        },
  { icon: '💳', color: 'blue',    title: 'Step 2 — Choose Plan',     desc: 'Daily, weekly, monthly or yearly'  },
  { icon: '🚗', color: 'cyan',    title: 'Step 3 — Confirm & Pay',   desc: 'Gate opens automatically on arrival' },
]

function SummaryRow({ label, value, highlight }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-[#1E3550] last:border-0 text-[13px]">
      <span className="text-[#8DA4BF]">{label}</span>
      <span
        className={`font-medium ${highlight ? 'text-cyan-400 text-[15px] font-bold' : 'text-white'}`}
        style={highlight ? { fontFamily: 'Syne, sans-serif' } : {}}
      >
        {value}
      </span>
    </div>
  )
}

// ── Dummy Payment Modal ───────────────────────────────────
function PaymentModal({ plan, method, upiId, onSuccess, onCancel, processing }) {
  const [otp, setOtp] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [otpError, setOtpError] = useState('')

  function handleSendOtp() {
    setOtpSent(true)
    setOtpError('')
  }

  function handleVerify() {
    if (method === 'upi') {
      if (otp !== '1234') { setOtpError('Invalid OTP. (Hint: use 1234)'); return }
    }
    onSuccess()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm mx-4 bg-[#0D1B2A] border border-[#1E3550] rounded-2xl p-6 shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-[17px] font-bold text-white" style={{ fontFamily: 'Syne, sans-serif' }}>
            Complete Payment
          </h3>
          <button onClick={onCancel} className="text-[#8DA4BF] hover:text-white text-xl leading-none">×</button>
        </div>

        {/* Amount banner */}
        <div className="bg-blue-500/8 border border-blue-500/20 rounded-xl px-4 py-3 flex justify-between items-center mb-5">
          <div>
            <div className="text-[11px] text-[#8DA4BF] uppercase tracking-wide">Amount Due</div>
            <div className="text-[12px] text-[#8DA4BF] mt-0.5">{plan.label}</div>
          </div>
          <div className="text-[28px] font-bold text-cyan-400" style={{ fontFamily: 'Syne, sans-serif' }}>
            ₹{plan.price}
          </div>
        </div>

        {/* UPI flow */}
        {method === 'upi' && (
          <div className="space-y-4">
            <div className="bg-[#0a1520] border border-[#1E3550] rounded-xl px-4 py-3">
              <div className="text-[11px] text-[#8DA4BF] uppercase tracking-wide mb-1">Paying to</div>
              <div className="text-[13px] text-white font-medium">smartpark@upi</div>
            </div>
            <div className="bg-[#0a1520] border border-[#1E3550] rounded-xl px-4 py-3">
              <div className="text-[11px] text-[#8DA4BF] uppercase tracking-wide mb-1">From</div>
              <div className="text-[13px] text-white font-medium">{upiId || 'yourname@upi'}</div>
            </div>

            {!otpSent ? (
              <button
                onClick={handleSendOtp}
                className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px transition-all"
              >
                Send OTP →
              </button>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
                    Enter OTP (sent to your UPI app)
                  </label>
                  <input
                    type="text"
                    maxLength={4}
                    value={otp}
                    onChange={(e) => { setOtp(e.target.value); setOtpError('') }}
                    placeholder="• • • •"
                    className={`w-full bg-[#0D1B2A] border rounded-[10px] py-3 px-4 text-sm text-white placeholder-[#8DA4BF] outline-none text-center tracking-[0.4em] transition
                      ${otpError ? 'border-red-500' : 'border-[#1E3550] focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10'}`}
                  />
                  {otpError && <p className="text-[11px] text-red-400 mt-1.5">{otpError}</p>}
                  <p className="text-[11px] text-[#8DA4BF] mt-1.5">Demo OTP: <strong className="text-cyan-400">1234</strong></p>
                </div>
                <button
                  onClick={handleVerify}
                  disabled={processing || otp.length !== 4}
                  className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px transition-all disabled:opacity-60"
                >
                  {processing ? 'Processing...' : '✓ Verify & Pay'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Card flow */}
        {method === 'card' && (
          <div className="space-y-3">
            <div>
              <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">Card Number</label>
              <input
                type="text"
                defaultValue="4242 4242 4242 4242"
                readOnly
                className="w-full bg-[#0a1520] border border-[#1E3550] rounded-[10px] py-3 px-4 text-sm text-white outline-none tracking-widest"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">Expiry</label>
                <input defaultValue="12/28" readOnly className="w-full bg-[#0a1520] border border-[#1E3550] rounded-[10px] py-3 px-4 text-sm text-white outline-none" />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">CVV</label>
                <input defaultValue="•••" readOnly className="w-full bg-[#0a1520] border border-[#1E3550] rounded-[10px] py-3 px-4 text-sm text-white outline-none" />
              </div>
            </div>
            <p className="text-[11px] text-[#8DA4BF]">Demo card — pre-filled, just click Pay.</p>
            <button
              onClick={onSuccess}
              disabled={processing}
              className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px transition-all disabled:opacity-60"
            >
              {processing ? 'Processing...' : '✓ Pay ₹' + plan.price}
            </button>
          </div>
        )}

        {/* Net Banking flow */}
        {method === 'net-banking' && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              {['SBI', 'HDFC', 'ICICI', 'Axis', 'Kotak', 'Other'].map((bank) => (
                <button key={bank}
                  className="border border-[#1E3550] rounded-[10px] py-2.5 text-[12px] text-[#8DA4BF] hover:border-blue-500/50 hover:text-white transition bg-[#0a1520]">
                  {bank}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-[#8DA4BF]">Demo mode — select any bank and confirm.</p>
            <button
              onClick={onSuccess}
              disabled={processing}
              className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px transition-all disabled:opacity-60"
            >
              {processing ? 'Processing...' : '✓ Confirm Payment'}
            </button>
          </div>
        )}

      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────
export default function Register() {
  const navigate = useNavigate()

  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getUser().then(async ({ data: { user: authUser } }) => {
      if (!authUser) { navigate('/'); return }
      const { data: profile } = await supabase
        .from('users')
        .select('name, phone')
        .eq('id', authUser.id)
        .single()
      setUser({ ...authUser, profile })
      setLoading(false)
    })
  }, [navigate])

  const [step,      setStep]      = useState(1)
  const [success,   setSuccess]   = useState(false)
  const [bookingId, setBookingId] = useState('')
  const [saving,    setSaving]    = useState(false)

  // Step 1
  const [vehicleNumber, setVehicleNumber] = useState('')
  const [arrivalDate,   setArrivalDate]   = useState(new Date().toISOString().slice(0, 10))
  const [vehicleType,   setVehicleType]   = useState('2-wheeler')
  const [vnumError,     setVnumError]     = useState('')

  // Step 2
  const [selectedPlan, setSelectedPlan] = useState(PARKING_PLANS[0])
  const [payMethod,    setPayMethod]    = useState('upi')
  const [upiId,        setUpiId]        = useState('')

  // IDs
  const [vehicleId,   setVehicleId]   = useState(null)
  const [slotId,      setSlotId]      = useState(null)

  // Payment modal
  const [showPayModal, setShowPayModal] = useState(false)

  // Toast
  const [toast, setToast] = useState({ message: '', type: 'success' })
  const showToast  = (message, type = 'success') => setToast({ message, type })
  const clearToast = () => setToast({ message: '', type: 'success' })

  // ── STEP 1: Save vehicle ─────────────────────────────────
  async function handleStep1() {
    if (vehicleNumber.trim().length < 4) {
      setVnumError('Enter a valid vehicle number (min 4 characters)')
      return
    }
    setVnumError('')
    setSaving(true)

    try {
      const { data: vehicle, error } = await supabase
        .from('vehicles')
        .upsert({
          user_id:      user.id,
          plate_number: vehicleNumber.trim().toUpperCase(),
          vehicle_type: vehicleType,
          is_active:    true,
        }, { onConflict: 'plate_number' })
        .select('id')
        .single()

      if (error) throw error
      setVehicleId(vehicle.id)
      setStep(2)
    } catch (err) {
      console.error(err)
      showToast('Failed to save vehicle. Try again.', 'error')
    } finally {
      setSaving(false)
    }
  }

  // ── STEP 2: Check availability, get slot ─────────────────
  async function handleStep2() {
    if (payMethod === 'upi' && !upiId.trim()) {
      showToast('Please enter your UPI ID to continue', 'error')
      return
    }
    setSaving(true)

    try {
      // 1. Get the general parking slot
      const { data: slots, error: slotErr } = await supabase
        .from('parking_slots')
        .select('id, capacity')
        .eq('is_active', true)
        .limit(1)
        .single()

      if (slotErr || !slots) throw new Error('Could not fetch parking slot info.')

      // 2. Count bookings that overlap with the arrival date
      const { count, error: countErr } = await supabase
        .from('bookings')
        .select('id', { count: 'exact', head: true })
        .eq('slot_id', slots.id)
        .lte('scheduled_entry', arrivalDate)   // booking starts on or before arrival
        .gte('scheduled_exit',  arrivalDate)   // booking ends on or after arrival
        .in('status', ['pending', 'confirmed', 'active'])

      if (countErr) throw countErr

      if (count >= slots.capacity) {
        showToast(`Parking full on ${arrivalDate}. Please choose another date.`, 'error')
        setSaving(false)
        return
      }

      setSlotId(slots.id)
      setStep(3)
    } catch (err) {
      console.error(err)
      showToast(err.message || 'Error checking availability.', 'error')
    } finally {
      setSaving(false)
    }
  }

  // ── STEP 3: Open payment modal ────────────────────────────
  function handleConfirmClick() {
    setShowPayModal(true)
  }

  // ── Payment confirmed → insert booking + payment ─────────
  async function handlePaymentSuccess() {
    setSaving(true)

    try {
      // Calculate exit date
      const entry = new Date(arrivalDate)
      const exit  = new Date(arrivalDate)

      if      (selectedPlan.id === 'daily')   exit.setDate(entry.getDate() + 1)
      else if (selectedPlan.id === 'weekly')  exit.setDate(entry.getDate() + 7)
      else if (selectedPlan.id === 'monthly') exit.setMonth(entry.getMonth() + 1)
      else if (selectedPlan.id === 'yearly')  exit.setFullYear(entry.getFullYear() + 1)

      // 1. Insert booking — matches your schema exactly
      const { data: booking, error: bookingError } = await supabase
        .from('bookings')
        .insert({
          user_id:         user.id,
          vehicle_id:      vehicleId,
          slot_id:         slotId,
          plan:            selectedPlan.id,
          scheduled_entry: entry.toISOString().slice(0, 10),  // date only
          scheduled_exit:  exit.toISOString().slice(0, 10),   // date only
          amount:          selectedPlan.price,
          status:          'confirmed',
        })
        .select('id')
        .single()

      if (bookingError) throw bookingError

      // 2. Insert payment
      const { error: paymentError } = await supabase
        .from('payments')
        .insert({
          booking_id:     booking.id,
          method:         payMethod,
          status:         'success',
          amount:         selectedPlan.price,
          transaction_id: 'SP-' + Math.floor(100000 + Math.random() * 900000),
          paid_at:        new Date().toISOString(),
        })

      if (paymentError) throw paymentError

      const displayId = 'SP-' + booking.id.slice(0, 8).toUpperCase()
      setShowPayModal(false)
      setBookingId(displayId)
      setSuccess(true)
      showToast(`Payment confirmed! Booking: ${displayId}`, 'success')

    } catch (err) {
      console.error(err)
      showToast('Something went wrong. Try again.', 'error')
    } finally {
      setSaving(false)
    }
  }

  // ── Reset ─────────────────────────────────────────────────
  function handleRegisterAnother() {
    setStep(1); setSuccess(false); setBookingId('')
    setVehicleNumber(''); setVnumError('')
    setArrivalDate(new Date().toISOString().slice(0, 10))
    setVehicleType('2-wheeler')
    setSelectedPlan(PARKING_PLANS[0])
    setPayMethod('upi'); setUpiId('')
    setVehicleId(null); setSlotId(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0D1B2A] flex items-center justify-center">
        <div className="text-[#8DA4BF] text-sm">Loading...</div>
      </div>
    )
  }

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

      {/* Payment Modal */}
      {showPayModal && (
        <PaymentModal
          plan={selectedPlan}
          method={payMethod}
          upiId={upiId}
          processing={saving}
          onSuccess={handlePaymentSuccess}
          onCancel={() => setShowPayModal(false)}
        />
      )}

      {/* Split layout */}
      <div className="relative z-10 min-h-screen grid grid-cols-1 lg:grid-cols-[1fr_1.15fr]">

        {/* LEFT PANEL — unchanged */}
        <div className="hidden lg:flex p-16 border-r border-[#1E3550] flex-col justify-center">
          <div className="mb-11"><Brand /></div>
          <h1 className="text-[34px] font-extrabold leading-tight tracking-tight text-white mb-3"
            style={{ fontFamily: 'Syne, sans-serif' }}>
            Register your<br /><span className="text-cyan-400">vehicle.</span>
          </h1>
          <p className="text-sm text-[#8DA4BF] leading-relaxed mb-9 max-w-xs">
            Complete registration and payment to activate your smart parking pass. Our ANPR system handles the rest.
          </p>
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
          <button onClick={() => navigate('/')}
            className="w-fit py-2.5 px-5 bg-transparent border border-[#1E3550] rounded-xl text-[13px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition">
            ← Back to Home
          </button>
        </div>

        {/* RIGHT PANEL */}
        <div className="p-6 md:p-14 flex items-center justify-center overflow-y-auto">
          <div className="w-full max-w-[500px]">

            {success ? (
              <SuccessScreen bookingId={bookingId} onRegisterAnother={handleRegisterAnother} />
            ) : (
              <>
                <h2 className="text-[22px] font-bold text-white mb-1" style={{ fontFamily: 'Syne, sans-serif' }}>
                  Vehicle Registration
                </h2>
                <p className="text-[13px] text-[#8DA4BF] mb-6">
                  Logged in as:{' '}
                  <strong className="text-cyan-400">{user?.profile?.phone || user?.email}</strong>
                </p>

                <StepIndicator step={step} />

                {/* STEP 1 — unchanged */}
                {step === 1 && (
                  <div className="space-y-5 animate-fade-in">
                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">Vehicle Number</label>
                      <div className="relative">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">🔢</span>
                        <input
                          type="text"
                          value={vehicleNumber}
                          onChange={(e) => { setVehicleNumber(e.target.value.toUpperCase()); setVnumError('') }}
                          placeholder="e.g. KL 11 AB 1234"
                          className={`w-full bg-[#0D1B2A] border rounded-[10px] py-3 pl-10 text-sm text-white placeholder-[#8DA4BF] outline-none transition uppercase
                            ${vnumError ? 'border-red-500' : 'border-[#1E3550] focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10'}`}
                        />
                      </div>
                      {vnumError && <p className="text-[11px] text-red-400 mt-1.5">{vnumError}</p>}
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">Date of Arrival</label>
                      <div className="relative">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">📅</span>
                        <input
                          type="date"
                          value={arrivalDate}
                          onChange={(e) => setArrivalDate(e.target.value)}
                          min={new Date().toISOString().slice(0, 10)}
                          className="w-full bg-[#0D1B2A] border border-[#1E3550] rounded-[10px] py-3 pl-10 text-sm text-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition"
                          style={{ colorScheme: 'dark' }}
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">Vehicle Type</label>
                      <div className="grid grid-cols-3 gap-3">
                        {VEHICLE_TYPES.map((v) => (
                          <button key={v.id} onClick={() => setVehicleType(v.id)}
                            className={`border rounded-[10px] py-3 px-2 text-center transition-all
                              ${vehicleType === v.id ? 'border-blue-500 bg-blue-500/10' : 'border-[#1E3550] bg-[#0D1B2A] hover:border-blue-500/50'}`}>
                            <span className="text-[22px] block mb-1">{v.emoji}</span>
                            <span className={`text-[11px] ${vehicleType === v.id ? 'text-white' : 'text-[#8DA4BF]'}`}>{v.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    <button onClick={handleStep1} disabled={saving}
                      className="w-full py-[15px] bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[15px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all disabled:opacity-60">
                      {saving ? 'Saving...' : 'Continue to Payment →'}
                    </button>
                  </div>
                )}

                {/* STEP 2 — unchanged UI, but button now checks availability */}
                {step === 2 && (
                  <div className="space-y-5 animate-fade-in">
                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-3">Select Plan</label>
                      <div className="grid grid-cols-2 gap-3">
                        {PARKING_PLANS.map((plan) => (
                          <button key={plan.id} onClick={() => setSelectedPlan(plan)}
                            className={`relative border rounded-xl p-3.5 text-left transition-all
                              ${selectedPlan.id === plan.id ? 'border-cyan-400 bg-cyan-400/6' : 'border-[#1E3550] bg-[#0D1B2A] hover:border-blue-500/50'}`}>
                            {plan.popular && (
                              <span className="absolute -top-2 right-2 bg-blue-600 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide">Popular</span>
                            )}
                            <div className="text-[13px] font-semibold text-white mb-0.5">{plan.label}</div>
                            <div className="text-[20px] font-bold text-cyan-400" style={{ fontFamily: 'Syne, sans-serif' }}>₹{plan.price}</div>
                            <div className="text-[11px] text-[#8DA4BF]">{plan.period}</div>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="bg-[#0D1B2A] border border-[#1E3550] rounded-xl px-5 py-4 flex items-center justify-between">
                      <div>
                        <div className="text-[13px] text-[#8DA4BF]">Amount to Pay</div>
                        <div className="text-[12px] text-[#8DA4BF] mt-0.5">{selectedPlan.label}</div>
                      </div>
                      <div className="text-[26px] font-bold text-cyan-400" style={{ fontFamily: 'Syne, sans-serif' }}>₹{selectedPlan.price}</div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-3">Payment Method</label>
                      <div className="flex gap-3">
                        {PAY_METHODS.map((m) => (
                          <button key={m.id} onClick={() => setPayMethod(m.id)}
                            className={`flex-1 border rounded-[10px] py-3 text-center transition-all
                              ${payMethod === m.id ? 'border-blue-500 bg-blue-500/10 text-white' : 'border-[#1E3550] bg-[#0D1B2A] text-[#8DA4BF] hover:border-blue-500/50 hover:text-white'}`}>
                            <span className="text-xl block mb-1">{m.icon}</span>
                            <span className="text-[12px]">{m.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {payMethod === 'upi' && (
                      <div className="animate-fade-in">
                        <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">UPI ID</label>
                        <div className="relative">
                          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-[#8DA4BF] pointer-events-none">@</span>
                          <input
                            type="text"
                            value={upiId}
                            onChange={(e) => setUpiId(e.target.value)}
                            placeholder="e.g. yourname@upi"
                            className="w-full bg-[#0D1B2A] border border-[#1E3550] rounded-[10px] py-3 pl-9 text-sm text-white placeholder-[#8DA4BF] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition"
                          />
                        </div>
                        <p className="text-[11px] text-[#8DA4BF] mt-1.5">Enter your UPI ID to proceed with payment</p>
                      </div>
                    )}

                    <div className="flex gap-3 pt-1">
                      <button onClick={() => setStep(1)}
                        className="flex-1 py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition">
                        ← Back
                      </button>
                      <button onClick={handleStep2} disabled={saving}
                        className="flex-[2] py-3.5 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all disabled:opacity-60">
                        {saving ? 'Checking availability...' : 'Review & Confirm →'}
                      </button>
                    </div>
                  </div>
                )}

                {/* STEP 3 — same summary, button opens modal */}
                {step === 3 && (
                  <div className="animate-fade-in">
                    <div className="bg-[#0D1B2A] border border-[#1E3550] rounded-xl p-4 mb-5">
                      <SummaryRow label="Name"            value={user?.profile?.name || '—'} />
                      <SummaryRow label="Phone"           value={user?.profile?.phone || '—'} />
                      <SummaryRow label="Vehicle Number"  value={vehicleNumber} />
                      <SummaryRow label="Vehicle Type"    value={vehicleType} />
                      <SummaryRow label="Date of Arrival" value={arrivalDate} />
                      <SummaryRow label="Plan"            value={selectedPlan.label} />
                      <SummaryRow label="Payment Method"  value={payMethod.toUpperCase()} />
                      <SummaryRow label="Total Amount"    value={`₹${selectedPlan.price}`} highlight />
                    </div>

                    {/* Availability badge */}
                    <div className="flex items-center gap-2 bg-emerald-500/8 border border-emerald-500/20 rounded-xl px-4 py-2.5 mb-4">
                      <span className="text-emerald-400 text-sm">✓</span>
                      <span className="text-[12px] text-emerald-400">Parking slot available for selected date</span>
                    </div>

                    <div className="flex gap-3">
                      <button onClick={() => setStep(2)}
                        className="flex-1 py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition">
                        ← Back
                      </button>
                      <button onClick={handleConfirmClick} disabled={saving}
                        className="flex-[2] py-3.5 bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[14px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all disabled:opacity-60">
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