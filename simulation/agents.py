# -*- coding: utf-8 -*-
"""
无锡城市人文治理多智能体仿真平台 —— 智能体定义模块 v2
===================================================
核心修正：
  - 诉求产生率下调（request_prob=0.008），与处理能力匹配
  - 信任动态引入"自然恢复"机制，避免单向衰减
  - VulnerableAgent 指标跟踪改为只计"已结案"的服务事件
  - AI 偏差事件对公平感产生更大负面冲击
"""

from __future__ import annotations

import random
from enum import Enum
from mesa import Agent


# ─────────────────────────── 枚举 ────────────────────────────────────────────

class CitizenType(Enum):
    NORMAL   = "normal"
    ELDERLY  = "elderly"
    DISABLED = "disabled"
    MIGRANT  = "migrant"


class RequestState(Enum):
    NONE    = "none"
    PENDING = "pending"
    DONE    = "done"      # 已处理（含成功和失败）
    TIMEOUT = "timeout"   # 超时未处理


# ─────────────────────────── 普通市民 ─────────────────────────────────────────

class CitizenAgent(Agent):
    """
    普通市民智能体

    状态变量
    --------
    digital_literacy : float [0,1]
    trust            : float [0,1]  对 AI 系统的信任
    fairness         : float [0,1]  公平感知
    satisfaction     : float [0,1]  最近一次服务满意度
    income_level     : float [0,1]
    """

    def __init__(self, model, *, digital_literacy=0.6, trust=0.5,
                 income_level=0.5):
        super().__init__(model)
        self.citizen_type = CitizenType.NORMAL
        self.digital_literacy = digital_literacy
        self.trust = trust
        self.fairness = 0.5
        self.satisfaction = 0.5
        self.income_level = income_level

        # 诉求相关
        self.req_state    = RequestState.NONE
        self.req_birth    = -1       # 诉求产生 tick
        self.req_done     = -1       # 诉求结案 tick
        self.wait_ticks   = 0
        self.response_delay = 0      # 最终响应时延

        # 累计统计
        self.n_services_total   = 0
        self.n_services_success = 0  # satisfaction >= 0.5
        self.n_timeouts         = 0

    # ── 每步行为 ──────────────────────────────────────────────────────────────

    def step(self):
        # 1) 产生诉求
        if self.req_state == RequestState.NONE:
            if random.random() < self.model.request_prob:
                self.req_state = RequestState.PENDING
                self.req_birth = self.model.tick
                self.wait_ticks = 0
                self.model.pending_requests.append(self)

        # 2) 等待中：检查超时
        if self.req_state == RequestState.PENDING:
            self.wait_ticks += 1
            if self.wait_ticks >= self.model.max_wait_ticks:
                self._timeout()

        # 3) 结案冷却 → 重置
        if self.req_state in (RequestState.DONE, RequestState.TIMEOUT):
            if self.model.tick - self.req_done >= 2:
                self.req_state = RequestState.NONE

        # 4) 信任自然恢复（缓慢向基线 0.5 漂移）
        self.trust += (0.5 - self.trust) * 0.005

    # ── 服务交互 ──────────────────────────────────────────────────────────────

    def receive_service(self, quality: float):
        """接收服务结果（由路由器/AI/网格员调用）"""
        if self.req_state != RequestState.PENDING:
            return   # 已超时或已处理，忽略

        self.response_delay = self.wait_ticks
        self.req_done  = self.model.tick
        self.req_state = RequestState.DONE
        self.satisfaction = quality
        self.n_services_total += 1
        if quality >= 0.5:
            self.n_services_success += 1

        # 信任更新：以满意度为锚点
        delta_trust = (quality - 0.5) * 0.25
        self.trust = max(0.0, min(1.0, self.trust + delta_trust))

        # 公平感知更新：与全局均值比较
        gap = quality - self.model.avg_service_quality
        self.fairness = max(0.0, min(1.0, self.fairness + gap * 0.2))

    def _timeout(self):
        """超时处理：信任/公平双降"""
        self.response_delay = self.wait_ticks
        self.req_done  = self.model.tick
        self.req_state = RequestState.TIMEOUT
        self.n_timeouts += 1
        self.n_services_total += 1
        # 超时带来较强负面反馈
        self.trust    = max(0.0, self.trust - 0.08)
        self.fairness = max(0.0, self.fairness - 0.06)


# ─────────────────────────── 弱势群体 ─────────────────────────────────────────

class VulnerableAgent(CitizenAgent):
    """
    弱势群体智能体（老年人 / 残障人士 / 外来务工）

    与普通市民的差异：
    - 数字素养更低（默认 0.15–0.30）
    - 诉求频率更高（×1.6）
    - 获得 AI 服务时存在"数字障碍折扣"
    - "人感城市"范式下折扣显著减轻
    """

    def __init__(self, model, *, citizen_type=CitizenType.ELDERLY,
                 digital_literacy=0.2, trust=0.4, income_level=0.25):
        super().__init__(model,
                         digital_literacy=digital_literacy,
                         trust=trust, income_level=income_level)
        self.citizen_type = citizen_type
        self.digital_barrier_count = 0   # 遭遇数字障碍的次数
        self.barrier_resolved_count = 0  # 障碍被化解的次数

    def step(self):
        # 诉求频率比普通市民高 60%
        if self.req_state == RequestState.NONE:
            if random.random() < self.model.request_prob * 1.6:
                self.req_state = RequestState.PENDING
                self.req_birth = self.model.tick
                self.wait_ticks = 0
                self.model.pending_requests.append(self)

        if self.req_state == RequestState.PENDING:
            self.wait_ticks += 1
            if self.wait_ticks >= self.model.max_wait_ticks:
                self._timeout()

        if self.req_state in (RequestState.DONE, RequestState.TIMEOUT):
            if self.model.tick - self.req_done >= 2:
                self.req_state = RequestState.NONE

        # 信任恢复略慢（弱势群体信任更难建立）
        self.trust += (0.4 - self.trust) * 0.003

    def receive_service(self, quality: float):
        """
        接收服务（含数字障碍折扣）

        传统模式：折扣 0.15–0.25（数字渠道不友好）
        人感城市模式：折扣 0.03–0.08（政策介入后障碍减轻）
        """
        if self.req_state != RequestState.PENDING:
            return

        # 数字障碍折扣
        if self.model.digital_inclusion_policy:
            discount = random.uniform(0.03, 0.08)
        else:
            discount = random.uniform(0.15, 0.25)

        effective_quality = max(0.0, quality - discount)

        # 记录障碍事件
        if discount > 0.12:
            self.digital_barrier_count += 1
        else:
            self.barrier_resolved_count += 1

        # 调用父类逻辑（传入折扣后的质量）
        # 需要直接实现，不能 super()，因为父类会检查 PENDING 状态
        self.response_delay = self.wait_ticks
        self.req_done  = self.model.tick
        self.req_state = RequestState.DONE
        self.satisfaction = effective_quality
        self.n_services_total += 1
        if effective_quality >= 0.5:
            self.n_services_success += 1

        # 信任更新
        delta_trust = (effective_quality - 0.5) * 0.30
        self.trust = max(0.0, min(1.0, self.trust + delta_trust))

        # 公平感知更新（对弱势群体，障碍加剧不公平感）
        gap = effective_quality - self.model.avg_service_quality
        self.fairness = max(0.0, min(1.0, self.fairness + gap * 0.25))


# ─────────────────────────── 网格员 ───────────────────────────────────────────

class GridWorkerAgent(Agent):
    """
    社区网格员智能体

    capacity   : 每 tick 处理上限
    efficiency : 基础服务质量（0–1）
    """

    def __init__(self, model, *, capacity=12, efficiency=0.72):
        super().__init__(model)
        self.capacity   = capacity
        self.efficiency = efficiency
        self.total_handled = 0
        self.overload_ticks = 0

    def step(self):
        queue = self.model.grid_worker_queue
        handled = 0
        while handled < self.capacity and queue:
            citizen = queue.pop(0)
            if citizen.req_state != RequestState.PENDING:
                continue
            # 服务质量 = 效率 ± 噪声
            quality = self.efficiency + random.gauss(0, 0.08)
            quality = max(0.05, min(0.95, quality))
            citizen.receive_service(quality)
            self.total_handled += 1
            handled += 1

        # 超负荷检测
        backlog = len(queue)
        if backlog > self.capacity * 3:
            self.overload_ticks += 1
            # 超负荷时效率衰减
            self.efficiency = max(0.4, self.efficiency - 0.01)


# ─────────────────────────── AI 算法系统 ──────────────────────────────────────

class AISystemAgent(Agent):
    """
    AI 算法系统智能体

    accuracy      : 算法准确率
    bias_rate     : 对弱势群体的歧视概率
    coverage      : 每 tick 处理的队列比例
    fairness_mode : True = 算法公平审查模式（"人感城市"范式）
    """

    def __init__(self, model, *, accuracy=0.80, bias_rate=0.15,
                 coverage=0.45, fairness_mode=False):
        super().__init__(model)
        self.accuracy      = accuracy
        self.bias_rate     = bias_rate
        self.coverage      = coverage
        self.fairness_mode = fairness_mode
        self.total_processed = 0
        self.bias_incidents  = 0

    def step(self):
        queue = self.model.ai_system_queue
        n_to_process = max(1, int(len(queue) * self.coverage))
        processed = 0

        while processed < n_to_process and queue:
            citizen = queue.pop(0)
            if citizen.req_state != RequestState.PENDING:
                continue

            is_vulnerable = isinstance(citizen, VulnerableAgent)

            # 偏差判定
            bias_prob = self.bias_rate
            if self.fairness_mode:
                bias_prob *= 0.25   # 公平审查模式大幅降低偏差

            if is_vulnerable and random.random() < bias_prob:
                # 偏差事件：服务质量大幅下降
                quality = random.uniform(0.10, 0.38)
                self.bias_incidents += 1
                citizen.receive_service(quality)
            else:
                # 正常处理
                quality = self.accuracy + random.gauss(0, 0.09)
                quality = max(0.10, min(0.98, quality))

                # 复杂诉求（15%）分流给网格员
                if random.random() < 0.15:
                    self.model.grid_worker_queue.append(citizen)
                else:
                    citizen.receive_service(quality)

            processed += 1
            self.total_processed += 1
