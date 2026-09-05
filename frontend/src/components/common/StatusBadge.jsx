export default function StatusBadge({ status = 'UNKNOWN' }) {
	const value = String(status).replaceAll('_', ' ')
	return <span className={`status-badge status-${String(status).toLowerCase()}`}>{value}</span>
}
