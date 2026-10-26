# Study 3 后续仿真计划：未来跳变覆盖与状态摘要负控

**协议状态**：计划草案，尚未批准、未锁定、未运行。  
**代码仓库**：`zhong3:~/Documents/state-aware-persistence-residual-mamba`  
**与现有研究的关系**：独立 Study 3；不修改、不重跑、不覆盖 Study 1（九机制仿真）或 Study 2（matched-encoder follow-up）的锁、test、结果和结论。

## 1. 为什么需要 Study 3

当前论文的主要结论不需要新的仿真即可成立，但仍有两个明确的科学边界：

1. Study 1 的 future-jump offset 为 48。H=12 和 H=24 行评估跳变前的 random-walk background，而不是预测窗内发生的跳变；H=48 是否包含端点取决于生成器索引约定。
2. Study 2 的 C4 只测试各 residual head 相对 persistence 的显著有利误差告警。它没有对 Mamba 的 summary-on 与 summary-off 在 N2/N8 上做预先声明的 non-inferiority 或安全性检验。因此，Study 2 的 S4/S6 摘要增益不能外推为负控安全保证。

Study 3 只在作者希望扩展这两个边界时运行。它不是为改变现有结果、修复已发表数字或选择更有利模型而设计。

## 2. 预注册问题与限定性主张

### P1：预测窗内未来跳变

在相同背景机制下，将事件 offset 预先固定为 12，使事件满足 `0 < change_point - origin <= H=24`。主 estimand 是 residual head 相对 persistence 的 paired series-level path RMSE difference，限定在真正位于 H=24 预测窗内的 N2 origins。

**可支持的主张**：在明确的 random-walk background、H=24 和指定 offset=12 条件下，模型是否错误地显著预报一个历史中不可见的未来跳变。  
**不可支持的主张**：对所有 future-jump offset、所有 horizon 或所有自回归背景均成立的普遍结论。

### P2：状态摘要在负控上的增量与边界

在 MambaPhi 与 Mamba0 的相同结构、数据、训练预算和共同原点上，直接比较 summary-on minus summary-off。主 estimand 分别在 S4、S6、N2、N8 报告；N2/N8 是安全边界，不把“不显著”解释为等价。

**可支持的主张**：在预先声明的 non-inferiority margin 内，summary-on 是否未明显损害 N2/N8 的 RMSE；以及 summary increment 是否只出现在已见变化机制。  
**不可支持的主张**：summary 的内部 selective-state 因果作用，或在未运行强 ablation 时的通用安全性。

## 3. 数据生成与共同原点

- 长度 `T=2048`，季节周期 `P=48`，唯一主 horizon `H=24`。
- Study 3 重新生成 train/validation/test，使用与 Study 1/2 不重叠的 generator seed 和 training seed；不得复用旧 test roster。
- train/validation/test 分别为 2,000/550/1,100 series，使用独立 split RNG。
- 所有 lookback 使用同一组合法 `L=768` origins；`L=96` 和 `L=384` 是同一长历史的 suffix。
- S4/S6 主 visible subset 使用与 Study 2 相同的 metadata 规则：`o-96 <= cp < o` 且 `o >= cp+12`。
- N2 主 subset 只保留 `0 < cp-o <= 24`，并记录真实 event offset；offset=12 仅作为设计中心，不得在生成后筛选最佳 offset。
- N8 使用预先定义的 near-random-walk 生成器；其 increment predictability 参数必须在 test 前写入锁文件。
- 每组主 test subset 预先锁定 100 series；覆盖不足时报告失败，不通过改变阈值或删除 series 修复。

## 4. 模型矩阵

主矩阵固定为：

| Lookback | Heads | Seeds |
|---|---|---:|
| L=384 | MambaPhi, Mamba0, TransformerPhi, Transformer0 | 5 each |
| L=96 | MambaPhi, Mamba0 | 5 each |
| L=768 | MambaPhi, Mamba0 | 5 each |

共 40 个训练 cell。所有条件使用同一训练预算、batch、optimizer、epoch 上限、early stopping 和验证规则。Study 2 的已知 MLP125/125、advancing RNG 等偏差不得默默延伸为 Study 3 的设计；Study 3 应在锁文件中明确真实执行字段。

不训练外部门控，不把 MambaPhi 与 Mamba0 解释为 gate intervention。Transformer0 只作为 summary representation control，不作为 selective-state causal control。

## 5. 主统计与安全规则

### 5.1 主指标

对每个 test series、model、seed 和 group，先在该 series 的注册 origins 上计算 path RMSE，再对五个训练 seed 求 series-level mean。Paired bootstrap 的基本单位是 independent test series，不是 origins，也不是五个 seed 当作五个独立实验。

报告：

- paired percentile bootstrap 95% interval，10,000 resamples；
- paired random sign-flip p-value，仅作为预先锁定的对称差值检验；
- Holm correction，按预先声明的 family；
- 普通 interval 不称为 multiplicity-adjusted interval。

### 5.2 P1 future-jump leakage rule

N2 的每个 residual-minus-persistence contrast 若 estimate < 0、ordinary CI upper bound < 0 且 family-Holm p<0.05，则触发 leakage review。未触发不证明无泄漏；触发也先审计 generator、origin metadata 和 input lineage，不直接宣称泄漏。

### 5.3 P2 summary safety rule

在 N2/N8 上，预先声明 summary-on minus summary-off 的 non-inferiority margin `delta`，并在 test 前锁定其单位和理由。只有当 95% paired interval 的 lower bound 高于 `-delta` 时，才可写“未观察到超过预设 margin 的恶化”；这不是等价性证明，也不是无害性证明。

S4/S6 的 summary increment 仍按 superiority 方向报告。不得因 N2/N8 结果不利而删除 S4/S6 结果，也不得因 S4/S6 有利而隐藏 N8 trade-off。

### 5.4 Seed/retraining uncertainty

主估计仍以五个 fitted seed 平均后的 series-level RMSE 为单位，并明确为 conditional on the realized training roster。若要估计 retraining variability，必须另设 exploratory crossed analysis，至少保存每个 seed 的 paired series losses；不得用现有 mean-only CSV 事后伪造这一层不确定性。

## 6. Test 前 release gate

test 访问前必须同时通过：

1. 40/40 training cells complete，0 failed；
2. runner、model、feature、config 和 analysis source hashes 与锁一致；
3. 所有 checkpoint strict-load、finite、parameter-count match；
4. train/validation/test roster、common-origin、event metadata hashes match；
5. coverage counts meet the frozen minimums；
6. test arrays 尚未物化，且 one-time access ledger 不存在；
7. analysis script、bootstrap seed、Holm family 和 margin 在 test 前固定；
8. release binding 写明 Study 3 与 Study 1/2 不混池。

只要一个 gate 失败，就保持 test 锁定。不得为修复论文措辞而重跑 Study 1/2，也不得在看到 test 后修改 `delta`、event offset、primary subset 或 family。

## 7. 结果发布字段

必须保存 compact、可校验文件：

- `protocol.json`：Study 3 版本、event offset、margin、seeds、families、hashes；
- `coverage.json`：每组 series/origin/event-offset 计数；
- `sequence_rmse.csv`：每 series、model、seed、group 的 RMSE 及 origins；
- `paired_comparisons.csv`：完整 contrasts、ordinary CI、raw p、Holm p；
- `resource_metrics.csv`：参数量、训练时间、峰值显存和端到端推理时间；
- `release_binding.json`：source/config/metrics/output/test ledger SHA-256；
- `deviations.md`：任何实际实现与计划差异，按发现时间和推断影响记录。

checkpoint、预测数组、原始 test 数据和缓存不得复制进论文仓库；它们留在 zhong3 的运行目录。

## 8. 对当前论文的关系

Study 3 结果不得回写为 Study 1 或 Study 2 的结果，也不得把当前论文改写为 Study 3 已完成。当前论文可在没有 Study 3 的情况下投稿为：

- Study 1：机制条件化的 persistence-anchored residual comparison；
- Study 2：带测试前偏差披露的 matched-encoder follow-up；
- Study 3：未来工作/独立后续协议，尚未运行。

**状态**：本计划只完成协议草案和服务器归档，不授权训练、不授权 test、不授权推送。
