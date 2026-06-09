# -*- coding: utf-8 -*-
"""
无锡城市人文治理多智能体仿真平台 —— 涌现指标计算模块 v2
=====================================================
修正：
  - 数字包容度改为只计已结案的服务事件
  - 公平感指数增加群体内方差惩罚
"""

from __future__ import annotations

import numpy as np
from agents import CitizenAgent, VulnerableAgent, CitizenType


def _all_citizens(model):
    return [a for a in model.agents
            if isinstance(a, (CitizenAgent, VulnerableAgent))]

def _vulnerable(model):
    return [a for a in model.agents if isinstance(a, VulnerableAgent)]

def _normal(model):
    return [a for a in model.agents
            if isinstance(a, CitizenAgent) and not isinstance(a, VulnerableAgent)]

def _gini(vals):
    arr = np.array(vals, dtype=float)
    arr = arr[arr > 0]
    if arr.size < 2:
        return 0.0
    arr = np.sort(arr)
    n = len(arr)
    cumsum = np.cumsum(arr)
    return float((n + 1 - 2 * cumsum.sum() / cumsum[-1]) / n)


# ─── 指标 1：公平感指数 ──────────────────────────────────────────────────────

def fairness_index(model) -> float:
    """
    公平感指数 = 1 - Gini(各群体平均fairness)

    越接近 1 表示公共服务分配越公平。
    """
    citizens = _all_citizens(model)
    if not citizens:
        return 0.0

    group_means = {}
    for ct in CitizenType:
        vals = [c.fairness for c in citizens if c.citizen_type == ct]
        if vals:
            group_means[ct.value] = float(np.mean(vals))

    if len(group_means) < 2:
        return float(np.mean([c.fairness for c in citizens]))

    return max(0.0, 1.0 - _gini(list(group_means.values())))


# ─── 指标 2：信任度 ──────────────────────────────────────────────────────────

def trust_level(model) -> float:
    citizens = _all_citizens(model)
    return float(np.mean([c.trust for c in citizens])) if citizens else 0.0

def trust_level_vulnerable(model) -> float:
    vulns = _vulnerable(model)
    return float(np.mean([v.trust for v in vulns])) if vulns else 0.0

def trust_level_normal(model) -> float:
    normals = _normal(model)
    return float(np.mean([n.trust for n in normals])) if normals else 0.0


# ─── 指标 3：数字包容度 ──────────────────────────────────────────────────────

def digital_inclusion(model) -> float:
    """
    数字包容度 = 弱势群体成功服务数 / 已结案服务总数

    只统计已结案（DONE 或 TIMEOUT）的事件，未结案的不计入。
    success 标准：satisfaction >= 0.5（在 receive_service 中已记录）
    """
    vulns = _vulnerable(model)
    if not vulns:
        return 0.0

    total   = sum(v.n_services_total for v in vulns)
    success = sum(v.n_services_success for v in vulns)

    if total == 0:
        return 1.0   # 尚无事件时默认满分

    return success / total


def vulnerable_barrier_rate(model) -> float:
    """弱势群体遭遇数字障碍的比率（越低越好）"""
    vulns = _vulnerable(model)
    if not vulns:
        return 0.0
    barriers = sum(v.digital_barrier_count for v in vulns)
    total_events = barriers + sum(v.barrier_resolved_count for v in vulns)
    if total_events == 0:
        return 0.0
    return barriers / total_events


# ─── 指标 4：治理响应时延 ────────────────────────────────────────────────────

def avg_response_delay(model) -> float:
    citizens = _all_citizens(model)
    delays = [c.response_delay for c in citizens if c.response_delay > 0]
    return float(np.mean(delays)) if delays else 0.0

def p95_response_delay(model) -> float:
    citizens = _all_citizens(model)
    delays = [c.response_delay for c in citizens if c.response_delay > 0]
    return float(np.percentile(delays, 95)) if delays else 0.0

def vulnerable_avg_delay(model) -> float:
    vulns = _vulnerable(model)
    delays = [v.response_delay for v in vulns if v.response_delay > 0]
    return float(np.mean(delays)) if delays else 0.0

def timeout_rate(model) -> float:
    """诉求超时率（越低说明治理能力越强）"""
    citizens = _all_citizens(model)
    total = sum(c.n_services_total for c in citizens)
    timeouts = sum(c.n_timeouts for c in citizens)
    return timeouts / total if total > 0 else 0.0


# ─── 综合快照 ────────────────────────────────────────────────────────────────

def collect_snapshot(model) -> dict:
    return {
        "tick":                  model.tick,
        "fairness_index":        fairness_index(model),
        "trust_level":           trust_level(model),
        "trust_vulnerable":      trust_level_vulnerable(model),
        "trust_normal":          trust_level_normal(model),
        "digital_inclusion":     digital_inclusion(model),
        "vulnerable_barrier_rate": vulnerable_barrier_rate(model),
        "avg_response_delay":    avg_response_delay(model),
        "p95_response_delay":    p95_response_delay(model),
        "vulnerable_avg_delay":  vulnerable_avg_delay(model),
        "timeout_rate":          timeout_rate(model),
        "pending_queue_size":    len(model.pending_requests),
        "ai_bias_incidents":     sum(
            a.bias_incidents for a in model.agents
            if hasattr(a, "bias_incidents")
        ),
    }
