import axios from 'axios'

let apiHost = import.meta.env.VITE_API_URL || ''
if (apiHost === 'bid-compliance-api' || (apiHost && !apiHost.includes('.') && !apiHost.includes('localhost'))) {
  apiHost = 'https://bid-compliance-api.onrender.com'
} else if (apiHost && !apiHost.startsWith('http://') && !apiHost.startsWith('https://')) {
  apiHost = `https://${apiHost}`
}
const apiBase = apiHost ? `${apiHost.replace(/\/+$/, '')}/api` : '/api'

const client = axios.create({ baseURL: apiBase })



client.interceptors.request.use((config) => {
  const token = localStorage.getItem('bbc_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default client
