import { useCallback, useEffect, useState } from 'react'
import { apiBaseUrl, getSourceState, uploadSourceFiles, deleteSource } from './api/sourceApi'
import { getBackups, getBackupDetails, createFullBackup, createIncrementalBackup, findAlternate, verifyAlternate } from './api/backupApi'
import { verifyChain } from './api/chainApi'
import { restore, verifyRestore } from './api/recoveryApi'
import Header from './components/common/Header'
import SourcePanel from './components/source/SourcePanel'
import BackupChain from './components/backup/BackupChain'
import ProcessLog from './components/common/ProcessLog'
import SimpleControls from './components/common/SimpleControls'

export default function App() {
  const [source, setSource] = useState(null)
  const [backups, setBackups] = useState([])
  const [verification, setVerification] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [selectedBackup, setSelectedBackup] = useState(null)
  const [restoreResult, setRestoreResult] = useState(null)
  const [restoreVerification, setRestoreVerification] = useState(null)
  const [alternateResult, setAlternateResult] = useState(null)
  const [logEntries, setLogEntries] = useState([])
  const [activeOperation, setActiveOperation] = useState('')
  const [activeNode, setActiveNode] = useState('')
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

  const addLog = (message, status = 'completed', details = '') => setLogEntries((current) => [...current, { time: new Date().toLocaleTimeString(), message, status, details }].slice(-40))

  const playSteps = async (title, steps = [], stepHook) => {
    setActiveOperation(title)
    addLog(title, 'running')
    for (const step of steps) {
      await new Promise((resolve) => setTimeout(resolve, 240))
      addLog(step.name.replaceAll('_', ' '), step.status === 'failed' ? 'failed' : 'completed', step.details || '')
      stepHook?.(step)
    }
    setActiveOperation('')
    setActiveNode('')
  }

  const run = async (operation, successMessage, after = refresh) => {
    setBusy(true); setError(''); setNotice('')
    try { const result = await operation(); await playSteps(successMessage, result?.steps, result?.stepHook); if (successMessage) setNotice(successMessage); await after(false); return result }
    catch (requestError) { setError(requestError.message); addLog(requestError.message, 'failed') }
    finally { setBusy(false) }
  }

  const selectBackup = async (id) => {
    setSelectedId(id); setAlternateResult(null)
    try { setSelectedBackup(await getBackupDetails(id)); setError('') } catch (requestError) { setError(requestError.message) }
  }

  const verifyChainAction = () => run(async () => {
    const result = await verifyChain()
    setVerification({ ...result, nodes: result.nodes?.map((node) => ({ ...node, status: 'pending' })) || [] })
    const steps = (result.nodes || []).flatMap((node) => node.steps.map((step) => ({ ...step, node_id: node.id })))
    return {
      ...result,
      steps,
      stepHook: (step) => {
        setActiveNode(step.node_id)
        setVerification((current) => current ? { ...current, nodes: current.nodes.map((node) => node.id === step.node_id ? { ...node, status: step.status === 'failed' ? 'failed' : 'checking' } : node) } : current)
      },
    }
  }, 'Verifying backup chain')
  const createFullAction = () => run(createFullBackup, 'Creating full backup')
  const createIncrementalAction = () => run(createIncrementalBackup, 'Creating incremental backup')
  const upload = (files) => run(() => uploadSourceFiles(files), 'Uploading source files')
  const remove = (fileId) => run(() => deleteSource(fileId), `Deleting ${fileId}`)
  const findAlternateAction = (id) => run(async () => { const result = await findAlternate(id); setAlternateResult(result); return { ...result, steps: [{ name: 'find_alternate_delta', status: 'completed', details: `${result.candidates?.length || 0} candidates` }] } }, 'Finding alternate delta')
  const verifyAlternateAction = (id, alternateId) => run(async () => { const result = await verifyAlternate(id, alternateId); setAlternateResult((current) => ({ ...current, verification: result })); if (result.accepted) { setVerification(await verifyChain()) } return { ...result, steps: [{ name: result.accepted ? 'alternate_accepted' : 'alternate_rejected', status: result.accepted ? 'completed' : 'failed' }] } }, 'Verifying alternate delta')
  const restoreAction = (id) => run(async () => { const result = await restore(id); setRestoreResult(result); setRestoreVerification(null); return { ...result, steps: [{ name: result.restored ? 'restore_safe_recovery_point' : 'restore_failed', status: result.restored ? 'completed' : 'failed' }] } }, 'Restoring safe point')
  const verifyRestoreAction = (id) => run(async () => { const result = await verifyRestore(id); setRestoreVerification(result); return { ...result, steps: [{ name: result.verified ? 'restored_data_matches' : 'restored_data_mismatch', status: result.verified ? 'completed' : 'failed' }] } }, 'Verifying restored data')

  return (
    <div className="app-shell">
      <Header connected={connected} onRefresh={() => refresh()} refreshing={refreshing} apiUrl={apiBaseUrl} />
      <main>
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

        <div className="simple-layout">
          <SourcePanel source={source} onUpload={upload} onDelete={remove} busy={busy} />
          <BackupChain backups={backups} selectedId={selectedId} selectedBackup={selectedBackup} onSelect={selectBackup} verification={verification} activeNode={activeNode} alternateResult={alternateResult} />
          <ProcessLog entries={logEntries} active={activeOperation} />
          <SimpleControls backups={backups} safePoint={verification?.latest_safe_recovery_point || ''} onFull={createFullAction} onIncremental={createIncrementalAction} onVerify={verifyChainAction} onRestore={restoreAction} onVerifyRestore={verifyRestoreAction} onFindAlternate={findAlternateAction} onVerifyAlternate={verifyAlternateAction} alternateResult={alternateResult} busy={busy} />
          {(restoreResult || restoreVerification) && <p className="compact-result">{restoreVerification ? (restoreVerification.verified ? 'Restored data verified.' : 'Restored data has mismatches.') : restoreResult?.restored ? `Restored ${restoreResult.files?.length || 0} files.` : 'Restore failed.'}</p>}
        </div>
      </main>
      <footer>
        <span>BackupChain local console</span>
        <span>API - {apiBaseUrl}</span>
      </footer>
    </div>
  )
}
