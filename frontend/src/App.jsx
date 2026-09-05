import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import Header from './components/common/Header'
import SourcePanel from './components/source/SourcePanel'
import BackupChain from './components/backup/BackupChain'
import BackupDetails from './components/backup/BackupDetails'
import VerificationPanel from './components/chain/VerificationPanel'
import RecoveryPanel from './components/recovery/RecoveryPanel'
import DemoControls from './components/recovery/DemoControls'

export default function App() {
  const [source, setSource] = useState(null)
  const [backups, setBackups] = useState([])
  const [verification, setVerification] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [selectedBackup, setSelectedBackup] = useState(null)
  const [validation, setValidation] = useState(null)
  const [restoreResult, setRestoreResult] = useState(null)
  const [restoreVerification, setRestoreVerification] = useState(null)
  const [alternateResult, setAlternateResult] = useState(null)
  const [connected, setConnected] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const refresh = useCallback(async (showSpinner = true) => {
    if (showSpinner) setRefreshing(true)
    try {
      const [nextSource, nextBackups] = await Promise.all([api.getSourceState(), api.getBackups()])
      setSource(nextSource); setBackups(nextBackups); setConnected(true); setError('')
      if (selectedId && nextBackups.some((item) => item.id === selectedId)) {
        setSelectedBackup(nextBackups.find((item) => item.id === selectedId))
      } else if (!selectedId && nextBackups.length) {
        setSelectedId(nextBackups.at(-1).id); setSelectedBackup(nextBackups.at(-1))
      }
    } catch (requestError) { setConnected(false); setError(requestError.message) } finally { if (showSpinner) setRefreshing(false) }
  }, [selectedId])

  useEffect(() => { refresh() }, [])

  const run = async (operation, successMessage, after = refresh) => {
    setBusy(true); setError(''); setNotice('')
    try { const result = await operation(); if (successMessage) setNotice(successMessage); await after(false); return result }
    catch (requestError) { setError(requestError.message) }
    finally { setBusy(false) }
  }

  const selectBackup = async (id) => {
    setSelectedId(id); setValidation(null); setAlternateResult(null)
    try { setSelectedBackup(await api.getBackupDetails(id)); setError('') } catch (requestError) { setError(requestError.message) }
  }

  const verifyChain = () => run(async () => { const result = await api.verifyChain(); setVerification(result); return result }, 'Chain verification updated.')
  const createFull = () => run(api.createFullBackup, 'Full backup created.')
  const createIncremental = () => run(api.createIncrementalBackup, 'Incremental backup created.')
  const seed = (files) => run(() => api.seedSource(files), 'Source seeded.')
  const modify = (fileId, content) => run(() => api.modifySource(fileId, content), 'Source file modified.')
  const add = (fileId, filename, content) => run(() => api.addSource(fileId, filename, content), 'Source file added.')
  const validate = (id) => run(async () => { const result = await api.validateBackup(id); setValidation(result); return result }, 'Backup validation completed.', async () => {})
  const findAlternate = (id) => run(async () => { const result = await api.findAlternate(id); setAlternateResult(result); return result }, 'Alternate search completed.', async () => {})
  const verifyAlternate = (id, alternateId) => run(async () => { const result = await api.verifyAlternate(id, alternateId); setAlternateResult((current) => ({ ...current, verification: result })); if (result.accepted) { setVerification(await api.verifyChain()) } return result }, 'Alternate verification completed.')
  const restore = (id) => run(async () => { const result = await api.restore(id); setRestoreResult(result); setRestoreVerification(null); return result }, 'Restore operation completed.', async () => {})
  const verifyRestore = (id) => run(async () => { const result = await api.verifyRestore(id); setRestoreVerification(result); return result }, 'Restore verification completed.', async () => {})

  return <div className="app-shell">
    <Header connected={connected} onRefresh={() => refresh()} refreshing={refreshing} apiUrl={api.baseUrl} />
    <main>
      <section className="hero-strip"><div><p className="eyebrow">Recovery evidence, at a glance</p><h2>Know which backup you can trust.</h2><p>Trace every dependency from the full snapshot to the latest safe recovery point.</p></div><div className="hero-metric"><span>Safe recovery point</span><strong>{verification?.latest_safe_recovery_point || '—'}</strong><small>{verification?.chain_status ? verification.chain_status.replaceAll('_', ' ') : 'Not verified yet'}</small></div></section>
      {error && <div className="alert alert-error"><strong>Request failed</strong><span>{error}</span><button onClick={() => setError('')}>Dismiss</button></div>}
      {notice && <div className="alert alert-success"><strong>Operation complete</strong><span>{notice}</span><button onClick={() => setNotice('')}>Dismiss</button></div>}
      <div className="dashboard-grid"><SourcePanel source={source} onSeed={seed} onModify={modify} onAdd={add} busy={busy} /><BackupChain backups={backups} selectedId={selectedId} onSelect={selectBackup} verification={verification} /><BackupDetails backup={selectedBackup} validation={validation} onValidate={validate} onFindAlternate={findAlternate} busy={busy} /><VerificationPanel verification={verification} onVerify={verifyChain} busy={busy} /><RecoveryPanel backups={backups} verification={verification} restoreResult={restoreResult} restoreVerification={restoreVerification} onRestore={restore} onVerifyRestore={verifyRestore} busy={busy} /><DemoControls backups={backups} onFindAlternate={findAlternate} alternateResult={alternateResult} onVerifyAlternate={verifyAlternate} onCreateFull={createFull} onCreateIncremental={createIncremental} busy={busy} /></div>
    </main>
    <footer><span>BackupChain local console</span><span>API · {api.baseUrl}</span></footer>
  </div>
}
