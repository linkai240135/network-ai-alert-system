import http from './http'

export const loginApi = (payload) => http.post('/auth/login', payload)
export const logoutApi = () => http.post('/auth/logout')
export const meApi = () => http.get('/auth/me')
