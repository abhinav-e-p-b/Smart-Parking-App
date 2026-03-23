import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
import Toast from '../components/Toast'
import supabase from '../supabase'

export default function Signup() {
  const navigate = useNavigate()

  const [user,       setUser]       = useState(null)
  const [name,       setName]       = useState('')
  const [phone,      setPhone]      = useState('')
  const [nameError,  setNameError]  = useState('')
  const [phoneError, setPhoneError] = useState('')
  const [saving,     setSaving]     = useState(false)

  const [toast, setToast] = useState({ message: '', type: 'success' })
  const showToast  = (msg, type = 'success') => setToast({ message: msg, type })
  const clearToast = () => setToast({ message: '', type: 'success' })

  // Load Google user + pre-fill name if available
  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) { navigate('/'); return }
      setUser(user)
      // Pre-fill name from Google if available
      if (user.user_metadata?.full_name) {
        setName(user.user_metadata.full_name)
      }
    })
  }, [navigate])

  async function handleSubmit() {
    let valid = true

    if (name.trim().length < 2) {
      setNameError('Enter your full name')
      valid = false
    }
    if (!/^\d{10}$/.test(phone)) {
      setPhoneError('Enter a valid 10-digit phone number')
      valid = false
    }
    if (!valid) return

    setSaving(true)
    try {
      // Update users table — email + avatar_url already saved by trigger
      const { error } = await supabase
        .from('users')
        .update({
          name:  name.trim(),
          phone: '+91' + phone,
        })
        .eq('id', user.id)
      console.log('Update result:', data, error)

      if (error) throw error

      showToast('Profile saved! Welcome to SmartPark 🚀', 'success')
      setTimeout(() => navigate('/register'), 1200)

    } catch (err) {
      console.error(err)
      showToast('Failed to save. Try again.', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AuthCard>
      {/* Google account banner */}
      {user && (
        <div className="flex items-center gap-3 bg-[#0D1B2A] border border-[#1E3550] rounded-xl px-4 py-3 mb-6">
          {user.user_metadata?.avatar_url && (
            <img src={user.user_metadata.avatar_url} alt="avatar"
              className="w-8 h-8 rounded-full border border-[#1E3550]" />
          )}
          <div>
            <p className="text-[13px] font-medium text-white">{user.user_metadata?.full_name}</p>
            <p className="text-[11px] text-[#8DA4BF]">{user.email}</p>
          </div>
          <div className="ml-auto">
            <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-full px-2 py-0.5">
              ✓ Google verified
            </span>
          </div>
        </div>
      )}

      <h1 className="text-[22px] font-bold text-white mb-1" style={{ fontFamily: 'Syne, sans-serif' }}>
        Complete your profile
      </h1>
      <p className="text-[13px] text-[#8DA4BF] mb-6">
        Just two more things and you're good to go
      </p>

      <div className="space-y-4">

        {/* Name */}
        <div>
          <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
            Full Name
          </label>
          <div className="relative">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">👤</span>
            <input
              type="text"
              value={name}
              onChange={(e) => { setName(e.target.value); setNameError('') }}
              placeholder="Your full name"
              className={`w-full bg-[#0D1B2A] border rounded-[10px] py-3 pl-10 text-sm text-white placeholder-[#8DA4BF] outline-none transition
                ${nameError ? 'border-red-500' : 'border-[#1E3550] focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10'}`}
            />
          </div>
          {nameError && <p className="text-[11px] text-red-400 mt-1.5">{nameError}</p>}
        </div>

        {/* Phone */}
        <div>
          <label className="block text-[11px] font-medium text-[#8DA4BF] uppercase tracking-wide mb-2">
            Phone Number{' '}
            <span className="text-cyan-400 normal-case tracking-normal text-[10px]">
              — For parking notifications
            </span>
          </label>
          <div className="relative">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">📱</span>
            <input
              type="tel"
              value={phone}
              onChange={(e) => {
                setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))
                setPhoneError('')
              }}
              placeholder="10-digit mobile number"
              className={`w-full bg-[#0D1B2A] border rounded-[10px] py-3 pl-10 text-sm text-white placeholder-[#8DA4BF] outline-none transition
                ${phoneError ? 'border-red-500' : 'border-[#1E3550] focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10'}`}
            />
          </div>
          {phoneError
            ? <p className="text-[11px] text-red-400 mt-1.5">{phoneError}</p>
            : <p className="text-[11px] text-[#8DA4BF] mt-1.5">Used to link with ANPR system</p>
          }
        </div>

        {/* What we already have from Google */}
        <div className="bg-[#0D1B2A] border border-[#1E3550] rounded-xl px-4 py-3">
          <p className="text-[11px] text-[#8DA4BF] uppercase tracking-wide mb-2 font-medium">
            Already saved from Google
          </p>
          <div className="flex gap-4">
            <span className="text-[12px] text-emerald-400">✓ Email</span>
            <span className="text-[12px] text-emerald-400">✓ Profile photo</span>
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={saving}
          className="w-full py-[15px] bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[15px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all disabled:opacity-60"
        >
          {saving ? 'Saving...' : 'Complete Setup ✓'}
        </button>
      </div>

      <Toast message={toast.message} type={toast.type} onClose={clearToast} />
    </AuthCard>
  )
}