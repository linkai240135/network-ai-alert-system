const { createApp, nextTick } = Vue;

const vueApp = createApp({
  data() {
    const initialForm = Object.fromEntries(window.APP_CONFIG.featureColumns.map((item) => [item, 0]));
    return {
      tabs: [
        { key: "dashboard", label: "系统总览" },
        { key: "detect", label: "在线检测" },
        { key: "alerts", label: "告警与日志" },
      ],
      activeTab: "dashboard",
      featureColumns: window.APP_CONFIG.featureColumns,
      overview: { training: {}, models: [], preview: [], class_distribution: {}, db_mode: "SQLite" },
      alerts: [],
      detections: [],
      systemInfo: { architecture: {} },
      detectForm: initialForm,
      result: null,
      latestAlert: null,
      loading: {
        train: false,
        detect: false,
      },
      chart: null,
    };
  },
  computed: {
    previewColumns() {
      return this.overview.preview?.length ? Object.keys(this.overview.preview[0]) : [];
    },
    dbLabel() {
      return this.overview.db_mode === "MySQL" ? "推荐生产模式" : "本地演示模式";
    },
    resultClass() {
      if (!this.result) return "empty";
      return this.result.risk_level === "低" ? "safe" : this.result.risk_level === "中" ? "warning" : "danger";
    },
    badgeClass() {
      if (!this.result) return "low";
      return this.badgeClassByLevel(this.result.risk_level);
    },
  },
  methods: {
    async fetchJson(url, method = "get", data = undefined) {
      const response = await axios({ url, method, data });
      return response.data;
    },
    async loadOverview() {
      this.overview = await this.fetchJson("/api/overview");
      await nextTick();
      this.renderChart();
    },
    async loadAlerts() {
      const data = await this.fetchJson("/api/alerts");
      this.alerts = data.alerts;
    },
    async loadDetections() {
      const data = await this.fetchJson("/api/detections");
      this.detections = data.detections;
    },
    async loadSystem() {
      this.systemInfo = await this.fetchJson("/api/system");
    },
    async refreshAll() {
      await Promise.all([this.loadOverview(), this.loadAlerts(), this.loadDetections(), this.loadSystem()]);
    },
    renderChart() {
      const chartDom = document.getElementById("class-chart");
      if (!chartDom) return;
      this.chart = this.chart || echarts.init(chartDom);
      this.chart.setOption({
        tooltip: { trigger: "item" },
        color: ["#b1452f", "#d8892f", "#6d8f3f", "#3a7ca5", "#845ec2", "#d65d7a"],
        series: [
          {
            type: "pie",
            radius: ["40%", "72%"],
            roseType: "area",
            itemStyle: { borderRadius: 12 },
            data: Object.entries(this.overview.class_distribution || {}).map(([name, value]) => ({ name, value })),
          },
        ],
      });
    },
    badgeClassByLevel(level) {
      if (level === "低") return "low";
      if (level === "中") return "mid";
      return "high";
    },
    formatCell(value) {
      return typeof value === "number" ? value.toFixed(4) : value;
    },
    fillAttackSample() {
      this.detectForm = {
        flow_duration: 42,
        packet_rate: 680,
        byte_rate: 23000,
        syn_rate: 0.82,
        dst_port_entropy: 0.12,
        failed_login_rate: 0.01,
        request_interval_std: 0.05,
        payload_mean: 180,
      };
    },
    fillBenignSample() {
      this.detectForm = {
        flow_duration: 250,
        packet_rate: 70,
        byte_rate: 2600,
        syn_rate: 0.04,
        dst_port_entropy: 0.21,
        failed_login_rate: 0.01,
        request_interval_std: 0.56,
        payload_mean: 680,
      };
    },
    async retrainModel() {
      this.loading.train = true;
      try {
        await this.fetchJson("/api/train", "post", {});
        await this.refreshAll();
      } finally {
        this.loading.train = false;
      }
    },
    async submitDetection() {
      this.loading.detect = true;
      try {
        const data = await this.fetchJson("/api/predict", "post", this.detectForm);
        this.result = data.result;
        this.latestAlert = data.alert;
        this.activeTab = "detect";
        await Promise.all([this.loadAlerts(), this.loadDetections()]);
      } finally {
        this.loading.detect = false;
      }
    },
  },
  async mounted() {
    await this.refreshAll();
    window.addEventListener("resize", () => this.chart && this.chart.resize());
  },
});

vueApp.config.compilerOptions.delimiters = ["[[", "]]"];
vueApp.mount("#app");
