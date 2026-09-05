import { useRef, useState } from 'react'

export default function SourcePanel({ source, onUpload, onDelete, busy }) {
	const inputRef = useRef(null)
	const [selectedFiles, setSelectedFiles] = useState([])
	const files = source?.files || []
	const upload = () => {
		if (selectedFiles.length) onUpload(selectedFiles)
		setSelectedFiles([])
		if (inputRef.current) inputRef.current.value = ''
	}

	return (
		<section className="panel source-panel">
			<div className="section-heading"><div><p className="eyebrow">01 / source</p><h2>Source files</h2></div><span className="version-chip">V{source?.version ?? '-'}</span></div>
			<div className="action-row">
				<input ref={inputRef} type="file" multiple onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))} disabled={busy} />
				<button type="button" className="button button-primary" onClick={upload} disabled={busy || !selectedFiles.length}>Upload Files</button>
			</div>
			{selectedFiles.length > 0 && <p className="helper-text">Ready to upload: {selectedFiles.map((file) => file.name).join(', ')}</p>}
			<div className="file-list">
				{files.length ? files.map((file) => <div className="file-row" key={file.file_id}><span className="file-icon">{file.filename.endsWith('.json') ? '{}' : 'F'}</span><div><strong>{file.filename}</strong><span>{file.file_id} - v{file.version} - {file.size} bytes - {file.content_hash?.slice(0, 12)}</span></div><button type="button" className="button button-ghost" onClick={() => onDelete(file.file_id)} disabled={busy} aria-label={`Delete ${file.filename}`}>Delete</button></div>) : <p className="empty-state">No source files yet. Upload files or seed the demo dataset to begin.</p>}
			</div>
		</section>
	)
}
