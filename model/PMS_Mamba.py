import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from layers.Embed import PatchEmbedding
from layers.Mamba_EncDec import Encoder, EncoderLayer
from layers.NonStationaryGate import NonStationaryGate
from layers.SeriesDecomp import SeriesDecompResidual
from mamba_ssm import Mamba


class FlattenHead(nn.Module):
    def __init__(self, nf, target_window, dropout=0.0):
        super(FlattenHead, self).__init__()
        self.flatten = nn.Flatten(start_dim=-2)
        self.linear = nn.Linear(nf, target_window)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.flatten(x)
        x = self.linear(x)
        return self.dropout(x)


class PatchMambaBranch(nn.Module):
    def __init__(self, configs, input_len):
        super(PatchMambaBranch, self).__init__()
        self.patch_len = configs.patch_len
        self.stride = configs.stride
        self.patch_embedding = PatchEmbedding(
            configs.d_model,
            self.patch_len,
            self.stride,
            self.stride,
            configs.dropout,
        )
        self.encoder = Encoder(
            [
                EncoderLayer(
                    Mamba(
                        d_model=configs.d_model,
                        d_state=configs.d_state,
                        d_conv=2,
                        expand=1,
                    ),
                    Mamba(
                        d_model=configs.d_model,
                        d_state=configs.d_state,
                        d_conv=2,
                        expand=1,
                    ),
                    configs.d_model,
                    configs.d_ff,
                    dropout=configs.dropout,
                    activation=configs.activation,
                )
                for _ in range(configs.e_layers)
            ],
            norm_layer=torch.nn.LayerNorm(configs.d_model),
        )
        patch_num = max(1, int((input_len - self.patch_len) / self.stride + 2))
        self.head = FlattenHead(
            configs.d_model * patch_num,
            configs.pred_len,
            dropout=configs.dropout,
        )

    def forward(self, x):
        # x: [B, L, C]
        x = x.permute(0, 2, 1)
        enc_out, n_vars = self.patch_embedding(x)
        enc_out, _ = self.encoder(enc_out, attn_mask=None)
        enc_out = enc_out.reshape(-1, n_vars, enc_out.shape[-2], enc_out.shape[-1])
        enc_out = enc_out.permute(0, 1, 3, 2)
        return self.head(enc_out)


class Model(nn.Module):
    """
    Patch multi-scale Mamba forecaster.

    This model targets the gap with PatchTST by making Mamba operate over
    temporal patch sequences instead of only over inverted variable tokens.
    It keeps the GLD-friendly reversible normalization and can add the same
    trend/seasonal/residual component split used by MS_Mamba.
    """

    def __init__(self, configs):
        super(Model, self).__init__()
        self.seq_len = configs.seq_len
        self.pred_len = configs.pred_len
        self.output_attention = configs.output_attention
        self.use_norm = bool(configs.use_norm)
        self.residual_target = bool(getattr(configs, "residual_target", 0))
        self.ms_use_decomp = bool(getattr(configs, "ms_use_decomp", 1))
        self.ms_fusion = getattr(configs, "ms_fusion", "gate")
        self.ms_scales = self._parse_scales(getattr(configs, "ms_scales", [1, 2, 4]))
        self.component_count = 3 if self.ms_use_decomp else 1

        if self.ms_fusion not in ("gate", "learned", "mean"):
            raise ValueError("ms_fusion must be one of: gate, learned, mean")

        self.decomp = SeriesDecompResidual(configs.moving_avg) if self.ms_use_decomp else None
        self.branches = nn.ModuleList(
            [
                PatchMambaBranch(configs, self._scaled_length(configs.seq_len, scale))
                for scale in self.ms_scales
            ]
        )

        if self.ms_fusion == "gate":
            self.scale_gate = NonStationaryGate(
                d_model=configs.d_model,
                hidden_dim=2 * configs.d_model,
                gate_dim=configs.pred_len,
                num_gates=len(self.ms_scales),
                recent_ratio=getattr(configs, "ns_recent_ratio", 0.25),
                dropout=configs.dropout,
                activation="softmax",
            )
            self.scale_logits = None
        elif self.ms_fusion == "learned":
            self.scale_gate = None
            self.scale_logits = nn.Parameter(torch.zeros(len(self.ms_scales)))
        else:
            self.scale_gate = None
            self.register_parameter("scale_logits", None)

    def _parse_scales(self, scales):
        if isinstance(scales, int):
            scales = [scales]
        parsed = []
        for scale in scales:
            scale = int(scale)
            if scale <= 0:
                raise ValueError("all ms_scales must be positive integers")
            if scale not in parsed:
                parsed.append(scale)
        return parsed

    def _scaled_length(self, length, scale):
        return max(1, int(math.ceil(length / scale)))

    def _standard_normalize(self, x):
        means = x.mean(1, keepdim=True).detach()
        centered = x - means
        stdev = torch.sqrt(torch.var(centered, dim=1, keepdim=True, unbiased=False) + 1e-5)
        return centered / stdev, means, stdev

    def _standard_denormalize(self, x, means, stdev):
        x = x * stdev[:, 0, :].unsqueeze(1).repeat(1, self.pred_len, 1)
        return x + means[:, 0, :].unsqueeze(1).repeat(1, self.pred_len, 1)

    def _downsample(self, x, scale):
        if scale == 1:
            return x
        if scale >= x.size(1):
            return x.mean(dim=1, keepdim=True)
        x = x.permute(0, 2, 1)
        x = F.avg_pool1d(x, kernel_size=scale, stride=scale, ceil_mode=True)
        return x.permute(0, 2, 1)

    def _component_tokens(self, x):
        if self.decomp is None:
            return x
        seasonal, trend, residual = self.decomp(x)
        return torch.cat([trend, seasonal, residual], dim=-1)

    def _branch_forecast(self, branch, x, num_vars):
        out = branch(x)
        if self.component_count == 1:
            return out[:, :num_vars, :]

        out = out.reshape(out.size(0), self.component_count, num_vars, self.pred_len)
        return out.sum(dim=1)

    def _fuse_scales(self, scale_outputs, raw_x, num_vars):
        stack = torch.stack(scale_outputs, dim=2)
        if self.scale_gate is not None:
            weights = self.scale_gate(raw_x, target_tokens=num_vars)
            return (weights * stack).sum(dim=2)
        if self.scale_logits is not None:
            weights = torch.softmax(self.scale_logits, dim=0).view(1, 1, -1, 1)
            return (weights * stack).sum(dim=2)
        return stack.mean(dim=2)

    def forecast(self, x_enc, x_mark_enc, x_dec, x_mark_dec):
        raw_x = x_enc
        _, _, num_vars = x_enc.shape
        means = None
        stdev = None

        if self.use_norm:
            x_enc, means, stdev = self._standard_normalize(x_enc)

        x_tokens = self._component_tokens(x_enc)
        scale_outputs = []
        for scale, branch in zip(self.ms_scales, self.branches):
            scale_x = self._downsample(x_tokens, scale)
            scale_outputs.append(self._branch_forecast(branch, scale_x, num_vars))

        dec_out = self._fuse_scales(scale_outputs, raw_x, num_vars).permute(0, 2, 1)

        if self.residual_target:
            if self.use_norm:
                dec_out = self._standard_denormalize(dec_out, raw_x[:, -1:, :], stdev)
            else:
                dec_out = dec_out + raw_x[:, -1:, :]
        elif self.use_norm:
            dec_out = self._standard_denormalize(dec_out, means, stdev)

        return dec_out, None

    def forward(self, x_enc, x_mark_enc, x_dec, x_mark_dec, mask=None):
        dec_out, attns = self.forecast(x_enc, x_mark_enc, x_dec, x_mark_dec)
        dec_out = dec_out[:, -self.pred_len:, :]
        if self.output_attention:
            return dec_out, attns
        return dec_out
