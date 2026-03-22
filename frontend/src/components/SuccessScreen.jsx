import { useNavigate } from 'react-router-dom'

export default function SuccessScreen({ bookingId, onRegisterAnother }) {
  const navigate = useNavigate()

  return (
    <div className="text-center py-5 animate-fade-in">
      {/* Animated check circle */}
      <div className="w-20 h-20 rounded-full bg-emerald-500/12 border-2 border-emerald-500 flex items-center justify-center text-4xl mx-auto mb-5"
        style={{ animation: 'pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards' }}>
        ✅
      </div>

      <h2 className="text-[22px] font-bold text-white mb-2" style={{ fontFamily: 'Syne, sans-serif' }}>
        You're all set!
      </h2>
      <p className="text-[13px] text-[#8DA4BF] leading-relaxed mb-6">
        Your vehicle has been registered.<br />
        Show up — the camera will do the rest.
      </p>

      {/* Booking ID */}
      <div className="bg-[#0D1B2A] border border-[#1E3550] rounded-xl py-3 px-4 font-bold text-xl tracking-[3px] text-cyan-400 mb-6"
        style={{ fontFamily: 'Syne, sans-serif' }}>
        {bookingId}
      </div>

      <button
        onClick={onRegisterAnother}
        className="w-full py-[15px] bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl text-white text-[15px] font-semibold hover:-translate-y-px hover:shadow-lg hover:shadow-blue-600/30 transition-all mb-3"
      >
        Register Another Vehicle
      </button>
      <button
        onClick={() => navigate('/')}
        className="w-full py-3.5 bg-transparent border border-[#1E3550] rounded-xl text-[14px] font-medium text-[#8DA4BF] hover:border-[#8DA4BF] hover:text-white transition"
      >
        Back to Home
      </button>

      <style>{`
        @keyframes pop {
          from { transform: scale(0.85); opacity: 0; }
          to   { transform: scale(1);    opacity: 1; }
        }
      `}</style>
    </div>
  )
}