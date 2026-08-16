# ace2 代码 Agent 实验补充任务书

状态：仅为实验规范，未授权自动启动任务
日期：2026-08-12（Asia/Shanghai）
远端执行仓库：`zhong@ace2:~/Documents/pms-mamba-financial-forecasting`
本地论文仓库：`D:\Github\nonstationary-mamba`

## 1. 目的

为论文生成可提交的、统一协议的 S-only 回顾性证据。当前本地活动证据
`reproducibility/financial_s_only_review_v0/` 明确是 interim、post hoc、retrospective、
not submission-ready。它把当前学习模型重跑摘要和归档的确定性基线拼在一起，且部分
比较模型与旧表不一致，不能直接升级为投稿结果。

2026-08-12 远端预检：ace2 为 `main@f5a694d3f18565af2cd46a6f7005027d92c13a1f`，无活动
训练/分析/Optuna 进程，RTX 5090 D 利用率为 0%，磁盘剩余约 370 GB。远端已有
`results/financial_baseline_rerun_v1/`，包含 8 个任务（S/MS）和 5 个学习基线模型的
1,200 个完成运行，但没有 Regime-Gated Mamba、Last-value、random-walk-with-drift、
ARIMA 的统一结果，因此不能作为本任务的最终发布物。

## 2. 操作安全

- 本文档不授权启动、停止、重启、删除或重排远端任务。
- 开始任何运行前必须获得明确授权，并重新执行 AGENTS.md 中的只读远端预检。
- 不修改冻结协议，不打开新的受保护测试集，不用 2023--2026 结果重新选择模型。
- 不覆盖旧发布物；新结果必须写入版本化目录。
- 不复制 `.git/`、缓存、TensorBoard、日志、wheel、检查点或虚拟环境到论文 Git 仓库。
- 文件必须在两次观察中大小和修改时间稳定，或由完成清单原子确认后再归档。

## 3. 目标协议

建议新发布物名称：`financial_s_only_retrospective_v1`，证据状态：
`retrospective_protocol_matched`。

仅运行以下四个 target-only 任务，不运行 `_ms` 输入任务，也不为删除 MS 而重新构造
目标序列：

- `financial_cross_asset_s`
- `financial_crypto_s`
- `financial_fx_s`
- `financial_yields_s`

固定条件：

- 数据边界、目标构造、训练/验证/测试切分和数据哈希沿用现有 `_s` 记录。
- 训练截止 2020-12-31，验证为 2021-01-01--2022-12-31，回顾性测试为
  2023-01-01--2026-06-30。
- horizons：`1, 5, 20, 60, 120, 252` retained observations。
- learned seeds：`2023, 2024, 2025, 2026, 2027`。
- 主指标：path RMSSE；同时输出 MAE、RMSE，terminal 指标作为次要结果。
- 所有模型必须使用相同 forecast origins、逆变换规则和 RMSSE denominator。
- 2023--2026 已被查看，所有新结果必须标为 retrospective，不能称为 untouched 或
  prospective test。

## 4. 主比较矩阵

必须包含：

1. `Regime-Gated Mamba`（论文提议模型）；
2. `Last-value`、`random-walk-with-drift`、`ARIMA`；
3. `DLinear`、`NLinear`、`PatchTST`、`TimesNet`、`iTransformer`；
4. `Inverted Mamba`、`Decomposition Mamba`，以及只有在当前代码、参数快照和运行
   环境可完整复现时才纳入的 Multi-Scale Mamba 变体。

如果最终纳入 10 个 learned models，期望为 `4 x 10 x 5 = 200` 个
task-model-seed runs，产生 1,200 个 learned per-seed horizon rows；三个确定性基线
产生 `4 x 3 x 6 = 72` 个 task-model-horizon rows。若模型列表不同，必须在 protocol 中
更新期望计数，不能留下缺口。

注意：`financial_*_ms` 是多变量输入任务；`Multi-Scale` 出现在模型名中不等于运行
`_ms` 任务。是否保留该模型作为 S-only learned comparator，必须在运行前写入模型清单，
不能看完结果后决定。

## 5. 必须增加的消融

消融用于判断结果是否来自 persistence anchor、linear change path 或 gate，而不是只
增加更多黑盒基线：

- persistence-only：与 `Last-value` 完全一致的锚点；
- ungated linear change：保留 linear change path，移除 Mamba horizon gate；
- full Regime-Gated Mamba：当前实现，作为预先指定的主模型；
- 可选的固定 gate 或移除 RevIN，只有在运行开始前写入 protocol 才能执行。

S-only 当前实现中，两个 cross-channel standard deviation 输入恒为零。第一阶段原样
重跑以审计实现；若改成 rolling temporal statistics 或其他非退化输入，必须新建模型
标识、配置和 evidence release，并只用 2022 年以前的开发数据选择，不能与当前模型
静默合并。

## 6. 不确定性和统计分析

- 结果表同时给出每个 task-horizon 的五 seed 均值、seed 分布、cell rank、winner 和
  与三个强基线的 paired difference。
- 必须保留每个 origin/lead 的 `pred`、`true`、`origin_dates` 和逐起点损失，原始数组
  放在外部校验归档，不提交到普通 Git 文件。
- 预先规定依赖感知的区间方法（例如按 forecast-origin block bootstrap 或其他经作者
  批准的方法），并记录 block 长度、重复次数、随机种子和多重比较规则。
- 四个任务是四个主要独立簇；不能把 24 个 task-horizon cells 当作 24 个独立观测进行
  普通显著性检验。任务级区间应明确标为描述性并同时展示逐任务结果。
- 不把非显著写成等效，不把点估计胜出写成稳定或普遍优势。

## 7. 发布物和验收

输出目录：`reproducibility/financial_s_only_retrospective_v1/`，至少包含：

- `README.md`、`protocol/`、`training_datasets.json`、`model_identity_map.json`；
- 选择参数快照和运行环境（Python、PyTorch、CUDA、GPU）；
- learned per-seed metrics、确定性基线 metrics、统一 aggregate/ranking 表；
- paired contrasts、seed stability、origin-level uncertainty、ablation 表；
- `release_status.json`（expected/completed/missing/failures）；
- `claim_evidence_map.md`；
- `SHA256SUMS`，并在发布前完整验证。

发布前必须同时满足：

1. branch、commit、dirty 状态、环境和硬件已记录；
2. 四个 `_s` 数据哈希与协议一致；
3. 所有计划单元完成，无仍在写入的文件；
4. 统计基线与 learned models 使用相同 origins 和 RMSSE denominator；
5. 失败、排除、旧结果差异均有书面说明；
6. `SHA256SUMS` 通过；
7. 生成一份新的结果到论文 claim 的映射。

只有在上述发布物复制到本地并二次校验后，论文 agent 才能替换正文中的 interim
数字、表格和图。不得把旧冻结表或当前 `financial_baseline_rerun_v1` 的部分行与新结果
静默拼接。

## 8. 回传给论文 agent 的最小报告

请回传：远端预检记录、协议文件哈希、完成/缺失矩阵、每个模型和任务的运行计数、
失败清单、统一指标表路径、逐起点数组外部归档路径与校验值、消融结果、区间方法和
最终 `SHA256SUMS` 验证结果。没有这些信息时，只报告阻塞，不提供新的论文数字。
