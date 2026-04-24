import http from './http'

export const fetchDashboardSummary = () => http.get('/dashboard/summary')
export const fetchDatasetOverview = () => http.get('/datasets/overview')
export const fetchLatestTraining = () => http.get('/training/latest')
export const fetchTrainingHistory = () => http.get('/training/history')
export const fetchTrainingTrends = () => http.get('/training/trends')
export const triggerTraining = () => http.post('/training/run')
export const runDetection = (payload) => http.post('/detection/run', payload)
export const fetchDetectionLogs = (params) => http.get('/detection/logs', { params })
export const fetchAlerts = (params) => http.get('/alerts', { params })
export const fetchAlertTrends = (params) => http.get('/alerts/trends', { params })
export const fetchSystemOverview = () => http.get('/system/overview')
export const fetchServicePortrait = (params) => http.get('/alerts/service-portrait', { params })
export const simulateRealtimeStream = (payload) => http.post('/detection/simulate-stream', payload)
export const fetchAssets = (params) => http.get('/assets', { params })
export const fetchAssetTopology = () => http.get('/assets/topology')
export const fetchIncidents = (params) => http.get('/incidents', { params })
export const fetchIncidentBoard = () => http.get('/incidents/board')
export const fetchIncidentDetail = (id) => http.get(`/incidents/${id}`)
export const updateIncidentStatus = (id, payload) => http.put(`/incidents/${id}/status`, payload)
export const addIncidentNote = (id, payload) => http.post(`/incidents/${id}/notes`, payload)
export const fetchIncidentReport = (id) => http.get(`/incidents/${id}/report`)
export const fetchSourceChain = (sourceIp) => http.get('/incidents/source-chain', { params: { source_ip: sourceIp } })
export const submitIncidentFeedback = (id, payload) => http.post(`/incidents/${id}/feedback`, payload)
export const fetchTrainingFeedback = () => http.get('/training/feedback')
export const uploadCicidsDataset = (formData) =>
  http.post('/datasets/import-cicids', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const uploadCicidsDatasetBatch = (formData) =>
  http.post('/datasets/import-cicids-batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const fetchImportJobs = () => http.get('/datasets/import-jobs')
export const uploadBatchDetection = (formData) =>
  http.post('/detection/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const fetchSettings = () => http.get('/settings')
export const updateSettings = (payload) => http.put('/settings', payload)
export const fetchAlertsFiltered = (params) => http.get('/alerts', { params })
export const batchUpdateAlerts = (payload) => http.put('/alerts/status', payload)
const aiRequestConfig = { timeout: 90000 }

export const analyzeAlertWithAi = (payload) => http.post('/ai/analyze-alert', payload, aiRequestConfig)
export const analyzeIncidentWithAi = (payload) => http.post('/ai/analyze-incident', payload, aiRequestConfig)
export const chatWithAi = (payload) => http.post('/ai/chat', payload, aiRequestConfig)
export const generateIncidentReportWithAi = (payload) => http.post('/ai/generate-report', payload, aiRequestConfig)
