function icon(status) {
  if (status === 'failed') return 'x'
  if (status === 'running') return '~'
  if (status === 'completed' || status === 'passed') return 'ok'
  return 'o'
}

export default function ProcessLog({ entries, active }) {
  return (
    <section className="process-log" aria-live="polite">
      <div className="section-heading">
        <div><p className="eyebrow">Process log</p><h2>What the backend is doing</h2></div>
        {active && <span className="log-active">{active}</span>}
      </div>
      <div className="log-list">
        {entries.length ? entries.map((entry, index) => (
          <div className={`log-entry ${entry.status}`} key={`${entry.time}-${index}`}>
            <span className="log-icon">{icon(entry.status)}</span>
            <time>{entry.time}</time>
            <strong>{entry.message}</strong>
            {entry.details && <span>{entry.details}</span>}
          </div>
        )) : <p className="empty-state">Operations will appear here as the backend completes them.</p>}
      </div>
    </section>
  )
}
