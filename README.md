# 无锡城市人文治理多智能体仿真系统

> **课题组**：无锡太湖学院 / 无锡民革 殷梦娇课题组
> **课题编号**：WXSK26-C-107
> **框架**：Python Mesa 3.x | **规模**：10,000 Agent 原型验证

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)]()
[![Mesa](https://img.shields.io/badge/Mesa-3.x-orange)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()

## 📖 项目简介

本项目基于 **Agent-Based Modeling（ABM）** 方法，构建无锡市城市人文治理的多智能体计算模型。通过微观智能体交互规则推演宏观治理涌现指标，对比两种政策情景：

| 情景 | 说明 |
|------|------|
| 🟢 **传统效率优先模式** | AI 优先分流（72%），无公平审查，数字渠道未适老化 |
| 🔴 **人感城市范式（本研究提出）** | 网格员扩能、AI 公平审查、弱势群体优先人工服务 |

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   WuxiHumanGovernanceModel               │
│                     (仿真主模型)                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │ CitizenAgent │  │VulnerableAgent│  ← 诉求产生层      │
│  │  (普通市民)   │  │(老/残/外来)   │                    │
│  └──────┬───────┘  └──────┬───────┘                    │
│         │    诉求队列      │                             │
│         ▼    (路由分流)    ▼                             │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │AISystemAgent │  │GridWorkerAgent│  ← 服务处理层      │
│  │  (AI 系统)   │  │  (网格员)     │                    │
│  └──────────────┘  └──────────────┘                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                  metrics.py (涌现指标)                   │
│   公平感指数 · 信任度 · 数字包容度 · 响应时延 · 超时率    │
└─────────────────────────────────────────────────────────┘
```

## 🤖 智能体类型

| 智能体 | 数量 | 说明 |
|--------|------|------|
| `CitizenAgent` | 7,000 | 普通市民，基于 Beta 分布生成数字素养与信任度 |
| `VulnerableAgent`（老年） | 1,500 | 数字素养低，诉求频率 ×1.6，信任恢复慢 |
| `VulnerableAgent`（残障） | 500 | 面临数字障碍，服务满意度受折扣影响 |
| `VulnerableAgent`（外来务工） | 1,000 | 收入水平低，公平感知敏感 |
| `GridWorkerAgent` | 100 | 社区网格员，容量 12 件/tick，超负荷时效率衰减 |
| `AISystemAgent` | 5 | AI 算法系统，准确率 0.82，存在偏差率 |

## 📊 涌现指标体系

| 指标 | 计算方式 | 含义 |
|------|---------|------|
| **公平感指数** | 1 - Gini(各群体平均 fairness) | 越接近 1 越公平 |
| **信任度** | 全体市民 trust 均值 | 对 AI 治理系统的信任 |
| **数字包容度** | 弱势群体成功服务数 / 已结案数 | 数字渠道无障碍程度 |
| **响应时延** | 诉求产生到结案的 tick 数 | 治理效率 |
| **超时率** | 超时诉求 / 总诉求 | 治理能力 |
| **AI 偏差事件** | 累计偏差次数 | 算法公平性 |

## 🧪 实验设计

### 实验一：基准对照（传统模式）
- AI 优先分流 72%，无公平审查，网格员标准配置
- 作为性能基准线

### 实验二：人感城市范式
- 网格员效率 ×1.12，容量 ×1.20
- AI 偏差率降低 75%（公平审查）
- 弱势群体 65% 路由至网格员（保留传统服务方式）

### 实验三：突发情境压力测试
- tick=100 注入突发事件：
  - 诉求概率飙升至 0.25（31× 基准）
  - 网格员效率下降 40%
  - AI 覆盖率下降 30%
- 检验人感范式的系统韧性

每组实验重复 **5 轮**（不同随机种子），取均值消除随机性。

## 🚀 快速开始

### 环境要求

- Python ≥ 3.10
- 依赖见 `requirements.txt`

### 安装

```bash
cd simulation
pip install -r requirements.txt
```

### 运行全部实验

```bash
python run_experiment.py
```

运行完成后，结果输出至 `simulation/output/`：
- `exp1_baseline_traditional.csv` — 实验一数据
- `exp2_wuxi_paradigm.csv` — 实验二数据
- `exp3_stress_test.csv` — 实验三数据
- `comparison.png` — 情景对比图（暗色主题，2×2 子图）
- `stress_test.png` — 压力测试图

### 生成 HTML 报告

```bash
python gen_report.py
```

输出 `simulation/output/仿真实验报告.html`，包含嵌入图片、KPI 卡片、数据表格的完整报告。

## 📁 项目结构

```
├── .gitignore                   # Git 忽略规则
├── README.md                    # 项目说明（本文件）
└── simulation/                  # 仿真核心代码
    ├── agents.py                # 智能体定义（4 类，10,000 个）
    ├── model.py                 # 主模型（WuxiHumanGovernanceModel）
    ├── metrics.py               # 涌现指标计算（7 项）
    ├── run_experiment.py        # 实验运行与可视化（三组实验）
    ├── gen_report.py            # HTML 报告生成（base64 嵌入图片）
    ├── requirements.txt         # Python 依赖
    └── output/                  # 实验输出（.gitignore 排除）
        ├── exp1_baseline_traditional.csv   # 实验一数据
        ├── exp2_wuxi_paradigm.csv          # 实验二数据
        ├── exp3_stress_test.csv            # 实验三数据
        ├── comparison.png                  # 情景对比图
        ├── stress_test.png                 # 压力测试图
        ├── 仿真实验报告.html               # 实验报告
        └── 研究报告_人工智能驱动城市人文治理创新.html
```

## ⚙️ 核心参数（部分）

| 参数 | 值 | 数据来源 |
|------|----|---------|
| 诉求概率 `request_prob` | 0.008/tick | 对标北京 12345 年人均 ~1 件 |
| AI 准确率 `ai_accuracy` | 0.82 | 综合广州 97% / 上海 90% 多源数据 |
| AI 偏差率 `ai_bias_rate` | 0.18 | NIST FRVT + 英国福利 AI 偏差 |
| 网格员容量 `gw_capacity` | 12 件/tick | 深圳南山日均 10-15 件 |
| 网格员效率 `gw_efficiency` | 0.73 | 基层复杂事务处理效率 |
| 超时阈值 `max_wait_ticks` | 30 tick | 对应约 15 个工作日 |

## 📈 关键结论

1. **公平感**：人感范式下群体间公平感 Gini 系数显著降低，指数接近 1.0
2. **弱势群体信任度**：提升约 +9%，"人工兜底"机制有效弥合信任赤字
3. **数字包容度**：适老化改造使弱势群体服务成功率提升约 +19%
4. **AI 偏差**：公平审查框架将偏差事件从 ~808 件降至 ~26 件（降幅 97%）
5. **系统韧性**：突发冲击下，网格员扩能机制提供 AI 失效时的服务连续性保障

## 📄 许可证

MIT License

## 📬 引用

```bibtex
@misc{wuxi-harmonious-city-2026,
  title   = {无锡城市人文治理多智能体仿真系统},
  author  = {殷梦娇},
  year    = {2026},
  url     = {https://github.com/AicbLab/wuxi-harmonious-city},
  note    = {无锡太湖学院/无锡民革殷梦娇课题组, 课题编号 WXSK26-C-107}
}
```
