import { useRef, useState } from 'react'

export default function SourcePanel({ source, sourceCreated, onAddSource, onAddChanged, onDelete, busy }) {
	const inputRef = useRef(null)
	const [selectedFiles, setSelectedFiles] = useState([])
	const files = source?.files || []
	const clearSelection = () => {
		setSelectedFiles([])
		if (inputRef.current) inputRef.current.value = ''
	}
	const addSource = () => { if (selectedFiles.length) { onAddSource(selectedFiles); clearSelection() } }
	const addChanged = () => { onAddChanged(selectedFiles); clearSelection() }

	return (
		<section className="panel source-panel">
			<div className="section-heading"><div><p className="eyebrow">01 / source</p><h2>Source files</h2></div><span className="version-chip">V{source?.version ?? '-'}</span></div>
			<div className="action-row">
				<input ref={inputRef} type="file" multiple onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))} disabled={busy} />
			</div>
			{selectedFiles.length > 0 && <p className="helper-text">Ready to upload: {selectedFiles.map((file) => file.name).join(', ')}</p>}
			<div className="source-actions">
				<button type="button" className="button button-primary" onClick={addSource} disabled={busy || sourceCreated || !selectedFiles.length}>Add Source Data</button>
				<button type="button" className="button button-secondary" onClick={addChanged} disabled={busy || !sourceCreated}>Add Changed Data</button>
			</div>
			<p className="helper-text">{sourceCreated ? 'Source baseline is locked. New files are compared against the latest linked state.' : 'Add source data once to create the immutable FULL baseline.'}</p>
			<div className="file-list">
				{files.length ? files.map((file) => <div className="file-row" key={file.file_id}><span className="file-icon">{file.filename.endsWith('.json') ? '{}' : 'F'}</span><div><strong>{file.filename}</strong><span>{file.file_id} - v{file.version} - {file.size} bytes - {file.content_hash?.slice(0, 12)}</span></div><button type="button" className="button button-ghost" onClick={() => onDelete(file.file_id)} disabled={busy} aria-label={`Delete ${file.filename}`}>Delete</button></div>) : <p className="empty-state">No source files yet. Upload your files to begin.</p>}
			</div>
		</section>
	)
}
