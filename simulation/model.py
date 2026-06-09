# -*- coding: utf-8 -*-
"""
无锡城市人文治理多智能体仿真平台 —— 主模型 v2
============================================
核心校准修正：
  - 诉求产生率下调（0.008），与处理能力匹配
  - 网格员扩编至 100 人，AI 系统扩至 5 个
  - 场景差异通过多个参数通道注入，确保涌现差异
  - 路由器根据场景动态调整分流比例
"""

from __future__ import annotations

import random
import numpy as np
from mesa import Model
from mesa.datacollection import DataCollector

from agents import (
    CitizenAgent, VulnerableAgent, GridWorkerAgent, AISystemAgent,
    CitizenType, RequestState,
)
import metrics


# ─────────────────────────── 模型参数 ─────────────────────────────────────────

DEFAULT_PARAMS = dict(
    # ── 人口结构 ──────────────────────────────────────────────────────────────
    n_citizens       = 7000,     # 普通市民
    n_elderly        = 1500,     # 老年人
    n_disabled       = 500,      # 残障人士
    n_migrant        = 1000,     # 外来务工
    n_grid_workers   = 100,      # 网格员
    n_ai_systems     = 5,        # AI 系统

    # ── 诉求产生（校准后）────────────────────────────────────────────────────
    request_prob     = 0.008,    # 每 tick 每市民基础诉求概率

    # ── AI 系统参数 ───────────────────────────────────────────────────────────
    ai_accuracy      = 0.82,
    ai_bias_rate     = 0.18,     # 传统模式偏差率
    ai_coverage      = 0.50,     # 每 AI 系统每 tick 处理队列比例

    # ── 网格员参数 ────────────────────────────────────────────────────────────
    gw_capacity      = 12,       # 每网格员每 tick 处理上限
    gw_efficiency    = 0.73,

    # ── 政策情景 ──────────────────────────────────────────────────────────────
    # "traditional"    = 传统效率优先模式
    # "wuxi_paradigm"  = 人感城市范式（本研究提出）
    governance_mode  = "traditional",

    # ── 仿真控制 ──────────────────────────────────────────────────────────────
    max_ticks        = 200,
    max_wait_ticks   = 30,       # 诉求超时 tick（放宽以避免过高超时率）
    seed             = 42,
)


# ─────────────────────────── 主模型 ───────────────────────────────────────────

class WuxiHumanGovernanceModel(Model):
    """
    无锡城市人文治理多智能体仿真模型 v2

    用法
    ----
    >>> m = WuxiHumanGovernanceModel(governance_mode="wuxi_paradigm")
    >>> df = m.run(n_ticks=200)
    """

    def __init__(self, **kwargs):
        # 提取 seed，避免与 Mesa 内置属性冲突
        seed_val = kwargs.pop("seed", 42)
        super().__init__()
        self._rng = np.random.default_rng(seed_val)
        object.__setattr__(self, "seed", seed_val)

        # 合并参数
        params = {**DEFAULT_PARAMS, **kwargs}
        params.pop("seed", None)
        for k, v in params.items():
            object.__setattr__(self, k, v)

        self.tick = 0
        self.avg_service_quality = 0.5

        # 诉求队列
        self.pending_requests:  list = []
        self.ai_system_queue:   list = []
        self.grid_worker_queue: list = []

        # 政策开关
        self.digital_inclusion_policy = (self.governance_mode == "wuxi_paradigm")
        self.fairness_audit_mode      = (self.governance_mode == "wuxi_paradigm")

        # 场景差异化参数
        if self.governance_mode == "wuxi_paradigm":
            # 人感城市模式：网格员扩能、AI 偏差大幅降低、分流更倾向网格员
            self._ai_route_ratio    = 0.55   # AI 处理比例下降
            self._gw_efficiency_adj = 1.12   # 网格员效率提升（培训赋能）
            self._gw_capacity_adj   = 1.20   # 网格员容量提升
        else:
            self._ai_route_ratio    = 0.72   # 传统模式 AI 优先
            self._gw_efficiency_adj = 1.0
            self._gw_capacity_adj   = 1.0

        # 创建智能体
        self._create_agents()

        # 数据采集器
        self.datacollector = DataCollector(
            model_reporters={
                "fairness_index":         lambda m: metrics.fairness_index(m),
                "trust_level":            lambda m: metrics.trust_level(m),
                "trust_vulnerable":       lambda m: metrics.trust_level_vulnerable(m),
                "trust_normal":           lambda m: metrics.trust_level_normal(m),
                "digital_inclusion":      lambda m: metrics.digital_inclusion(m),
                "vulnerable_barrier_rate": lambda m: metrics.vulnerable_barrier_rate(m),
                "avg_response_delay":     lambda m: metrics.avg_response_delay(m),
                "p95_response_delay":     lambda m: metrics.p95_response_delay(m),
                "vulnerable_avg_delay":   lambda m: metrics.vulnerable_avg_delay(m),
                "timeout_rate":           lambda m: metrics.timeout_rate(m),
                "pending_queue_size":     lambda m: len(m.pending_requests),
                "ai_bias_incidents":      lambda m: sum(
                    a.bias_incidents for a in m.agents
                    if hasattr(a, "bias_incidents")
                ),
            },
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  智能体创建
    # ──────────────────────────────────────────────────────────────────────────

    def _create_agents(self):
        rng = np.random.default_rng(self.seed)

        # 普通市民
        for _ in range(self.n_citizens):
            CitizenAgent(self,
                digital_literacy=float(rng.beta(5, 2)),
                trust=float(rng.beta(5, 5)),
                income_level=float(rng.beta(2, 2)))

        # 老年人
        for _ in range(self.n_elderly):
            VulnerableAgent(self,
                citizen_type=CitizenType.ELDERLY,
                digital_literacy=float(rng.beta(2, 6)),
                trust=float(rng.beta(4, 6)),
                income_level=float(rng.beta(2, 4)))

        # 残障人士
        for _ in range(self.n_disabled):
            VulnerableAgent(self,
                citizen_type=CitizenType.DISABLED,
                digital_literacy=float(rng.beta(2, 5)),
                trust=float(rng.beta(3, 6)),
                income_level=float(rng.beta(2, 5)))

        # 外来务工
        for _ in range(self.n_migrant):
            VulnerableAgent(self,
                citizen_type=CitizenType.MIGRANT,
                digital_literacy=float(rng.beta(3, 4)),
                trust=float(rng.beta(3, 5)),
                income_level=float(rng.beta(2, 3)))

        # 网格员（场景调整容量/效率）
        for _ in range(self.n_grid_workers):
            eff = float(rng.normal(self.gw_efficiency, 0.08))
            eff = max(0.40, min(0.92, eff)) * self._gw_efficiency_adj
            cap = int(self.gw_capacity * self._gw_capacity_adj)
            GridWorkerAgent(self, capacity=cap, efficiency=eff)

        # AI 系统（场景调整偏差率）
        bias_rate = self.ai_bias_rate
        if self.fairness_audit_mode:
            bias_rate *= 0.25   # 人感模式偏差率降低 75%

        for _ in range(self.n_ai_systems):
            acc = float(rng.normal(self.ai_accuracy, 0.04))
            br  = float(rng.normal(bias_rate, 0.03))
            AISystemAgent(self,
                accuracy=max(0.5, min(0.95, acc)),
                bias_rate=max(0.01, min(0.40, br)),
                coverage=self.ai_coverage,
                fairness_mode=self.fairness_audit_mode)

    # ──────────────────────────────────────────────────────────────────────────
    #  仿真主循环
    # ──────────────────────────────────────────────────────────────────────────

    def step(self):
        """
        单步逻辑：
        ① 市民 step（产生诉求 / 超时检测 / 信任恢复）
        ② 路由分流
        ③ AI 系统处理
        ④ 网格员处理
        ⑤ 更新全局统计
        ⑥ 采集指标
        """
        # ① 市民行为
        citizens = [a for a in self.agents
                    if isinstance(a, (CitizenAgent, VulnerableAgent))]
        random.shuffle(citizens)
        for agent in citizens:
            agent.step()

        # ② 路由分流
        self._route_requests()

        # ③ AI 系统处理
        for ai in (a for a in self.agents if isinstance(a, AISystemAgent)):
            ai.step()

        # ④ 网格员处理
        for gw in (a for a in self.agents if isinstance(a, GridWorkerAgent)):
            gw.step()

        # ⑤ 全局服务质量滑动均值
        sats = [c.satisfaction for c in citizens if c.satisfaction > 0]
        if sats:
            self.avg_service_quality = float(np.mean(sats))

        # ⑥ 采集
        self.datacollector.collect(self)
        self.tick += 1

    def _route_requests(self):
        """将 pending_requests 中的新诉求分流至 AI 或网格员队列"""
        to_route = [c for c in self.pending_requests
                    if c.req_state == RequestState.PENDING]
        self.pending_requests = []

        random.shuffle(to_route)
        for citizen in to_route:
            # 已在队列中的不重复添加
            if citizen in self.ai_system_queue or citizen in self.grid_worker_queue:
                continue

            is_vuln = isinstance(citizen, VulnerableAgent)

            if self.governance_mode == "wuxi_paradigm" and is_vuln:
                # 人感模式：弱势群体 65% → 网格员，35% → AI
                if random.random() < 0.65:
                    self.grid_worker_queue.append(citizen)
                else:
                    self.ai_system_queue.append(citizen)
            else:
                # 常规路由
                if random.random() < self._ai_route_ratio:
                    self.ai_system_queue.append(citizen)
                else:
                    self.grid_worker_queue.append(citizen)

    # ──────────────────────────────────────────────────────────────────────────
    #  运行接口
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, n_ticks=None):
        n = n_ticks or self.max_ticks
        for _ in range(n):
            self.step()
        return self.datacollector.get_model_vars_dataframe()
