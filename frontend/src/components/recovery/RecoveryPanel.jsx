import { useEffect, useState } from 'react'

export default function RecoveryPanel({ backups, verification, restoreResult, restoreVerification, onRestore, onVerifyRestore, busy }) {
	const [selected, setSelected] = useState(verification?.latest_safe_recovery_point || '')
	useEffect(() => { if (verification?.latest_safe_recovery_point) setSelected(verification.latest_safe_recovery_point) }, [verification?.latest_safe_recovery_point])
	const recoveryPoint = selected || verification?.latest_safe_recovery_point || backups.at(-1)?.id || ''

	return (
		<section className="panel recovery-panel">
			<div className="section-heading">
				<div>
					<p className="eyebrow">05 / reconstruct state</p>
					<h2>Recovery</h2>
				</div>
				<span className="recovery-target">Safe target: {verification?.latest_safe_recovery_point || '-'}</span>
			</div>
			<label>
				Recovery point
				<select value={recoveryPoint} onChange={(event) => setSelected(event.target.value)}>
					{backups.map((point) => <option key={point.id} value={point.id}>{point.id} - {point.type}</option>)}
				</select>
			</label>
			<div className="action-row">
				<button type="button" className="button button-primary" onClick={() => onRestore(recoveryPoint)} disabled={busy || !recoveryPoint}>{busy ? 'Restoring...' : 'Restore selected point'}</button>
				<button type="button" className="button button-secondary" onClick={() => onVerifyRestore(recoveryPoint)} disabled={busy || !recoveryPoint}>Verify restored state</button>
			</div>
			{(restoreResult || restoreVerification) && (
				<div className="restore-output">
					<div className="restore-output-heading">
						<strong>{restoreVerification ? (restoreVerification.verified ? 'Restored state verified' : 'Restore verification failed') : restoreResult?.restored ? 'Restore completed' : 'Restore stopped'}</strong>
						<span>{restoreVerification ? (restoreVerification.verified ? 'Source hashes and versions match.' : 'The backend reported mismatches.') : restoreResult?.recovery_point_id}</span>
					</div>
					{restoreVerification?.mismatches?.length > 0 && <pre>{JSON.stringify(restoreVerification.mismatches, null, 2)}</pre>}
					{restoreResult?.errors?.length > 0 && <pre>{restoreResult.errors.join('\n')}</pre>}
				</div>
			)}
		</section>
	)
}
