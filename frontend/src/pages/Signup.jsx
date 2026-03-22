import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import PasswordInput from '../components/PasswordInput'
import Toast from '../components/Toast'
import useTimer from '../hooks/useTimer'
import { MOCK_OTP } from '../data/mockData'
import AuthCard from '../components/AuthCard'
import ProgressBars from '../components/ProgressBars'
import OTPInput from '../components/OTPInput'
import { getPasswordStrength } from '../utils/passwordStrength'

const OTP_LENGTH = 6

export default function Signup() {
  const navigate = useNavigate()
  const timer = useTimer(30)

  // ── Step state (1 | 2 | 3) ──────────────────────────────
  const [step, setStep] = useState(1)

  // ── Step 1 fields ───────────────────────────────────────
  const [name,    setName]    = useState('')
  const [phone,   setPhone]   = useState('')
  const [errors1, setErrors1] = useState({ name: '', phone: '' })

  // ── Step 2: OTP ─────────────────────────────────────────
  const [otp,         setOtp]         = useState(Array(OTP_LENGTH).fill(''))
  const [otpError,    setOtpError]    = useState('')
  const [otpVerified, setOtpVerified] = useState(false)
  const inputRefs = useRef([])

  // ── Step 3: Password ─────────────────────────────────────
  const [password, setPassword] = useState('')
  const [confirm,  setConfirm]  = useState('')
  const [errors3,  setErrors3]  = useState({ password: '', confirm: '' })
  const strength = getPasswordStrength(password)

  // ── Toast ────────────────────────────────────────────────
  const [toast, setToast] = useState({ message: '', type: 'success' })
  const showToast  = (message, type = 'success') => setToast({ message, type })
  const clearToast = () => setToast({ message: '', type: 'success' })

  const stepLabels = {
    1: 'Your details',
    2: 'Verify phone',
    3: 'Set password',
  }

  // ─────────────────────────────────────────────────────────
  // STEP 1 — validate and send OTP
  // ─────────────────────────────────────────────────────────
  function handleStep1() {
    const errs = { name: '', phone: '' }
    if (name.trim().length < 2)  errs.name  = 'Enter your full name (min 2 characters)'
    if (!/^\d{10}$/.test(phone)) errs.phone = 'Enter a valid 10-digit phone number'
    setErrors1(errs)
    if (errs.name || errs.phone) return

    // ── API-READY ──────────────────────────────────────────
    // await supabase.auth.signInWithOtp({ phone: '+91' + phone })
    // ──────────────────────────────────────────────────────
    showToast(`OTP sent to +91 ${phone}  (Demo OTP: ${MOCK_OTP})`, 'success')
    setOtp(Array(OTP_LENGTH).fill(''))
    setOtpError('')
    setOtpVerified(false)
    setStep(2)
    timer.start()
    setTimeout(() => inputRefs.current[0]?.focus(), 100)
  }

  // ─────────────────────────────────────────────────────────
  // STEP 2 — verify OTP
  // ─────────────────────────────────────────────────────────
  function handleStep2() {
    if (otpVerified) { setStep(3); return }

    const entered = otp.join('')
    if (entered.length < OTP_LENGTH) {
      setOtpError('Please enter the complete 6-digit OTP')
      return
    }

    // ── API-READY ──────────────────────────────────────────
    // const { data, error } = await supabase.auth.verifyOtp({
    //   phone: '+91' + phone, token: entered, type: 'sms'
    // })
    // if (error) { setOtpError('Invalid OTP'); return }
    // ──────────────────────────────────────────────────────

    if (entered !== MOCK_OTP) {
      setOtpError('Incorrect OTP — please try again')
      return
    }

    setOtpError('')
    setOtpVerified(true)
    timer.reset()
    setTimeout(() => setStep(3), 300)
  }

  // ─────────────────────────────────────────────────────────
  // STEP 3 — create account
  // ─────────────────────────────────────────────────────────
  function handleStep3() {
    const errs = { password: '', confirm: '' }
    if (password.length < 8)  errs.password = 'Password must be at least 8 characters'
    if (password !== confirm) errs.confirm  = 'Passwords do not match'
    setErrors3(errs)
    if (errs.password || errs.confirm) return

    // ── API-READY ──────────────────────────────────────────
    // const { data, error } = await supabase.auth.signUp({
    //   phone: '+91' + phone,
    //   password,
    //   options: { data: { name } }
    // })
    // if (error) { showToast(error.message, 'error'); return }
    // ──────────────────────────────────────────────────────

    showToast('Account created! Please sign in.', 'success')
    setTimeout(() => navigate('/'), 1500)
  }

  // ─────────────────────────────────────────────────────────
  // OTP box handlers
  // ─────────────────────────────────────────────────────────
  const handleOtpChange = useCallback((e, idx) => {
    const val = e.target.value.replace(/\D/g, '').slice(-1)
    const next = [...otp]
    next[idx] = val
    setOtp(next)
    setOtpError('')
    if (val && idx < OTP_LENGTH - 1) inputRefs.current[idx + 1]?.focus()
  }, [otp])

  const handleOtpKeyDown = useCallback((e, idx) => {
    if (e.key === 'Backspace' && !otp[idx] && idx > 0) {
      inputRefs.current[idx - 1]?.focus()
    }
  }, [otp])

  // ─────────────────────────────────────────────────────────
  // Resend OTP
  // ─────────────────────────────────────────────────────────
  function handleResend() {
    // ── API-READY: re-trigger OTP ──────────────────────────
    showToast(`OTP resent! (Demo OTP: ${MOCK_OTP})`, 'success')
    setOtp(Array(OTP_LENGTH).fill(''))
    setOtpError('')
    setOtpVerified(false)
    timer.start()
    setTimeout(() => inputRefs.current[0]?.focus(), 100)
  }

  // ─────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────
  return (
    <AuthCard>
      <h1 className="text-[22px] font-bold text-white mb-1" style={{ fontFamily: 'Syne, sans-serif' }}>
        Create your account
      </h1>
      <p className="text-[13px] text-[#8DA4BF] mb-6">
        Step {step} of 3 — {stepLabels[step]}
      </p>

      <ProgressBars step={step} />

      {/* ══ STEP 1: Name + Phone ══ */}
      {step === 1 && (
        <div className="space-y-4 animate-fade-in">
          <div>
            <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
              Full Name
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">👤</span>
              <input
                type="text"
                value={name}
                onChange={(e) => { setName(e.target.value); setErrors1((p) => ({ ...p, name: '' })) }}
                placeholder="e.g. Arjun Kumar"
                className={`w-full bg-[#0D1B2A] border rounded-[10px] py-3 pl-10 text-sm text-white placeholder-[#8DA4BF] outline-none transition
                  ${errors1.name
                    ? 'border-red-500'
                    : 'border-[#1E3550] focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10'
                  }`}
              />
            </div>
            {errors1.name && <p className="text-[11px] text-red-400 mt-1.5">{errors1.name}</p>}
          </div>

          <div>
            <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
              Phone Number{' '}
              <span className="text-cyan-400 normal-case tracking-normal text-[10px]">
                — This will be your User ID
              </span>
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">📱</span>
              <input
                type="tel"
                value={phone}
                onChange={(e) => {
                  setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))
                  setErrors1((p) => ({ ...p, phone: '' }))
                }}
                placeholder="10-digit mobile number"
                className={`w-full bg-[#0D1B2A] border rounded-[10px] py-3 pl-10 text-sm text-white placeholder-[#8DA4BF] outline-none transition
                  ${errors1.phone
                    ? 'border-red-500'
                    : 'border-[#1E3550] focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10'
                  }`}
              />
            </div>
            {errors1.phone
              ? <p className="text-[11px] text-red-400 mt-1.5">{errors1.phone}</p>
              : <p className="text-[11px] text-[#8DA4BF] mt-1.5">An OTP will be sent to verify this number</p>
            }
          </div>

          <button
            onClick={handleStep1}
            className="w-full py-[15px] bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[15px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all mt-2"
          >
            Send OTP →
          </button>
          <button
            onClick={() => navigate('/')}
            className="w-full py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition"
          >
            ← Back to Login
          </button>
        </div>
      )}

      {/* ══ STEP 2: OTP ══ */}
      {step === 2 && (
        <div className="animate-fade-in">
          <div className="bg-blue-500/8 border border-blue-500/25 rounded-xl px-4 py-3 mb-5 text-[13px] text-[#8DA4BF]">
            OTP sent to{' '}
            <strong className="text-cyan-400">
              +91 {phone.replace(/(\d{5})(\d{5})/, '$1 $2')}
            </strong>
          </div>

          <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-3">
            Enter 6-digit OTP
          </label>

          <OTPInput
            inputRefs={inputRefs}
            values={otp}
            onChange={handleOtpChange}
            onKeyDown={handleOtpKeyDown}
            hasError={!!otpError}
          />

          {otpError && (
            <p className="text-[11px] text-red-400 mt-2">{otpError}</p>
          )}
          {otpVerified && (
            <div className="flex items-center gap-2 mt-3 px-3.5 py-2.5 bg-emerald-500/8 border border-emerald-500/30 rounded-[10px] text-[13px] text-emerald-400">
              ✅ Phone number verified successfully
            </div>
          )}

          <div className="flex items-center justify-between mt-4">
            <button
              onClick={handleResend}
              disabled={timer.running}
              className="text-[13px] font-medium text-cyan-400 disabled:text-[#8DA4BF] disabled:cursor-not-allowed hover:underline"
            >
              Resend OTP
            </button>
            {timer.running && (
              <span className="text-[13px] text-[#8DA4BF]">
                Resend in <strong className="text-white">{timer.count}s</strong>
              </span>
            )}
          </div>

          <button
            onClick={handleStep2}
            className="w-full py-[15px] bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[15px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all mt-5"
          >
            {otpVerified ? 'Continue →' : 'Verify & Continue →'}
          </button>
          <button
            onClick={() => { setStep(1); timer.reset(); setOtpVerified(false) }}
            className="w-full py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition mt-2"
          >
            ← Back
          </button>
        </div>
      )}

      {/* ══ STEP 3: Password ══ */}
      {step === 3 && (
        <div className="space-y-4 animate-fade-in">
          <div>
            <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
              Create Password
            </label>
            <PasswordInput
              value={password}
              onChange={(e) => { setPassword(e.target.value); setErrors3((p) => ({ ...p, password: '' })) }}
              placeholder="Minimum 8 characters"
              className={errors3.password ? 'border-red-500' : ''}
            />
            <div className="flex gap-1 mt-2">
              {[1, 2, 3].map((n) => (
                <div
                  key={n}
                  className={`flex-1 h-[3px] rounded-full transition-all duration-300
                    ${strength.level >= n ? strength.color : 'bg-[#1E3550]'}`}
                />
              ))}
            </div>
            {strength.label && (
              <p className={`text-[11px] mt-1 ${
                strength.level === 1 ? 'text-red-400' :
                strength.level === 2 ? 'text-orange-400' : 'text-emerald-400'
              }`}>
                {strength.label}
              </p>
            )}
            {errors3.password && (
              <p className="text-[11px] text-red-400 mt-1">{errors3.password}</p>
            )}
          </div>

          <div>
            <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
              Confirm Password
            </label>
            <PasswordInput
              value={confirm}
              onChange={(e) => { setConfirm(e.target.value); setErrors3((p) => ({ ...p, confirm: '' })) }}
              placeholder="Re-enter your password"
              className={errors3.confirm ? 'border-red-500' : ''}
            />
            {errors3.confirm && (
              <p className="text-[11px] text-red-400 mt-1">{errors3.confirm}</p>
            )}
          </div>

          <button
            onClick={handleStep3}
            className="w-full py-[15px] bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[15px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all mt-2"
          >
            Create Account ✓
          </button>
          <button
            onClick={() => setStep(2)}
            className="w-full py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition"
          >
            ← Back
          </button>
        </div>
      )}

      <Toast message={toast.message} type={toast.type} onClose={clearToast} />
    </AuthCard>
  )
}