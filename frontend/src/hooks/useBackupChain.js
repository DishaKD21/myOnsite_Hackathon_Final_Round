import { useCallback, useEffect, useState } from 'react'
import { getSourceState } from '../api/sourceApi'
import { getBackups } from '../api/backupApi'

export function useBackupChain() {
  const [source, setSource] = useState(null)
  const [backups, setBackups] = useState([])
  const [verification, setVerification] = useState(null)

  const refresh = useCallback(async () => {
    const [nextSource, nextBackups] = await Promise.all([getSourceState(), getBackups()])
    setSource(nextSource)
    setBackups(nextBackups)
    return { source: nextSource, backups: nextBackups }
  }, [])

  useEffect(() => { refresh() }, [refresh])
  return { source, backups, verification, setVerification, refresh }
}
