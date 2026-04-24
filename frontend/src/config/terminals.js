export const TERMINALS = {
  display: {
    key: 'display',
    label: '展示端',
    badge: 'Display',
    title: '安全展示入口',
    description: '面向答辩展示与态势总览',
    rootPath: '/display',
    homePath: '/display/dashboard',
    roles: ['super_admin', 'admin', 'analyst'],
  },
  ops: {
    key: 'ops',
    label: '运营端',
    badge: 'Ops',
    title: '安全运营入口',
    description: '面向告警研判与事件处置',
    rootPath: '/ops',
    homePath: '/ops/alerts',
    roles: ['super_admin', 'admin', 'analyst'],
  },
  admin: {
    key: 'admin',
    label: '管理端',
    badge: 'Admin',
    title: '平台管理入口',
    description: '面向数据治理、训练与配置',
    rootPath: '/admin',
    homePath: '/admin/training',
    roles: ['super_admin', 'admin'],
  },
}

export const TERMINAL_ORDER = ['display', 'ops', 'admin']

export const TERMINAL_MENU_ITEMS = [
  {
    terminal: 'display',
    index: '/display/dashboard',
    label: '安全运营大屏',
    icon: 'DataAnalysis',
    roles: ['super_admin', 'admin', 'analyst'],
  },
  {
    terminal: 'display',
    index: '/display/assets',
    label: '资产画像总览',
    icon: 'Monitor',
    roles: ['super_admin', 'admin', 'analyst'],
  },
  {
    terminal: 'ops',
    index: '/ops/alerts',
    label: '告警中心',
    icon: 'Bell',
    roles: ['super_admin', 'admin', 'analyst'],
  },
  {
    terminal: 'ops',
    index: '/ops/incidents',
    label: '事件处置中心',
    icon: 'Management',
    roles: ['super_admin', 'admin', 'analyst'],
  },
  {
    terminal: 'ops',
    index: '/ops/ai-center',
    label: 'AI 研判中心',
    icon: 'Opportunity',
    roles: ['super_admin', 'admin', 'analyst'],
  },
  {
    terminal: 'ops',
    index: '/ops/detection',
    label: '在线检测',
    icon: 'Promotion',
    roles: ['super_admin', 'admin', 'analyst'],
  },
  {
    terminal: 'admin',
    index: '/admin/datasets',
    label: '数据集管理',
    icon: 'Files',
    roles: ['super_admin', 'admin'],
  },
  {
    terminal: 'admin',
    index: '/admin/training',
    label: '模型训练中心',
    icon: 'TrendCharts',
    roles: ['super_admin', 'admin'],
  },
  {
    terminal: 'admin',
    index: '/admin/batch-detection',
    label: 'CSV 批量检测',
    icon: 'UploadFilled',
    roles: ['super_admin', 'admin'],
  },
  {
    terminal: 'admin',
    index: '/admin/assets',
    label: '资产画像中心',
    icon: 'Monitor',
    roles: ['super_admin', 'admin'],
  },
  {
    terminal: 'admin',
    index: '/admin/role-permissions',
    label: '角色权限视图',
    icon: 'UserFilled',
    roles: ['super_admin', 'admin'],
  },
  {
    terminal: 'admin',
    index: '/admin/settings',
    label: '系统设置',
    icon: 'Setting',
    roles: ['super_admin'],
  },
]

export const getTerminalConfig = (terminalKey) => TERMINALS[terminalKey] || TERMINALS.display

export const getRoleAccessibleTerminals = (role) =>
  TERMINAL_ORDER.filter((key) => getTerminalConfig(key).roles.includes(role))

export const getTerminalHomePath = (terminalKey) => getTerminalConfig(terminalKey).homePath

