// ─────────────────────────────────────────────────────────────
// MOCK DATA — replace each section with real API calls later
// ─────────────────────────────────────────────────────────────

export const MOCK_OTP = '123456' // In production: generated server-side

export const MOCK_USER = {
  phone: '9633930481',
  password: 'password123',
  name: 'Midhun Madhav A R',
}

export const MOCK_ADMIN = {
  id: 'admin',
  password: 'admin123',
}

export const MOCK_VEHICLES = [
  { id: 1, vehicleNumber: 'KL 11 AB 1234', owner: 'Nimal Krishna',  type: '4-Wheeler', entryTime: '09:14 AM', duration: '2h 31m', plan: 'Daily',   status: 'inside' },
  { id: 2, vehicleNumber: 'TN 09 XY 5678', owner: 'Vijay',          type: '2-Wheeler', entryTime: '09:30 AM', duration: '1h 58m', plan: 'Weekly',  status: 'inside' },
  { id: 3, vehicleNumber: 'MH 12 EF 9090', owner: 'Akshay Khanna',  type: 'SUV / Van', entryTime: '10:00 AM', duration: '0h 45m', plan: 'Daily',   status: 'exited' },
  { id: 4, vehicleNumber: 'KA 05 JK 3344', owner: 'Ballaya',        type: '4-Wheeler', entryTime: '10:22 AM', duration: '0h 23m', plan: 'Monthly', status: 'inside' },
]

export const MOCK_LOGS = [
  { id: 1, timestamp: '11:45 AM', vehicleNumber: 'DL 01 MN 7788', event: 'Entry', duration: '—',      confidence: '98.4%', flag: null       },
  { id: 2, timestamp: '10:48 AM', vehicleNumber: 'MH 12 GH 9090', event: 'Exit',  duration: '0h 45m', confidence: '96.1%', flag: null       },
  { id: 3, timestamp: '10:22 AM', vehicleNumber: 'KA 05 JK 3344', event: 'Entry', duration: '—',      confidence: '72.3%', flag: 'Low Conf' },
  { id: 4, timestamp: '09:47 AM', vehicleNumber: 'TN 09 XY 5678', event: 'Entry', duration: '—',      confidence: '99.1%', flag: null       },
  { id: 5, timestamp: '09:14 AM', vehicleNumber: 'KL 11 AB 1234', event: 'Entry', duration: '—',      confidence: '95.6%', flag: null       },
  { id: 6, timestamp: '08:50 AM', vehicleNumber: 'XX 00 ZZ 0000', event: 'Entry', duration: '—',      confidence: '61.2%', flag: 'Low Conf' },
]

export const MOCK_STATS = {
  totalToday: 34,
  currentlyInside: 13,
  availableSlots: 37,
  totalSlots: 50,
  revenue: '₹4,820',
  occupancyPercent: 26,
}

export const MOCK_CAMERAS = [
  { id: 1, name: 'Entry Camera', status: 'online', fps: 24, confidence: '96.4%', resolution: '1080p' },
  { id: 2, name: 'Exit Camera',  status: 'online', fps: 22, confidence: '94.1%', resolution: '1080p' },
]

export const PARKING_PLANS = [
  { id: 'daily',   label: 'Daily Pass',   price: 30,   period: 'per day',    popular: false },
  { id: 'weekly',  label: 'Weekly Pass',  price: 150,  period: 'per 7 days', popular: true  },
  { id: 'monthly', label: 'Monthly Pass', price: 500,  period: 'per month',  popular: false },
  { id: 'yearly',  label: 'Yearly Pass',  price: 5000, period: 'per year',   popular: false },
]