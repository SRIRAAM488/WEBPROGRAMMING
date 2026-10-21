/**
 * useAsync - a small hook for "fetch some data, show loading, show errors".
 *
 * Every page needs the same three states (loading / error / data). Writing that
 * by hand each time invites bugs, so it lives here once.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { getErrorMessage } from '../api/client'

/**
 * @param {Function} loader   async function returning the data
 * @param {Array}    deps     values that should trigger a refetch
 * @param {Object}   options  { immediate, initialData, onSuccess }
 */
export default function useAsync(loader, deps = [], options = {}) {
  const { immediate = true, initialData = null, onSuccess } = options

  const [data, setData] = useState(initialData)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState(null)

  // Guards against setting state after unmount, and against a slow first
  // request overwriting a fast second one.
  const mounted = useRef(true)
  const requestId = useRef(0)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const execute = useCallback(async () => {
    const current = ++requestId.current
    setLoading(true)
    setError(null)
    try {
      const result = await loader()
      if (!mounted.current || current !== requestId.current) return undefined
      setData(result)
      if (onSuccess) onSuccess(result)
      return result
    } catch (err) {
      if (!mounted.current || current !== requestId.current) return undefined
      setError(err)
      return undefined
    } finally {
      if (mounted.current && current === requestId.current) setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    if (immediate) execute()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [execute, immediate])

  return {
    data,
    loading,
    error,
    errorMessage: getErrorMessage(error),
    refresh: execute,
    setData,
  }
}

/** A manual variant - nothing loads until you call `run()`. */
export function useManualAsync(loader) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const run = useCallback(
    async (...args) => {
      setLoading(true)
      setError(null)
      try {
        const result = await loader(...args)
        if (mounted.current) setData(result)
        return result
      } catch (err) {
        if (mounted.current) setError(err)
        throw err
      } finally {
        if (mounted.current) setLoading(false)
      }
    },
    [loader]
  )

  return { data, loading, error, errorMessage: getErrorMessage(error), run, setData }
}