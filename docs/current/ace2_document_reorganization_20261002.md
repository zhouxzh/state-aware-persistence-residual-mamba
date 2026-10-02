# ace2 文档整理记录

日期：2026-10-02（Asia/Shanghai）。本次只整理文档和导航，不修改模型代码、配置、
数据、冻结发布物或校验和。

## 整理目标

将当前状态感知持久性残差 Mamba 的训练前研究设计，与已完成的 Regime-Gated Mamba
金融 S-only 研究明确隔离，避免后续 agent 将历史数值、图表或投稿审查误用为新模型证据。

## 变更

- 新增 `docs/current/README.md`，说明研究问题、M0--M3 比较、因果状态约束与训练前冻结
  要求；明确当前没有新实验结果。
- 新增 `docs/archive/financial_s_only/README.md`，作为历史金融发布物、分析表和图表的
  导航入口，但不移动冻结工件或图表。
- 将 `docs/journal_of_forecasting_submission_audit_20260914.md` 和
  `docs/manuscript_publication_gap_plan_20260914.md` 移至
  `docs/archive/financial_s_only/reviews/`。二者移动前后 SHA-256 相同。
- 更新根 `README.md`、`docs/README.md`、`docs/results_inventory.md`、
  `docs/repository_structure.md` 和 `docs/reproducibility.md`，明确其金融材料为历史记录，
  并记录 2026-10-02 原始输出清理后的路径状态。
- 新增 `docs/current/ace2_cleanup_20261002.md`，记录历史输出删除范围与冻结发布物校验结果。

## 保留边界

`reproducibility/financial_s_only_v1/`、`financial_s_only_v2/` 和
`financial_s_only_v2_supplement/` 未被修改。原有技术记录、分析文件、图表与清单也保留
原路径，以维持已有校验和、链接与审计可追溯性。

本次整理不授权任何训练、重跑、外部数据下载、结果选择或投稿操作。
