import { defineStore } from 'pinia'

import {
  fetchAlerts,
  fetchAlertTrends,
  fetchAssets,
  fetchDashboardSummary,
  fetchDatasetOverview,
  fetchDetectionLogs,
  fetchIncidentBoard,
  fetchIncidents,
  fetchLatestTraining,
  fetchSystemOverview,
} from '../api/dashboard'

export const useAppStore = defineStore('app', {
  state: () => ({
    dashboard: null,
    datasetOverview: null,
    latestTraining: null,
    alerts: [],
    alertTrend: null,
    detectionLogs: [],
    systemOverview: null,
    assets: [],
    assetStats: null,
    incidents: [],
    incidentBoard: null,
  }),
  actions: {
    async loadDashboard() {
      const response = await fetchDashboardSummary()
      this.dashboard = response.data
      return this.dashboard
    },
    async loadDatasetOverview() {
      const response = await fetchDatasetOverview()
      this.datasetOverview = response.data
      return this.datasetOverview
    },
    async loadLatestTraining() {
      const response = await fetchLatestTraining()
      this.latestTraining = response.data
      return this.latestTraining
    },
    async loadAlerts() {
      const response = await fetchAlerts()
      this.alerts = response.data.items
      return this.alerts
    },
    async loadDetectionLogs() {
      const response = await fetchDetectionLogs()
      this.detectionLogs = response.data.items
      return this.detectionLogs
    },
    async loadSystemOverview() {
      const response = await fetchSystemOverview()
      this.systemOverview = response.data
      return this.systemOverview
    },
    async loadAlertTrend() {
      const response = await fetchAlertTrends()
      this.alertTrend = response.data
      return this.alertTrend
    },
    async loadAssets() {
      const response = await fetchAssets()
      this.assets = response.data.items
      this.assetStats = response.data.stats
      return this.assets
    },
    async loadIncidents() {
      const response = await fetchIncidents()
      this.incidents = response.data.items
      return this.incidents
    },
    async loadIncidentBoard() {
      const response = await fetchIncidentBoard()
      this.incidentBoard = response.data
      return this.incidentBoard
    },
    async bootstrap() {
      const results = await Promise.allSettled([
        this.loadDashboard(),
        this.loadDatasetOverview(),
        this.loadLatestTraining(),
        this.loadAlerts(),
        this.loadDetectionLogs(),
        this.loadSystemOverview(),
        this.loadAlertTrend(),
        this.loadAssets(),
        this.loadIncidents(),
        this.loadIncidentBoard(),
      ])
      const rejected = results.filter((item) => item.status === 'rejected')
      if (rejected.length) {
        throw rejected[0].reason
      }
    },
    async refreshRuntimeData() {
      const results = await Promise.allSettled([
        this.loadDashboard(),
        this.loadAlerts(),
        this.loadDetectionLogs(),
        this.loadAlertTrend(),
        this.loadAssets(),
        this.loadIncidents(),
        this.loadIncidentBoard(),
      ])
      const rejected = results.filter((item) => item.status === 'rejected')
      if (rejected.length) {
        throw rejected[0].reason
      }
    },
  },
})
