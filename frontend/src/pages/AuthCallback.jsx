import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import supabase from '../supabase'

export default function AuthCallback() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('Completing sign-in...')

  useEffect(() => {
    async function handleCallback() {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()

        if (error || !session) {
          setStatus('Sign-in failed. Redirecting...')
          setTimeout(() => navigate('/'), 2000)
          return
        }

        const user = session.user

        // Trigger auto-creates the users row — we just check if phone exists
        const { data: existingUser } = await supabase
          .from('users')
          .select('id, phone')
          .eq('id', user.id)
          .single()

        if (!existingUser?.phone) {
          setStatus('Almost there! Complete your profile...')
          setTimeout(() => navigate('/signup'), 800)
        } else {
          setStatus('Welcome back!')
          setTimeout(() => navigate('/register'), 800)
        }

      } catch (err) {
        console.error('AuthCallback error:', err)
        setStatus('Something went wrong. Redirecting...')
        setTimeout(() => navigate('/'), 2000)
      }
    }

    handleCallback()
  }, [navigate])

  return (
    <>
      <div
        className="fixed inset-0 bg-[#0D1B2A] z-0"
        style={{
          backgroundImage: `linear-gradient(rgba(30,111,255,0.04) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(30,111,255,0.04) 1px, transparent 1px)`,
          backgroundSize: '48px 48px',
        }}
      />
      <div className="fixed top-[-120px] right-[-80px] w-[500px] h-[500px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(30,111,255,0.18)', filter: 'blur(120px)' }} />

      <div className="relative z-10 min-h-screen flex items-center justify-center">
        <div className="bg-[#132033] border border-[#1E3550] rounded-2xl p-12 flex flex-col items-center gap-6 shadow-2xl">
          <div className="relative w-16 h-16">
            <div className="absolute inset-0 rounded-full border-4 border-[#1E3550]" />
            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-blue-500 animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-8 h-8 bg-blue-600 rounded-[8px] flex items-center justify-center text-white text-sm font-extrabold">
                P
              </div>
            </div>
          </div>
          <div className="text-center">
            <p className="text-white font-semibold text-[16px] mb-1" style={{ fontFamily: 'Syne, sans-serif' }}>
              SmartPark
            </p>
            <p className="text-[#8DA4BF] text-[14px]">{status}</p>
          </div>
        </div>
      </div>
    </>
  )
}