import { request } from './client'

export const verifyChain = () => request('/chain/verify')
