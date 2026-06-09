# -*- coding: utf-8 -*-
"""
无锡城市人文治理多智能体仿真平台 —— 实验运行与可视化 v2
====================================================
三组核心实验：
  实验一：基准对照（传统模式）
  实验二：人感城市范式介入
  实验三：突发情境压力测试（t=100 注入突发事件）
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ── 中文字体 ──────────────────────────────────────────────────────────────────
_FONT_CANDIDATES = ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei",
                    "Noto Sans CJK SC", "Arial Unicode MS"]
_FONT = next((f for f in _FONT_CANDIDATES
              if any(f in fp.name for fp in fm.fontManager.ttflist)),
             "sans-serif")
plt.rcParams["font.sans-serif"] = [_FONT, "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

from model import WuxiHumanGovernanceModel

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SEED       = 42
MAX_TICKS  = 200
N_REPEATS  = 5


# ─────────────────────────── 实验函数 ──────────────────────────────────────────

def run_single(governance_mode: str, seed: int = SEED,
               max_ticks: int = MAX_TICKS,
               stress_tick: int | None = None) -> pd.DataFrame:
    model = WuxiHumanGovernanceModel(
        governance_mode=governance_mode, seed=seed, max_ticks=max_ticks
    )
    for t in range(max_ticks):
        if stress_tick and t == stress_tick:
            _inject_stress_event(model)
        model.step()
    return model.datacollector.get_model_vars_dataframe()


def _inject_stress_event(model):
    """
    突发情境压力测试：
    - 诉求概率飙升至 0.25
    - 网格员效率下降 40%
    - AI 覆盖率下降 30%
    """
    print(f"  [!] 突发事件注入 @ tick {model.tick}")
    object.__setattr__(model, "request_prob", 0.25)

    from agents import GridWorkerAgent, AISystemAgent
    for agent in model.agents:
        if isinstance(agent, GridWorkerAgent):
            agent.efficiency *= 0.6
        if isinstance(agent, AISystemAgent):
            agent.coverage *= 0.7


def run_experiment(name: str, governance_mode: str,
                   stress_tick: int | None = None) -> pd.DataFrame:
    print(f"\n{'='*60}")
    print(f"  实验：{name}")
    print(f"  情景：{governance_mode}" +
          (f"  | 突发事件 @ tick {stress_tick}" if stress_tick else ""))
    print(f"  重复轮数：{N_REPEATS}")
    print(f"{'='*60}")

    all_dfs = []
    for i in range(N_REPEATS):
        seed_i = SEED + i * 100
        df = run_single(governance_mode, seed=seed_i,
                        max_ticks=MAX_TICKS, stress_tick=stress_tick)
        all_dfs.append(df)
        print(f"    轮次 {i+1}/{N_REPEATS} 完成")

    for df in all_dfs:
        df.index.name = "tick"
        df.reset_index(inplace=True)
    mean_df = pd.concat(all_dfs).groupby("tick").mean(numeric_only=True).reset_index()

    csv_path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    mean_df.to_csv(csv_path, index=False)
    print(f"  => 已保存：{csv_path}")
    return mean_df


# ─────────────────────────── 可视化 ────────────────────────────────────────────

import matplotlib.ticker as ticker
from matplotlib.patches import FancyBboxPatch
from matplotlib.collections import LineCollection


def _auto_ylim(*arrays, pad=0.15):
    """根据数据自动计算紧凑的 y 轴范围（只展示有差异的区间）"""
    all_vals = np.concatenate([a.dropna().values for a in arrays])
    lo, hi = all_vals.min(), all_vals.max()
    margin = (hi - lo) * pad
    if margin < 1e-6:
        margin = 0.05
    return lo - margin, hi + margin


# ── 全局暗色主题配色 ──────────────────────────────────────────────────────────
_BG         = "#0F1923"       # 深色背景
_GRID_CLR   = "#1E3A5F"       # 网格线
_TXT_CLR    = "#E8E8E8"       # 文字
_CLR_BASE   = "#00D4AA"       # 传统模式（青绿）
_CLR_PARA   = "#FF6B6B"       # 人感范式（珊瑚红）
_CLR_VULN_B = "#00D4AA"       # 弱势群体-基准（同色虚线）
_CLR_VULN_P = "#FF6B6B"       # 弱势群体-人感（同色虚线）
_CLR_STRESS = "#FFD93D"       # 压力测试（金黄）


def _dark_ax(ax, ylabel, title=""):
    """统一暗色风格坐标轴"""
    ax.set_facecolor(_BG)
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color=_TXT_CLR, pad=12)
    ax.set_ylabel(ylabel, color=_TXT_CLR, fontsize=10)
    ax.set_xlabel("仿真步（tick）", color=_TXT_CLR, fontsize=9)
    ax.tick_params(colors=_TXT_CLR, labelsize=8)
    ax.grid(True, color=_GRID_CLR, linewidth=0.4, alpha=0.6)
    for spine in ax.spines.values():
        spine.set_color(_GRID_CLR)
        spine.set_linewidth(0.6)


# ────────────────────── 图 1：公平感指数（渐变面积图）─────────────────────────

def _plot_fairness(ax, df_base, df_para):
    """面积填充 + 渐变效果，突出两场景间的差距"""
    t = df_base["tick"]
    y1, y2 = df_base["fairness_index"], df_para["fairness_index"]
    ylim = _auto_ylim(y1, y2)

    # 两条曲线
    ax.plot(t, y1, color=_CLR_BASE, linewidth=2.2, label="传统模式",
            zorder=5)
    ax.plot(t, y2, color=_CLR_PARA, linewidth=2.2, label="人感城市范式",
            zorder=5)

    # 两线之间的面积填充（半透明）
    ax.fill_between(t, y1, y2, alpha=0.25, color=_CLR_PARA,
                    interpolate=True, zorder=2)
    ax.fill_between(t, ylim[0], y1, alpha=0.06, color=_CLR_BASE, zorder=1)

    # 终值标注
    for y, c, dy in [(y1.iloc[-1], _CLR_BASE, -12), (y2.iloc[-1], _CLR_PARA, 10)]:
        ax.annotate(f"{y:.4f}", xy=(t.iloc[-1], y),
                    fontsize=9, fontweight="bold", color=c,
                    xytext=(5, dy), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor=_BG,
                              edgecolor=c, linewidth=0.8))

    ax.set_ylim(ylim)
    _dark_ax(ax, "公平感指数", "① 公平感指数")
    ax.legend(fontsize=8, loc="lower left", facecolor=_BG,
              labelcolor=_TXT_CLR, edgecolor=_GRID_CLR)


# ────────────────────── 图 2：信任度演化（多线 + 置信带）─────────────────────

def _plot_trust(ax, df_base, df_para):
    """主线 + 虚线子群体 + 半透明置信带"""
    t = df_base["tick"]
    ylim = _auto_ylim(df_base["trust_vulnerable"], df_para["trust_normal"])

    # 主线（粗 + 发光效果）
    ax.plot(t, df_base["trust_level"], color=_CLR_BASE, linewidth=2.4,
            label="传统模式-总体", zorder=5)
    ax.plot(t, df_para["trust_level"], color=_CLR_PARA, linewidth=2.4,
            label="人感范式-总体", zorder=5)

    # 弱势群体（虚线）
    ax.plot(t, df_base["trust_vulnerable"], color=_CLR_BASE, linewidth=1.2,
            linestyle=(0, (4, 3)), alpha=0.7, label="传统-弱势群体", zorder=4)
    ax.plot(t, df_para["trust_vulnerable"], color=_CLR_PARA, linewidth=1.2,
            linestyle=(0, (4, 3)), alpha=0.7, label="人感-弱势群体", zorder=4)

    # 普通市民（点线）
    ax.plot(t, df_base["trust_normal"], color=_CLR_BASE, linewidth=0.9,
            linestyle=(0, (1, 3)), alpha=0.5, label="传统-普通市民", zorder=3)
    ax.plot(t, df_para["trust_normal"], color=_CLR_PARA, linewidth=0.9,
            linestyle=(0, (1, 3)), alpha=0.5, label="人感-普通市民", zorder=3)

    # 人感范式的信任带（总体 ± 弱势群体之间）
    ax.fill_between(t, df_para["trust_vulnerable"], df_para["trust_normal"],
                    alpha=0.08, color=_CLR_PARA, zorder=1)

    ax.set_ylim(ylim)
    _dark_ax(ax, "平均信任度", "② 市民信任度演化")
    ax.legend(fontsize=6.5, loc="lower right", facecolor=_BG,
              labelcolor=_TXT_CLR, edgecolor=_GRID_CLR, ncol=2)


# ────────────────────── 图 3：数字包容度（阶梯面积 + 终点标注）─────────────────

def _plot_inclusion(ax, df_base, df_para):
    """阶梯填充 + 箭头标注"""
    t = df_base["tick"]
    y1, y2 = df_base["digital_inclusion"], df_para["digital_inclusion"]
    ylim = _auto_ylim(y1, y2)

    # 阶梯线
    ax.step(t, y1, where="mid", color=_CLR_BASE, linewidth=2.0,
            label="传统模式", zorder=5)
    ax.step(t, y2, where="mid", color=_CLR_PARA, linewidth=2.0,
            label="人感城市范式", zorder=5)

    # 面积填充
    ax.fill_between(t, y1, step="mid", alpha=0.12, color=_CLR_BASE, zorder=1)
    ax.fill_between(t, y2, step="mid", alpha=0.12, color=_CLR_PARA, zorder=1)

    # 差距标注（在 tick=180 处画双向箭头）
    mid_t = 180
    v1 = y1.iloc[mid_t]
    v2 = y2.iloc[mid_t]
    ax.annotate("", xy=(mid_t, v2), xytext=(mid_t, v1),
                arrowprops=dict(arrowstyle="<->", color="#FFFFFF",
                                linewidth=1.8, mutation_scale=15))
    ax.text(mid_t + 3, (v1 + v2) / 2, f"Δ={v2-v1:.2f}",
            fontsize=10, fontweight="bold", color="#FFFFFF",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#333333",
                      edgecolor="#FFFFFF", linewidth=0.6))

    ax.set_ylim(ylim)
    _dark_ax(ax, "数字包容度", "③ 数字包容度")
    ax.legend(fontsize=8, loc="center right", facecolor=_BG,
              labelcolor=_TXT_CLR, edgecolor=_GRID_CLR)


# ────────────────────── 图 4：响应时延（圆点散点 + 趋势线）───────────────────

def _plot_delay(ax, df_base, df_para):
    """散点 + 平滑趋势线"""
    t = df_base["tick"]
    cols = [("avg_response_delay", "总体"), ("vulnerable_avg_delay", "弱势群体")]
    ylim = _auto_ylim(
        df_base["avg_response_delay"], df_base["vulnerable_avg_delay"],
        df_para["avg_response_delay"], df_para["vulnerable_avg_delay"],
    )

    markers = ["o", "s"]
    for (col, sublbl), mk in zip(cols, markers):
        # 基准（空心散点）
        ax.scatter(t, df_base[col], s=8, color="none", edgecolors=_CLR_BASE,
                   linewidths=0.6, marker=mk, alpha=0.4, zorder=3)
        ax.plot(t, df_base[col], color=_CLR_BASE, linewidth=1.0,
                alpha=0.6, label=f"传统-{sublbl}", zorder=4)

        # 人感（实心散点）
        ax.scatter(t, df_para[col], s=10, color=_CLR_PARA, marker=mk,
                   alpha=0.5, zorder=3)
        ax.plot(t, df_para[col], color=_CLR_PARA, linewidth=1.4,
                alpha=0.8, label=f"人感-{sublbl}", zorder=4)

    ax.set_ylim(ylim)
    _dark_ax(ax, "响应时延（tick）", "④ 治理响应时延")
    ax.legend(fontsize=7, loc="upper left", facecolor=_BG,
              labelcolor=_TXT_CLR, edgecolor=_GRID_CLR)


# ────────────────────── 主绘图入口 ────────────────────────────────────────────

def plot_comparison(results: dict[str, pd.DataFrame]):
    keys = list(results.keys())
    df_base, df_para = results[keys[0]], results[keys[1]]

    fig = plt.figure(figsize=(15, 10), facecolor=_BG)
    fig.patch.set_facecolor(_BG)
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.28,
                          left=0.07, right=0.96, top=0.92, bottom=0.06)

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    _plot_fairness(ax1, df_base, df_para)
    _plot_trust(ax2, df_base, df_para)
    _plot_inclusion(ax3, df_base, df_para)
    _plot_delay(ax4, df_base, df_para)

    fig.suptitle("无锡城市人文治理多智能体仿真 —— 情景对比",
                 fontsize=16, fontweight="bold", color=_TXT_CLR, y=0.98)
    out_path = os.path.join(OUTPUT_DIR, "comparison.png")
    plt.savefig(out_path, dpi=180, facecolor=_BG, bbox_inches="tight")
    print(f"\n图表已保存：{out_path}")
    plt.close()


# ────────────────────── 压力测试图 ────────────────────────────────────────────

def plot_stress_test(baseline_df: pd.DataFrame, stress_df: pd.DataFrame):
    fig = plt.figure(figsize=(16, 5), facecolor=_BG)
    fig.patch.set_facecolor(_BG)
    gs = fig.add_gridspec(1, 3, wspace=0.30,
                          left=0.06, right=0.97, top=0.95, bottom=0.12)

    configs = [
        ("trust_level",        "平均信任度",    _plot_stress_single_line),
        ("digital_inclusion",  "数字包容度",    _plot_stress_single_fill),
        ("avg_response_delay", "响应时延（tick）", _plot_stress_single_spike),
    ]

    for i, (col, title, plot_fn) in enumerate(configs):
        ax = fig.add_subplot(gs[0, i])
        plot_fn(ax, baseline_df, stress_df, col, title)

    # fig.suptitle removed per user request
    out_path = os.path.join(OUTPUT_DIR, "stress_test.png")
    plt.savefig(out_path, dpi=180, facecolor=_BG, bbox_inches="tight")
    print(f"压力测试图已保存：{out_path}")
    plt.close()


def _plot_stress_single_line(ax, base, stress, col, title):
    """信任度：渐变线条 + 事件标记"""
    t = base["tick"]
    ylim = _auto_ylim(base[col], stress[col])
    ax.plot(t, base[col], color=_CLR_BASE, linewidth=2.2, label="基准")
    ax.plot(t, stress[col], color=_CLR_STRESS, linewidth=2.2,
            linestyle="--", label="压力测试")
    # 事件后区域着色
    ax.axvspan(100, t.max(), alpha=0.08, color=_CLR_STRESS, zorder=0)
    ax.axvline(x=100, color="#FFFFFF", linestyle=":", linewidth=1.2, alpha=0.5)
    ax.set_ylim(ylim)
    _dark_ax(ax, title, title)
    ax.legend(fontsize=7, facecolor=_BG, labelcolor=_TXT_CLR,
              edgecolor=_GRID_CLR, loc="lower right")


def _plot_stress_single_fill(ax, base, stress, col, title):
    """数字包容度：面积对比 + 崩溃区域高亮"""
    t = base["tick"]
    ylim = _auto_ylim(base[col], stress[col])
    ax.fill_between(t, base[col], alpha=0.15, color=_CLR_BASE, zorder=1)
    ax.plot(t, base[col], color=_CLR_BASE, linewidth=2.0, label="基准")
    ax.fill_between(t, stress[col], alpha=0.15, color=_CLR_STRESS, zorder=1)
    ax.plot(t, stress[col], color=_CLR_STRESS, linewidth=2.0,
            linestyle="--", label="压力测试")
    # 崩溃区间高亮
    ax.axvspan(100, t.max(), alpha=0.10, color="#FF0000", zorder=0)
    ax.axvline(x=100, color="#FFFFFF", linestyle=":", linewidth=1.2, alpha=0.5)
    ax.set_ylim(ylim)
    _dark_ax(ax, title, title)
    ax.legend(fontsize=7, facecolor=_BG, labelcolor=_TXT_CLR,
              edgecolor=_GRID_CLR, loc="lower left")


def _plot_stress_single_spike(ax, base, stress, col, title):
    """响应时延：脉冲尖峰标注"""
    t = base["tick"]
    ylim = _auto_ylim(base[col], stress[col])
    ax.plot(t, base[col], color=_CLR_BASE, linewidth=1.8, label="基准")
    ax.plot(t, stress[col], color=_CLR_STRESS, linewidth=2.2,
            linestyle="--", label="压力测试")
    # 尖峰标注
    peak_idx = stress[col].idxmax()
    peak_t = stress["tick"].iloc[peak_idx]
    peak_v = stress[col].iloc[peak_idx]
    ax.annotate(f"峰值 {peak_v:.3f}", xy=(peak_t, peak_v),
                fontsize=9, fontweight="bold", color=_CLR_STRESS,
                xytext=(10, 12), textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color=_CLR_STRESS, lw=1.4),
                bbox=dict(boxstyle="round,pad=0.3", facecolor=_BG,
                          edgecolor=_CLR_STRESS, linewidth=0.8))
    ax.axvspan(100, t.max(), alpha=0.06, color="#FF0000", zorder=0)
    ax.axvline(x=100, color="#FFFFFF", linestyle=":", linewidth=1.2, alpha=0.5)
    ax.set_ylim(ylim)
    _dark_ax(ax, title, title)
    ax.legend(fontsize=7, facecolor=_BG, labelcolor=_TXT_CLR,
              edgecolor=_GRID_CLR, loc="upper left")


# ─────────────────────────── 主程序 ────────────────────────────────────────────

def main():
    print("="*60)
    print("  无锡城市人文治理多智能体仿真平台 v2.0")
    print("  10,000 Agent 原型验证（参数校准版）")
    print("="*60)

    # 实验一
    df_baseline = run_experiment(
        name="exp1_baseline_traditional",
        governance_mode="traditional")

    # 实验二
    df_paradigm = run_experiment(
        name="exp2_wuxi_paradigm",
        governance_mode="wuxi_paradigm")

    # 实验三
    df_stress = run_experiment(
        name="exp3_stress_test",
        governance_mode="wuxi_paradigm",
        stress_tick=100)

    # 可视化
    plot_comparison({
        "实验一：传统模式（基准）": df_baseline,
        "实验二：人感城市范式":     df_paradigm,
    })
    plot_stress_test(df_paradigm, df_stress)

    # 关键差异摘要
    print("\n" + "="*60)
    print("  关键指标对比（稳态均值，tick 150–200）")
    print("="*60)
    cols = [
        ("fairness_index",       "公平感指数"),
        ("trust_level",          "平均信任度"),
        ("trust_vulnerable",     "弱势群体信任度"),
        ("digital_inclusion",    "数字包容度"),
        ("avg_response_delay",   "平均响应时延"),
        ("vulnerable_avg_delay",  "弱势群体时延"),
        ("timeout_rate",         "诉求超时率"),
        ("ai_bias_incidents",    "AI偏差事件数"),
    ]
    for col, lbl in cols:
        v_base = df_baseline[col].tail(50).mean()
        v_para = df_paradigm[col].tail(50).mean()
        diff   = v_para - v_base
        sign   = "↑" if diff > 0 else "↓"
        print(f"  {lbl:12s}  传统={v_base:.4f}  人感={v_para:.4f}  "
              f"差异={sign}{abs(diff):.4f}")

    print("\n仿真完成！所有输出文件位于：", OUTPUT_DIR)


if __name__ == "__main__":
    main()
