FEATURE_COLUMNS = [
    "flow_duration",
    "packet_rate",
    "byte_rate",
    "syn_rate",
    "dst_port_entropy",
    "failed_login_rate",
    "request_interval_std",
    "payload_mean",
]

FEATURE_LABELS = {
    "flow_duration": "流持续时间",
    "packet_rate": "包速率",
    "byte_rate": "字节速率",
    "syn_rate": "SYN 比例",
    "dst_port_entropy": "目标端口熵",
    "failed_login_rate": "登录失败率",
    "request_interval_std": "请求间隔波动",
    "payload_mean": "平均载荷",
}

ATTACK_DESCRIPTIONS = {
    "BENIGN": "正常通信流量",
    "DoS": "拒绝服务攻击，表现为短时高频流量冲击和资源消耗异常。",
    "PortScan": "端口扫描行为，通常伴随高频目标端口探测与侦察行为。",
    "Bot": "疑似僵尸网络控制流量，常表现为周期性异常通信和外联。",
    "BruteForce": "暴力破解攻击，通常伴随较高的登录失败率和重复尝试。",
    "WebAttack": "针对 Web 服务的异常访问与攻击流量，可能涉及注入、目录探测等。",
    "UNKNOWN": "疑似未知异常流量，建议转入人工复核和深度排查流程。",
}

RISK_LEVELS = {
    "BENIGN": "低",
    "WebAttack": "中",
    "PortScan": "中",
    "Bot": "高",
    "BruteForce": "高",
    "DoS": "高",
    "UNKNOWN": "中",
}

MITIGATION_ADVICE = {
    "BENIGN": "保持持续监测即可，当前无需执行人工处置。",
    "DoS": "建议立即限流并封禁异常源 IP，同时核查网关、负载均衡和防火墙策略。",
    "PortScan": "建议对扫描源实施临时封禁，并同步核查暴露端口、ACL 与边界访问控制。",
    "Bot": "建议隔离疑似受控主机，排查外联地址、计划任务和可疑进程。",
    "BruteForce": "建议启用验证码与登录频率限制，并核查弱口令账户和认证策略。",
    "WebAttack": "建议联动 WAF 与应用日志，回溯恶意请求链路并排查漏洞。",
    "UNKNOWN": "建议转入人工研判队列，结合原始流量、主机日志和上下文信息进一步确认。",
}

ATTACK_STAGES = {
    "BENIGN": "正常业务阶段",
    "PortScan": "探测侦察阶段",
    "BruteForce": "入侵尝试阶段",
    "WebAttack": "利用攻击阶段",
    "Bot": "横向控制阶段",
    "DoS": "持续破坏阶段",
    "UNKNOWN": "疑似未知阶段",
}

SERVICE_PROFILES = [
    {"name": "Web Service", "port": 80, "protocol": "HTTP", "keywords": "站点访问"},
    {"name": "Secure Web", "port": 443, "protocol": "HTTPS", "keywords": "加密业务"},
    {"name": "Remote Login", "port": 22, "protocol": "SSH", "keywords": "远程运维"},
    {"name": "Name Service", "port": 53, "protocol": "DNS", "keywords": "域名解析"},
    {"name": "Remote Desktop", "port": 3389, "protocol": "RDP", "keywords": "桌面接入"},
    {"name": "Database", "port": 3306, "protocol": "MySQL", "keywords": "数据访问"},
]

UNKNOWN_ANOMALY_THRESHOLD = 0.72
ALERT_TRIGGER_THRESHOLD = 0.58
