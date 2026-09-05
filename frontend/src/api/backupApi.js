import { request } from './client'

export const getBackups = () => request('/backups')
export const getBackupDetails = (id) => request(`/backups/${encodeURIComponent(id)}`)
export const createFullBackup = () => request('/backup/full', { method: 'POST' })
export const createIncrementalBackup = () => request('/backup/incremental', { method: 'POST' })
export const validateBackup = (id) => request(`/backups/${encodeURIComponent(id)}/validate`, { method: 'POST' })
export const findAlternate = (id) => request(`/backups/${encodeURIComponent(id)}/find-alternate`, { method: 'POST' })
export const verifyAlternate = (id, alternateId) => request(`/backups/${encodeURIComponent(id)}/verify-alternate?alternate_id=${encodeURIComponent(alternateId)}`, { method: 'POST' })
