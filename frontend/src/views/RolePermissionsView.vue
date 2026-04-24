<template>
  <div class="page-stack">
    <div class="chain-overview-grid train-stage-grid">
      <div v-for="item in roleChain" :key="item.title" class="chain-node-card">
        <span>{{ item.step }}</span>
        <strong>{{ item.title }}</strong>
      </div>
    </div>

    <PanelCard title="角色权限矩阵" subtitle="展示不同角色在数据、训练、检测、告警和系统设置中的访问范围">
      <template #extra>
        <el-tag type="info">当前角色：{{ permissionData?.currentRole || '--' }}</el-tag>
      </template>
      <el-empty v-if="!permissionData" description="加载中" />
      <template v-else>
        <div class="role-card-grid">
          <div v-for="role in permissionData.roles" :key="role.code" class="role-mini-card">
            <span>{{ role.code }}</span>
            <strong>{{ role.name }}</strong>
          </div>
        </div>
        <el-table :data="permissionData.matrix" stripe border class="permission-table">
          <el-table-column prop="module" label="功能模块" min-width="180" />
          <el-table-column prop="super_admin" label="超级管理员" min-width="180" />
          <el-table-column prop="admin" label="系统管理员" min-width="180" />
          <el-table-column prop="analyst" label="安全分析员" min-width="180" />
        </el-table>
      </template>
    </PanelCard>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import { fetchPermissions } from '../api/system'
import PanelCard from '../components/PanelCard.vue'

const permissionData = ref(null)
const roleChain = [
  { step: '01', title: '用户登录', description: '通过登录鉴权区分平台访问身份。' },
  { step: '02', title: '角色识别', description: '识别超级管理员、系统管理员和安全分析员等角色。' },
  { step: '03', title: '权限控制', description: '控制不同角色对关键模块的访问和操作范围。' },
  { step: '04', title: '企业展示', description: '让系统更符合企业级安全平台的工程形态。' },
]

onMounted(async () => {
  const response = await fetchPermissions()
  permissionData.value = response.data
})
</script>
