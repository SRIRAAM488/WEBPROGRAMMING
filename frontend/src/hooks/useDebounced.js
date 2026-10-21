/**
 * useDebounced - delays a fast-changing value (a search box) so we do not fire
 * an API request on every keystroke.
 */

import { useEffect, useState } from 'react'

export default function useDebounced(value, delay = 350) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    // Cancel the pending timer whenever the value changes again.
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}