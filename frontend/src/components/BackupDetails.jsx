import { useState } from 'react'
import StatusBadge from './StatusBadge'

function HashValue({ value }) {
  const [copied, setCopied] = useState(false)
  if (!value) return <span className="hash-empty">not available</span>
  return <button className="hash-value" title="Copy full hash" onClick={() => { navigator.clipboard?.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1200) }}>{copied ? 'Copied' : `${value.slice(0, 12)}...${value.slice(-8)}`}</button>
}

export default function BackupDetails({ backup, validation, onValidate, onFindAlternate, busy }) {
  if (!backup) return <section className="panel details-panel empty-details"><span className="detail-symbol">⌁</span><h2>Select a recovery point</h2><p>Choose a node in the chain to inspect its evidence and validation state.</p></section>
  return <section className="panel details-panel">
    <div className="section-heading"><div><p className="eyebrow">03 / evidence record</p><h2>{backup.id}</h2></div><StatusBadge status={validation?.valid === false ? 'INVALID' : backup.status} /></div>
    <div className="detail-grid">
      <div><span>Type</span><strong>{backup.type}</strong></div><div><span>Parent</span><strong>{backup.parent_id || 'Root'}</strong></div><div><span>Source</span><strong>{backup.source_id}</strong></div><div><span>Sequence</span><strong>{backup.sequence}</strong></div><div><span>Start version</span><strong>V{backup.start_version}</strong></div><div><span>End version</span><strong>V{backup.end_version}</strong></div><div><span>Changes</span><strong>{backup.change_count}</strong></div><div><span>Created</span><strong>{backup.created_at ? new Date(backup.created_at).toLocaleString() : '—'}</strong></div>
    </div>
    <div className="hash-list"><div><span>Manifest hash</span><HashValue value={backup.manifest_hash} /></div><div><span>Artifact hash</span><HashValue value={backup.artifact_hash} /></div></div>
    <div className="detail-actions"><button className="button button-secondary" onClick={() => onValidate(backup.id)} disabled={busy}>Validate backup</button>{backup.type === 'INCREMENTAL' && <button className="button button-quiet" onClick={() => onFindAlternate(backup.id)} disabled={busy}>Find alternate</button>}</div>
    {validation && <div className={`validation-note ${validation.valid ? 'note-success' : 'note-error'}`}><strong>{validation.valid ? 'Validation passed' : 'Validation failed'}</strong>{validation.errors?.length > 0 && <ul>{validation.errors.map((error) => <li key={error}>{error}</li>)}</ul>}{validation.warnings?.length > 0 && <ul>{validation.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}</div>}
  </section>
}
