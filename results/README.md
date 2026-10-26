# 结果目录说明

此目录保存完整、可再审计的运行产物，默认被 Git 忽略。请从
[`docs/results_registry.md`](../docs/results_registry.md) 查找每个命名空间对应的协议锁、
校验和、覆盖判定和派生分析。

- 不移动、改名、覆盖或删除冻结命名空间中的文件。
- `metrics_all.csv`、`campaign_manifest.json`、`task_manifest.json` 和失败记录共同构成
  完整矩阵；不能只保留表现良好的子集。
- OCRA-v1.2.r1 的完整运行产物位于 `results/ocra_v1_2_r1/`；先前 OCRA 版本各自保留原始协议标签和停止记录，不能混合或覆盖。
- 任何数值结论都必须由保留产物重算并核对校验和，不能从控制器状态或日志转述。
