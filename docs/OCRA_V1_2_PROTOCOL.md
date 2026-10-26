# OCRA-v1.2：先转交、再打开

`ocra_v1.r2` 和 `ocra_v1.1.r4` 都完成了完整 train/validation 矩阵，但旧的“先判断
OPEN，再判断 DEFER”顺序无法安全地把可见水平跳变交给线性模型。只读 validation 检查显示：
把“最近 96 点内发生的水平跳变”先交给 DLinear，再对剩余原点判断 OPEN，可达到 100% 的
目标转交率，同时满足 N0/N2/N7/N8 安全限制。

`ocra_v1.2.r1` 使用 generator seed `20261050`、训练 seed
`20261051`--`20261055`、`ocra_v1_2_r1_` ID 前缀，完整运行根目录为
`results/ocra_v1_2_r1/`。该版本已完成 20 个 train/validation bundle，但在 E2 中因
GainGate validation macro false-open 为 0.02838、低于预注册的 0.05 下限而停止；test 数值
数组未生成或读取。该停止是该版本的有效结果，不能事后调整门槛重跑。未进入 test 的
`ocra_v1_2/` 保留了 E2 前的导入和特征接线错误记录。

执行顺序：

```bash
OCRA_CONFIG_DIR=configs/ocra_v1_2 OCRA_RUN_ID=ocra_v1_2_r1 \
  conda run --no-capture-output -n sci-agent python scripts/ocra_v1.py seal
OCRA_CONFIG_DIR=configs/ocra_v1_2 OCRA_RUN_ID=ocra_v1_2_r1 \
  conda run --no-capture-output -n sci-agent python scripts/ocra_v1.py preflight
```

E1 通过后，运行 `H=24, seed=20261041` 预检，再运行 20 个 bundle。E2 仍只看 validation；
只有 E2 通过才允许第一次生成 test 数值数组。监控器使用 `OCRA_MONITOR_RUN_ROOT=results/ocra_v1_2_r1`
和 `OCRA_MONITOR_RUN_ID=ocra_v1_2_r1`，每分钟防热、每 30 分钟写完整资源快照。
