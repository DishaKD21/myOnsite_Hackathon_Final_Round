import { api } from '../services/api'

export const getBackups = api.getBackups
export const getBackupDetails = api.getBackupDetails
export const createFullBackup = api.createFullBackup
export const createIncrementalBackup = api.createIncrementalBackup
export const validateBackup = api.validateBackup
