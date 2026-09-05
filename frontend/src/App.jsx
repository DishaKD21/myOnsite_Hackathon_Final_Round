import { useCallback, useEffect, useState } from 'react'
import { apiBaseUrl, getSourceState, uploadSourceFiles, seedSource, modifySource, addSource, deleteSource } from './api/sourceApi'
import { getBackups, getBackupDetails, createFullBackup, createIncrementalBackup, validateBackup, findAlternate, verifyAlternate } from './api/backupApi'
import { verifyChain } from './api/chainApi'
import { restore, verifyRestore } from './api/recoveryApi'
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
      const [nextSource, nextBackups] = await Promise.all([getSourceState(), getBackups()])
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
    try { setSelectedBackup(await getBackupDetails(id)); setError('') } catch (requestError) { setError(requestError.message) }
  }

  const verifyChainAction = () => run(async () => { const result = await verifyChain(); setVerification(result); return result }, 'Chain verification updated.')
  const createFullAction = () => run(createFullBackup, 'Full backup created.')
  const createIncrementalAction = () => run(createIncrementalBackup, 'Incremental backup created.')
  const seed = (files) => run(() => seedSource(files), 'Source seeded.')
  const upload = (files) => run(() => uploadSourceFiles(files), 'Source files uploaded.')
  const modify = (fileId, content) => run(() => modifySource(fileId, content), 'Source file modified.')
  const add = (fileId, filename, content) => run(() => addSource(fileId, filename, content), 'Source file added.')
  const remove = (fileId) => run(() => deleteSource(fileId), 'Source file deleted.')
  const validate = (id) => run(async () => { const result = await validateBackup(id); setValidation(result); return result }, 'Backup validation completed.', async () => {})
  const findAlternateAction = (id) => run(async () => { const result = await findAlternate(id); setAlternateResult(result); return result }, 'Alternate search completed.', async () => {})
  const verifyAlternateAction = (id, alternateId) => run(async () => { const result = await verifyAlternate(id, alternateId); setAlternateResult((current) => ({ ...current, verification: result })); if (result.accepted) { setVerification(await verifyChain()) } return result }, 'Alternate verification completed.')
  const restoreAction = (id) => run(async () => { const result = await restore(id); setRestoreResult(result); setRestoreVerification(null); return result }, 'Restore operation completed.', async () => {})
  const verifyRestoreAction = (id) => run(async () => { const result = await verifyRestore(id); setRestoreVerification(result); return result }, 'Restore verification completed.', async () => {})

  return (
    <div className="app-shell">
      <Header connected={connected} onRefresh={() => refresh()} refreshing={refreshing} apiUrl={apiBaseUrl} />
      <main>
        <section className="hero-strip">
          <div>
            <p className="eyebrow">Recovery evidence, at a glance</p>
            <h2>Know which backup you can trust.</h2>
            <p>Trace every dependency from the full snapshot to the latest safe recovery point.</p>
          </div>
          <div className="hero-metric">
            <span>Safe recovery point</span>
            <strong>{verification?.latest_safe_recovery_point || '-'}</strong>
            <small>{verification?.chain_status ? verification.chain_status.replaceAll('_', ' ') : 'Not verified yet'}</small>
          </div>
        </section>

        {error && (
          <div className="alert alert-error" role="alert">
            <strong>Request failed</strong>
            <span>{error}</span>
            <button type="button" onClick={() => setError('')}>Dismiss</button>
          </div>
        )}

        {notice && (
          <div className="alert alert-success" role="status">
            <strong>Operation complete</strong>
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice('')}>Dismiss</button>
          </div>
        )}

        <div className="dashboard-grid">
          <SourcePanel source={source} onSeed={seed} onUpload={upload} onModify={modify} onAdd={add} onDelete={remove} busy={busy} />
          <BackupChain backups={backups} selectedId={selectedId} onSelect={selectBackup} verification={verification} />
          <BackupDetails backup={selectedBackup} validation={validation} onValidate={validate} onFindAlternate={findAlternate} busy={busy} />
          <VerificationPanel verification={verification} onVerify={verifyChainAction} busy={busy} />
          <RecoveryPanel backups={backups} verification={verification} restoreResult={restoreResult} restoreVerification={restoreVerification} onRestore={restoreAction} onVerifyRestore={verifyRestoreAction} busy={busy} />
          <DemoControls backups={backups} onFindAlternate={findAlternateAction} alternateResult={alternateResult} onVerifyAlternate={verifyAlternateAction} onCreateFull={createFullAction} onCreateIncremental={createIncrementalAction} busy={busy} />
        </div>
      </main>
      <footer>
        <span>BackupChain local console</span>
        <span>API - {apiBaseUrl}</span>
      </footer>
    </div>
  )
}
