export default function SimpleControls({ backups, safePoint, onVerify, onRestore, onVerifyRestore, onFindAlternate, onVerifyAlternate, alternateResult, busy }) {
  const incremental = backups.find((point) => point.type === 'INCREMENTAL')
  const candidates = alternateResult?.candidates || []
  const selectedAlternate = candidates[0]

  return (
    <section className="simple-controls">
      <div className="section-heading"><div><p className="eyebrow">Controls</p><h2>Run the next backend operation</h2></div></div>
      <div className="control-row">
        <button type="button" className="button button-secondary" onClick={onVerify} disabled={busy || !backups.length}>Verify backup chain</button>
      </div>
      <div className="control-row control-row-secondary">
        <button type="button" className="button button-quiet" onClick={() => onRestore(safePoint)} disabled={busy || !safePoint}>Restore safe point{safePoint ? ` (${safePoint})` : ''}</button>
        <button type="button" className="button button-quiet" onClick={() => onVerifyRestore(safePoint)} disabled={busy || !safePoint}>Verify restored data</button>
        {incremental && <button type="button" className="button button-quiet" onClick={() => onFindAlternate(incremental.id)} disabled={busy}>Find alternate for {incremental.id}</button>}
        {selectedAlternate && <button type="button" className="button button-quiet" onClick={() => onVerifyAlternate(incremental.id, selectedAlternate.id)} disabled={busy}>Verify {selectedAlternate.id}</button>}
      </div>
    </section>
  )
}
