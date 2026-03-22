import { useState, useEffect, useRef } from 'react'

/**
 * useTimer — counts down from `seconds` to 0
 * Returns: { count, running, start, reset }
 */
export default function useTimer(seconds = 30) {
  const [count,   setCount]   = useState(0)
  const [running, setRunning] = useState(false)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!running) return
    intervalRef.current = setInterval(() => {
      setCount((prev) => {
        if (prev <= 1) {
          clearInterval(intervalRef.current)
          setRunning(false)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(intervalRef.current)
  }, [running])

  function start() {
    setCount(seconds)
    setRunning(true)
  }

  function reset() {
    clearInterval(intervalRef.current)
    setRunning(false)
    setCount(0)
  }

  return { count, running, start, reset }
}