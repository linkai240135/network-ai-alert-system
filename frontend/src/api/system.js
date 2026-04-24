import http from './http'

export const fetchPermissions = () => http.get('/auth/permissions')
