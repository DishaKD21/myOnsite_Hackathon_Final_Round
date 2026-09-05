export default function Header({ connected, onRefresh, refreshing, apiUrl }) {
	return (
		<header className="topbar">
			<div className="brand-lockup">
				<div className="brand-mark">BC</div>
				<div>
					<p className="eyebrow">Integrity console</p>
					<h1>BackupChain</h1>
					<p className="subtitle">Incremental backup integrity & recovery</p>
				</div>
			</div>
			<div className="connection-area">
				<div className="connection-status">
					<span className={`connection-dot ${connected ? 'is-connected' : ''}`} />
					<div><span className="muted-label">Backend</span><strong>{connected ? 'Connected' : 'Disconnected'}</strong></div>
				</div>
				<button type="button" className="button button-quiet" onClick={onRefresh} disabled={refreshing} title={`Refresh from ${apiUrl}`}>
					{refreshing ? 'Refreshing' : 'Refresh'}
				</button>
			</div>
		</header>
	)
}
