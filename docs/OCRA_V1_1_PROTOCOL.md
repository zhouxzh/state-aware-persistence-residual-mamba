# OCRA-v1.1: 可观测水平跳变修订协议

日期：2026-10-24。状态：探索性独立复核，尚未训练。

## 为什么新开版本

`ocra_v1.r2` 已按原规则完成 20 个 train/validation bundle，但 E2 失败：在满足所有
负集合约束的 2,082 个 validation 阈值中，已见水平跳变的最高 `DEFER` 比例只有 20.53%，
低于原来 80% 的要求。其测试数组从未生成或读取。

原规则把“很久以前发生、已离开 384 点历史窗口的水平跳变”仍计作必须识别的 `DEFER`
原点。那类原点没有可用的跳变时间证据，故本版本只对历史内仍可见的跳变做 `T1-vis`
路由要求。旧版的失败保持不变，不能用新版本改写。

## 修改内容

- 新 generator seed `20261030`，新训练 seeds `20261031`--`20261035`，新 ID 前缀
  `ocra_v1_1_r4_`，并检查其与 canonical 和旧 OCRA roster 无交集。未训练的
  `ocra_v1_1/` E1 自交检查失败记录、`ocra_v1_1_r1/` 特征清单遗漏记录和
  `ocra_v1_1_r2/` 预检 seed 写死记录和 `ocra_v1_1_r3/` 报告分类遗漏记录均保留原处；
  当前有效封存版本为 `ocra_v1.1.r4`。
- 仍使用 canonical_v2 的九机制、训练预算、M2/M1/DLinear/M0/SeasonalNaive 模型和测试
  一次性访问规则。
- 证书输入增加两项只由历史计算的特征：最大一阶差分的稳健分数和该差分距当前原点的
  相对时间。
- `visible_level_shift` 仅在 `origin - change_point <= 192` 时进入 `T1-vis`，目标为
  `DEFER`；其余已见但不再可观测的原点单独报告为 `T1-post-observable`，不作为成功证据。
- v1.1 的结论是探索性的，不能和 r2 或 canonical_v2 的确认性结论合并。

## 执行顺序

1. `OCRA_CONFIG_DIR=configs/ocra_v1_1 OCRA_RUN_ID=ocra_v1_1_r4 python scripts/ocra_v1.py seal`
2. 同环境运行 `preflight` 与注册的 `H=24, seed=20261031` 单骨干预检。
3. 仅在预检通过后运行 20 个 train/validation bundle。
4. E2 只使用 validation；通过才允许首次物化 test 并运行 E3--E7。
