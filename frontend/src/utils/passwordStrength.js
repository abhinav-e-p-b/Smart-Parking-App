export function getPasswordStrength(pw) {
  if (!pw) return { level: 0, label: '', color: '' }
  let score = 0
  if (pw.length >= 8)                        score++
  if (/[A-Z]/.test(pw) && /[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw))              score++
  return {
    1: { level: 1, label: 'Weak',   color: 'bg-red-500'     },
    2: { level: 2, label: 'Medium', color: 'bg-orange-400'  },
    3: { level: 3, label: 'Strong', color: 'bg-emerald-500' },
  }[score] || { level: 0, label: '', color: '' }
}