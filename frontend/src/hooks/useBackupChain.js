import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'

export function useBackupChain() {
  const [source, setSource] = useState(null)
  const [backups, setBackups] = useState([])
  const [verification, setVerification] = useState(null)

  const refresh = useCallback(async () => {
    const [nextSource, nextBackups] = await Promise.all([api.getSourceState(), api.getBackups()])
    setSource(nextSource)
    setBackups(nextBackups)
    return { source: nextSource, backups: nextBackups }
  }, [])

  useEffect(() => { refresh() }, [refresh])
  return { source, backups, verification, setVerification, refresh }
}
