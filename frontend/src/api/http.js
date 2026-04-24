import axios from 'axios'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  withCredentials: true,
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error?.response?.status === 401 && window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default http
