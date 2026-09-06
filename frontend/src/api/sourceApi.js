import { apiBaseUrl, jsonRequest, request } from './client'

export { apiBaseUrl }
export const getSourceState = () => request('/source/state')
export const uploadSourceFiles = (files) => {
	const body = new FormData()
	files.forEach((file) => body.append('files', file))
	return request('/source/files', { method: 'POST', body })
}
export const modifySource = (fileId, content) => request('/source/modify', jsonRequest('POST', { file_id: fileId, content }))
export const addSource = (fileId, filename, content) => request('/source/add', jsonRequest('POST', { file_id: fileId, filename, content }))
export const deleteSource = (fileId) => request('/source/delete', jsonRequest('POST', { file_id: fileId }))
