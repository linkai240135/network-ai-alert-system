# 通信网络异常检测与智能告警系统

这是当前项目的工程化版本，采用前后端分离结构，面向比赛答辩、系统演示和后续功能扩展。

## 目录结构

- `backend/`：Flask 后端，按 `api / models / services / utils` 分层
- `frontend/`：Vue 3 + Vite 前端，按 `views / components / router / stores / api` 分层
- `data/`：演示数据集
- `models/`：模型文件与训练产物
- `instance/`：SQLite 本地数据库

## 技术栈

- 前端：Vue 3、Vite、Vue Router、Pinia、Element Plus
- 后端：Flask、Flask-SQLAlchemy
- 数据库：MySQL 优先，SQLite 本地兜底
- 算法：scikit-learn、pandas、numpy、joblib

## 运行方式

### 后端

```bash
python app.py
```

默认监听 `http://127.0.0.1:5000`

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认监听 `http://127.0.0.1:5173`

## 默认登录账号

- 用户名：`admin`
- 密码：`admin123`

## CICIDS2017 真实数据接入

系统已支持在“数据集管理”页面直接上传 `CICIDS2017` 的 CSV 文件，并自动执行：

- 原始字段识别
- 标签映射与清洗
- 特征转换
- 数据入库
- 按设置自动触发重新训练

当前导入逻辑主要识别以下常见字段：

- `Flow Duration`
- `Total Fwd Packets`
- `Total Backward Packets`
- `Total Length of Fwd Packets`
- `Total Length of Bwd Packets`
- `SYN Flag Count`
- `Destination Port`
- `Init_Win_bytes_forward`
- `Flow IAT Std`
- `Average Packet Size`
- `Label`

支持映射的典型标签包括：

- `BENIGN`
- `DoS Hulk`
- `DoS GoldenEye`
- `DoS slowloris`
- `DoS Slowhttptest`
- `DDoS`
- `PortScan`
- `Bot`
- `FTP-Patator`
- `SSH-Patator`
- `Web Attack - Brute Force`
- `Web Attack - XSS`
- `Web Attack - Sql Injection`

## CSV 批量检测

“CSV批量检测”页面支持上传特征化后的 CSV，文件需包含以下字段：

- `flow_duration`
- `packet_rate`
- `byte_rate`
- `syn_rate`
- `dst_port_entropy`
- `failed_login_rate`
- `request_interval_std`
- `payload_mean`

## MySQL 切换

PowerShell 示例：

```powershell
$env:DATABASE_URL="mysql+pymysql://root:123456@127.0.0.1:3306/network_ai_alert?charset=utf8mb4"
python app.py
```

## 说明

- 当前默认数据集为演示型流量数据，可继续替换为 `CICIDS2017`、`CSE-CIC-IDS2018` 等真实公开数据集。
- 当前系统已经具备登录鉴权、数据集总览、CICIDS2017 导入、训练中心、训练图表、在线检测、CSV 批量检测、告警筛选、检测日志和系统设置等工程化页面。
- 下一阶段建议继续补充用户权限分级、模型解释、批量任务进度条、可视化大屏和比赛报告文档。
