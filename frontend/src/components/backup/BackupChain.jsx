import StatusBadge from '../common/StatusBadge'

function nodeStatus(point, verification) {
	if (verification?.replacement === point.id) return 'REPLACED'
	const result = verification?.nodes?.find((node) => node.id === point.id)
	if (result?.status === 'failed') return 'FAILED'
	return point.status || 'UNKNOWN'
}

export default function BackupChain({ backups, selectedId, selectedBackup, onSelect, verification, activeNode, alternateResult, operationSteps }) {
	return (
		<section className="panel chain-panel">
			<div className="section-heading">
				<div>
					<p className="eyebrow">02 / live dependency graph</p>
						<h2>Backup chain</h2>
				</div>
				<span className="chain-count">{backups.length} points</span>
			</div>
			<div className="chain-legend">
				<span><i className="legend-dot valid" />valid</span>
				<span><i className="legend-dot missing" />problem</span>
				<span><i className="legend-dot replaced" />replacement</span>
			</div>
			{backups.length ? (
				<div className="chain-track">
					{backups.map((point, index) => (
						<div className="chain-segment" key={point.id}>
							<button type="button" className={`chain-node ${selectedId === point.id ? 'selected' : ''} ${activeNode === point.id ? 'checking' : ''} ${verification?.earliest_problem === point.id ? 'failed' : ''}`} onClick={() => onSelect(point.id)}>
								<div className="node-top">
									<span className="node-type">{point.type === 'FULL' ? 'BASE' : 'DELTA'}</span>
									<StatusBadge status={nodeStatus(point, verification)} />
								</div>
								<strong>{point.id}</strong>
								<span className="node-meta">Seq {point.sequence} - {point.change_count} changes</span>
							</button>
							{index < backups.length - 1 && <div className={`chain-link ${verification?.earliest_problem === point.id ? 'broken' : ''}`}><span aria-hidden="true">━━━━</span></div>}
						</div>
					))}
				</div>
			) : (
				<div className="empty-chain">
					<span>0</span>
					<p>No recovery points yet</p>
					<small>Create a full backup to establish the chain.</small>
				</div>
			)}
			{operationSteps?.length > 0 && <div className="operation-inspection" aria-live="polite">
				<strong>Temporary operation state</strong>
				{operationSteps.map((step, index) => <div className={`inspection-step ${step.status}`} key={`${step.name}-${index}`}><span>{step.status === 'failed' ? 'x' : 'ok'}</span><span>{step.name.replaceAll('_', ' ')}</span>{step.details && <small>{step.details}</small>}</div>)}
			</div>}
			{selectedBackup && <div className="node-details"><strong>{selectedBackup.id}</strong><span>{selectedBackup.type} · parent {selectedBackup.parent_id || 'none'} · {selectedBackup.change_count} changes · V{selectedBackup.end_version}</span><span>Manifest {selectedBackup.manifest_hash?.slice(0, 16)}... · Artifact {selectedBackup.artifact_hash?.slice(0, 16)}...</span></div>}
			{verification?.chain_status === 'BROKEN' && <div className="chain-result failed-result"><strong>Earliest broken segment: {verification.earliest_problem}</strong><span>Latest safe recovery point: {verification.latest_safe_recovery_point || 'none'}</span></div>}
			{verification?.chain_status !== 'BROKEN' && verification?.chain_status && <div className="chain-result"><strong>{verification.chain_status.replaceAll('_', ' ')}</strong><span>Latest safe recovery point: {verification.latest_safe_recovery_point}</span></div>}
			{alternateResult?.verification && <div className={`chain-result ${alternateResult.verification.accepted ? '' : 'failed-result'}`}><strong>{alternateResult.verification.accepted ? 'Alternate accepted' : 'Alternate rejected'}</strong></div>}
		</section>
	)
}
