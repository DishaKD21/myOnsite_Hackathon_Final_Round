export default function DemoControls({ backups, onFindAlternate, alternateResult, onVerifyAlternate, onCreateFull, onCreateIncremental, busy }) {
  const original = alternateResult?.original_delta || backups.find((point) => point.type === 'INCREMENTAL')?.id
  const candidate = alternateResult?.candidates?.[0]?.id
  return <section className="panel demo-panel">
    <div className="section-heading"><div><p className="eyebrow">06 / controlled scenario</p><h2>Demo / failure simulation</h2></div><span className="demo-label">manual controls</span></div>
    <p className="panel-copy">Use the backend's real catalog and verifier to stage a chain. Artifact deletion and alternate creation remain backend-owned operations.</p>
    <div className="demo-actions"><button className="button button-secondary" onClick={onCreateFull} disabled={busy}>Create Full Backup</button><button className="button button-secondary" onClick={onCreateIncremental} disabled={busy}>Create Incremental Backup</button></div>
    <div className="demo-divider" />
    <div className="alternate-row"><div><strong>Alternate discovery</strong><span>Search structurally for a compatible delta.</span></div><button className="button button-quiet" onClick={() => original && onFindAlternate(original)} disabled={busy || !original}>Find alternate</button></div>
    {alternateResult && <div className="alternate-result"><span className="result-mark">{candidate ? '✓' : '!'}</span><div><strong>{candidate ? `${candidate} candidate found` : 'No alternate candidate found'}</strong><span>{candidate ? 'Select the original point and verify this candidate through the backend.' : 'The catalog has no structurally compatible delta.'}</span></div>{candidate && <button className="button button-primary" onClick={() => onVerifyAlternate(original, candidate)} disabled={busy}>Verify alternate</button>}</div>}
  </section>
}
