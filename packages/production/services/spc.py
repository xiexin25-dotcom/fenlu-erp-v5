"""SPC (Statistical Process Control) · p-chart 控制图计算。

TASK-MFG-006

p-chart 公式 (不良率控制图):
    p_i = defect_count_i / sample_size_i          (每个子组的不良率)
    p_bar = Σ defect_count / Σ sample_size         (总平均不良率 = CL)
    UCL_i = p_bar + 3 * sqrt(p_bar*(1-p_bar)/n_i)  (上控制限)
    LCL_i = max(0, p_bar - 3 * sqrt(p_bar*(1-p_bar)/n_i))  (下控制限, 不低于0)

当所有子组样本量相同时, UCL/LCL 是常数; 否则每个点有自己的控制限。
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class SPCDataPoint:
    """单个子组的 SPC 数据点。"""

    index: int
    sample_size: int
    defect_count: int
    p: float       # 不良率
    ucl: float     # 上控制限
    cl: float      # 中心线 (p_bar)
    lcl: float     # 下控制限


@dataclass
class SPCResult:
    """完整 SPC 结果,可直接序列化给前端 Recharts。"""

    p_bar: float           # 总平均不良率
    total_inspected: int
    total_defects: int
    points: list[SPCDataPoint]


def compute_p_chart(
    samples: list[tuple[int, int]],
) -> SPCResult:
    """计算 p-chart 控制限。

    Args:
        samples: [(sample_size, defect_count), ...] 按时间顺序排列的子组数据。

    Returns:
        SPCResult

    Raises:
        ValueError: 如果 samples 为空或 sample_size <= 0。
    """
    if not samples:
        raise ValueError("samples must not be empty")

    total_inspected = 0
    total_defects = 0
    for n, d in samples:
        if n <= 0:
            raise ValueError(f"sample_size must be > 0, got {n}")
        if d < 0:
            raise ValueError(f"defect_count must be >= 0, got {d}")
        total_inspected += n
        total_defects += d

    p_bar = total_defects / total_inspected

    points: list[SPCDataPoint] = []
    for i, (n, d) in enumerate(samples):
        p_i = d / n
        sigma = math.sqrt(p_bar * (1 - p_bar) / n) if p_bar < 1 else 0.0
        ucl = p_bar + 3 * sigma
        lcl = max(0.0, p_bar - 3 * sigma)
        points.append(
            SPCDataPoint(
                index=i,
                sample_size=n,
                defect_count=d,
                p=round(p_i, 6),
                ucl=round(ucl, 6),
                cl=round(p_bar, 6),
                lcl=round(lcl, 6),
            )
        )

    return SPCResult(
        p_bar=round(p_bar, 6),
        total_inspected=total_inspected,
        total_defects=total_defects,
        points=points,
    )
