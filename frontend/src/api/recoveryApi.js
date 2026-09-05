import { request, jsonRequest } from './client'

export const restore = (id) => request('/restore', jsonRequest('POST', { recovery_point_id: id }))
export const verifyRestore = (id) => request('/restore/verify', jsonRequest('POST', { recovery_point_id: id }))
