import StatusBadge from './StatusBadge'

export default function VerificationPanel({ verification, onVerify, busy }) {
  const status = verification?.chain_status || 'NOT VERIFIED'
  return <section className="panel verification-panel">
    <div className="section-heading"><div><p className="eyebrow">04 / machine check</p><h2>Chain verification</h2></div>{verification && <StatusBadge status={status} />}</div>
    <div className="verification-hero"><div className={`verification-icon ${status.toLowerCase().includes('valid') || status.includes('RECOVERED') ? 'good' : status === 'BROKEN' ? 'bad' : ''}`}>{status === 'VALID' || status.includes('RECOVERED') ? '✓' : status === 'BROKEN' ? '!' : '·'}</div><div><strong>{verification ? status.replaceAll('_', ' ') : 'Awaiting verification'}</strong><span>{verification ? 'Backend decision from the complete dependency chain.' : 'Run the verifier to establish the latest safe point.'}</span></div></div>
    <div className="verification-grid"><div><span>Latest safe point</span><strong>{verification?.latest_safe_recovery_point || '—'}</strong></div><div><span>Earliest problem</span><strong>{verification?.earliest_problem || 'None'}</strong></div><div><span>Replacement</span><strong>{verification?.replacement || 'None'}</strong></div></div>
    {verification?.details?.errors?.length > 0 && <div className="inline-errors">{verification.details.errors.map((error) => <p key={error}>{error}</p>)}</div>}
    <button className="button button-primary full-button" onClick={onVerify} disabled={busy}>{busy ? 'Verifying chain...' : 'Verify Chain'}</button>
  </section>
}
