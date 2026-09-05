import StatusBadge from '../common/StatusBadge'

function nodeStatus(point, verification) {
	if (verification?.replacement === point.id) return 'REPLACED'
	if (verification?.chain_status === 'BROKEN' && point.id === verification.earliest_problem) return 'MISSING'
	return point.status || 'UNKNOWN'
}

export default function BackupChain({ backups, selectedId, onSelect, verification }) {
	return (
		<section className="panel chain-panel">
			<div className="section-heading">
				<div>
					<p className="eyebrow">02 / dependency graph</p>
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
							<button type="button" className={`chain-node ${selectedId === point.id ? 'selected' : ''}`} onClick={() => onSelect(point.id)}>
								<div className="node-top">
									<span className="node-type">{point.type === 'FULL' ? 'BASE' : 'DELTA'}</span>
									<StatusBadge status={nodeStatus(point, verification)} />
								</div>
								<strong>{point.id}</strong>
								<span className="node-meta">Seq {point.sequence} - {point.change_count} changes</span>
							</button>
							{index < backups.length - 1 && <div className="chain-link"><span aria-hidden="true">-&gt;</span></div>}
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
		</section>
	)
}
