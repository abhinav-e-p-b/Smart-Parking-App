import { useState } from 'react'

export default function PasswordInput({ id, placeholder, value, onChange, className = '' }) {
  const [show, setShow] = useState(false)

  return (
    <div className="relative">
      <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none">🔑</span>
      <input
        id={id}
        type={show ? 'text' : 'password'}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className={`w-full bg-[#0D1B2A] border border-[#1E3550] rounded-[10px] py-3 pl-10 pr-11 text-sm text-white placeholder-[#8DA4BF] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition ${className}`}
      />
      <button
        type="button"
        onClick={() => setShow(!show)}
        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#8DA4BF] hover:text-white transition"
        tabIndex={-1}
      >
        {show ? '🙈' : '👁'}
      </button>
    </div>
  )
}