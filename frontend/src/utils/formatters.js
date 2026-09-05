export function formatVersion(version) {
  return version === undefined || version === null ? '-' : `V${version}`
}

export function formatTimestamp(timestamp) {
  return timestamp ? new Date(timestamp).toLocaleString() : '-'
}
