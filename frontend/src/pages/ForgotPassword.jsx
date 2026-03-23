import { useNavigate } from 'react-router-dom'
import AuthCard from '../components/AuthCard'
 
export default function ForgotPassword() {
  const navigate = useNavigate()
 
  return (
    <AuthCard>
      <div className="text-center">
        {/* Icon */}
        <div className="w-16 h-16 bg-[#0D1B2A] border border-[#1E3550] rounded-2xl flex items-center justify-center text-3xl mx-auto mb-6">
          🔑
        </div>
 
        <h1
          className="text-[22px] font-bold text-white mb-2"
          style={{ fontFamily: 'Syne, sans-serif' }}
        >
          Password Reset
        </h1>
 
        <p className="text-[13px] text-[#8DA4BF] leading-relaxed mb-8">
          SmartPark uses <span className="text-white font-medium">Google Sign-In</span> — you don't have a
          separate password here. Your account security is managed by Google.
        </p>
 
        {/* Google info card */}
        <div className="bg-[#0D1B2A] border border-[#1E3550] rounded-xl p-5 mb-6 text-left">
          <p className="text-[12px] font-semibold text-[#8DA4BF] uppercase tracking-wide mb-3">
            To reset your Google password:
          </p>
          <div className="space-y-2">
            {[
              'Go to myaccount.google.com',
              'Navigate to Security → Password',
              'Follow Google\'s password reset steps',
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-[10px] font-bold text-blue-400 shrink-0 mt-0.5">
                  {i + 1}
                </div>
                <span className="text-[13px] text-[#8DA4BF]">{step}</span>
              </div>
            ))}
          </div>
        </div>
 
        {/* Google account link */}
        <a
          href="https://myaccount.google.com/security"
          target="_blank"
          rel="noopener noreferrer"
          className="w-full flex items-center justify-center gap-3 py-[14px] bg-white hover:bg-gray-50 rounded-xl text-[15px] font-semibold text-gray-800 shadow-md hover:shadow-lg transition-all mb-3"
        >
          <svg width="18" height="18" viewBox="0 0 48 48">
            <path fill="#FFC107" d="M43.6 20H24v8h11.3C33.7 33.2 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34.1 6.5 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20c11 0 20-9 20-20 0-1.3-.1-2.7-.4-4z"/>
            <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 15.1 18.9 12 24 12c3 0 5.8 1.1 7.9 3l5.7-5.7C34.1 6.5 29.3 4 24 4 16.3 4 9.7 8.4 6.3 14.7z"/>
            <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.4 35.5 26.8 36 24 36c-5.2 0-9.7-3.3-11.3-8H6.1C9.4 37.7 16.2 44 24 44z"/>
            <path fill="#1976D2" d="M43.6 20H24v8h11.3c-.8 2.2-2.2 4-4.1 5.3l6.2 5.2C40.9 35.1 44 30 44 24c0-1.3-.1-2.7-.4-4z"/>
          </svg>
          Manage Google Account
        </a>
 
        <button
          onClick={() => navigate('/')}
          className="w-full py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition"
        >
          ← Back to Sign In
        </button>
      </div>
    </AuthCard>
  )
}