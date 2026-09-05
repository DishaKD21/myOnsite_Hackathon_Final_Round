import { useRef, useState } from 'react'

const seedFiles = [
	{ file_id: 'employee-101', filename: 'employee-101.json', content: '{"name":"Asha Patel","team":"Operations"}' },
	{ file_id: 'employee-102', filename: 'employee-102.json', content: '{"name":"Noah Chen","team":"Finance"}' },
	{ file_id: 'policy-001', filename: 'policy-001.json', content: '{"retention_days":90,"region":"eu-west"}' },
]

export default function SourcePanel({ source, onSeed, onUpload, onModify, onAdd, onDelete, busy }) {
	const inputRef = useRef(null)
	const [selectedFiles, setSelectedFiles] = useState([])
	const [fileId, setFileId] = useState('employee-101')
	const [content, setContent] = useState('{"name":"Asha Patel","team":"Operations","status":"active"}')
	const [newFileId, setNewFileId] = useState('audit-001')
	const [newFilename, setNewFilename] = useState('audit-001.json')
	const [newContent, setNewContent] = useState('{"event":"backup-check","owner":"ops"}')
	const files = source?.files || []
	const upload = () => {
		if (selectedFiles.length) onUpload(selectedFiles)
		setSelectedFiles([])
		if (inputRef.current) inputRef.current.value = ''
	}

	return (
		<section className="panel source-panel">
			<div className="section-heading"><div><p className="eyebrow">01 / source state</p><h2>Source data</h2></div><span className="version-chip">V{source?.version ?? '-'}</span></div>
			<div className="source-summary">
				<div><strong>{files.length}</strong><span>tracked files</span></div>
				<div><strong>V{source?.version ?? '-'}</strong><span>current version</span></div>
				<div><strong>{source?.source_id || '-'}</strong><span>source ID</span></div>
			</div>
			<div className="action-row">
				<input ref={inputRef} type="file" multiple onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))} disabled={busy} />
				<button type="button" className="button button-primary" onClick={upload} disabled={busy || !selectedFiles.length}>Upload Files</button>
				<button type="button" className="button button-secondary" onClick={() => onSeed(seedFiles)} disabled={busy}>Seed Demo</button>
			</div>
			{selectedFiles.length > 0 && <p className="helper-text">Ready to upload: {selectedFiles.map((file) => file.name).join(', ')}</p>}
			<div className="form-divider" />
			<p className="form-title">Modify a tracked file</p>
			<div className="form-grid">
				<label>File ID<input value={fileId} onChange={(event) => setFileId(event.target.value)} placeholder="employee-101" /></label>
				<label className="wide-field">New content<textarea value={content} onChange={(event) => setContent(event.target.value)} rows="2" /></label>
			</div>
			<button type="button" className="button button-secondary" onClick={() => onModify(fileId, content)} disabled={busy || !fileId || !content}>Modify File</button>
			<div className="form-divider" />
			<p className="form-title">Add a source file</p>
			<div className="form-grid">
				<label>File ID<input value={newFileId} onChange={(event) => setNewFileId(event.target.value)} placeholder="audit-001" /></label>
				<label>Filename<input value={newFilename} onChange={(event) => setNewFilename(event.target.value)} placeholder="audit-001.json" /></label>
				<label className="wide-field">Content<textarea value={newContent} onChange={(event) => setNewContent(event.target.value)} rows="2" /></label>
			</div>
			<button type="button" className="button button-secondary" onClick={() => onAdd(newFileId, newFilename, newContent)} disabled={busy || !newFileId || !newFilename || !newContent}>Add File</button>
			<div className="file-list">
				{files.length ? files.map((file) => <div className="file-row" key={file.file_id}><span className="file-icon">{file.filename.endsWith('.json') ? '{}' : 'F'}</span><div><strong>{file.filename}</strong><span>{file.file_id} - v{file.version} - {file.size} bytes - {file.content_hash?.slice(0, 12)}</span></div><button type="button" className="button button-ghost" onClick={() => onDelete(file.file_id)} disabled={busy} aria-label={`Delete ${file.filename}`}>Delete</button></div>) : <p className="empty-state">No source files yet. Upload files or seed the demo dataset to begin.</p>}
			</div>
		</section>
	)
}
