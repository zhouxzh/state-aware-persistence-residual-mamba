# Third-Party Notices

The MIT license applies to original Regime-Gated Mamba contributions only. Inherited or copied
third-party material remains subject to its own license and notice requirements.

| Local material | Upstream source | License status | Release action |
| --- | --- | --- | --- |
| `utils/timefeatures.py` | Amazon time-feature utility | Apache-2.0 header retained in source | Keep its header and Apache-2.0 notice |
| `layers/SelfAttention_Family.py` Informer-derived section | `zhouhaoyi/Informer2020` | Apache-2.0 | Retain attribution and Apache-2.0 notice |
| `layers/SelfAttention_Family.py` Flowformer-derived section | `thuml/Flowformer` | MIT | Retain attribution |
| `layers/SelfAttention_Family.py` FlashAttention-derived section | `shreyansh26/FlashAttention-PyTorch` | MIT according to its repository | Retain attribution |
| Python dependencies | `requirements.txt` | Each package has its own license | Resolve in the distribution environment, not this source notice |

Inherited source notices must remain attached to their corresponding files. Dataset
provider terms are governed separately by the archived source protocol at
`reproducibility/financial_reference_evaluation_v1/protocol/financial_confirmatory_source.json`
and are not granted by this software license.
