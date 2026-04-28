import torch
import torch.nn as nn

from layers.Embed import DataEmbedding
from layers.SelfAttention_Family import AttentionLayer, DSAttention
from layers.Transformer_EncDec import Decoder, DecoderLayer, Encoder, EncoderLayer


class Projector(nn.Module):
    """MLP used to learn de-stationary tau and delta factors."""

    def __init__(self, enc_in, seq_len, hidden_dims, hidden_layers, output_dim, kernel_size=3):
        super(Projector, self).__init__()
        if not hidden_dims:
            raise ValueError("hidden_dims must contain at least one value")

        padding = 1 if torch.__version__ >= "1.5.0" else 2
        self.series_conv = nn.Conv1d(
            in_channels=seq_len,
            out_channels=1,
            kernel_size=kernel_size,
            padding=padding,
            padding_mode="circular",
            bias=False,
        )

        layers = [nn.Linear(2 * enc_in, hidden_dims[0]), nn.ReLU()]
        for i in range(hidden_layers - 1):
            layers += [nn.Linear(hidden_dims[i], hidden_dims[i + 1]), nn.ReLU()]
        layers += [nn.Linear(hidden_dims[-1], output_dim, bias=False)]
        self.backbone = nn.Sequential(*layers)

    def forward(self, x, stats):
        batch_size = x.shape[0]
        x = self.series_conv(x)
        x = torch.cat([x, stats], dim=1)
        x = x.reshape(batch_size, -1)
        return self.backbone(x)


class Model(nn.Module):
    """
    Non-stationary Transformer adapted to this repo's forecasting interface.
    Paper: https://openreview.net/pdf?id=ucNDIDRNjjv
    """

    def __init__(self, configs):
        super(Model, self).__init__()
        self.task_name = getattr(configs, "task_name", "long_term_forecast")
        self.pred_len = configs.pred_len
        self.seq_len = configs.seq_len
        self.label_len = configs.label_len
        self.output_attention = configs.output_attention

        p_hidden_dims = list(getattr(configs, "p_hidden_dims", [128, 128]))
        p_hidden_layers = int(getattr(configs, "p_hidden_layers", len(p_hidden_dims)))
        if len(p_hidden_dims) < p_hidden_layers:
            p_hidden_dims = p_hidden_dims + [p_hidden_dims[-1]] * (p_hidden_layers - len(p_hidden_dims))

        self.enc_embedding = DataEmbedding(
            configs.enc_in,
            configs.d_model,
            configs.embed,
            configs.freq,
            configs.dropout,
        )
        self.dec_embedding = DataEmbedding(
            configs.dec_in,
            configs.d_model,
            configs.embed,
            configs.freq,
            configs.dropout,
        )

        self.encoder = Encoder(
            [
                EncoderLayer(
                    AttentionLayer(
                        DSAttention(
                            False,
                            configs.factor,
                            attention_dropout=configs.dropout,
                            output_attention=configs.output_attention,
                        ),
                        configs.d_model,
                        configs.n_heads,
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
        self.decoder = Decoder(
            [
                DecoderLayer(
                    AttentionLayer(
                        DSAttention(
                            True,
                            configs.factor,
                            attention_dropout=configs.dropout,
                            output_attention=False,
                        ),
                        configs.d_model,
                        configs.n_heads,
                    ),
                    AttentionLayer(
                        DSAttention(
                            False,
                            configs.factor,
                            attention_dropout=configs.dropout,
                            output_attention=False,
                        ),
                        configs.d_model,
                        configs.n_heads,
                    ),
                    configs.d_model,
                    configs.d_ff,
                    dropout=configs.dropout,
                    activation=configs.activation,
                )
                for _ in range(configs.d_layers)
            ],
            norm_layer=torch.nn.LayerNorm(configs.d_model),
            projection=nn.Linear(configs.d_model, configs.c_out, bias=True),
        )

        self.tau_learner = Projector(
            enc_in=configs.enc_in,
            seq_len=configs.seq_len,
            hidden_dims=p_hidden_dims,
            hidden_layers=p_hidden_layers,
            output_dim=1,
        )
        self.delta_learner = Projector(
            enc_in=configs.enc_in,
            seq_len=configs.seq_len,
            hidden_dims=p_hidden_dims,
            hidden_layers=p_hidden_layers,
            output_dim=configs.seq_len,
        )

    def _normalize(self, x_enc):
        mean_enc = x_enc.mean(1, keepdim=True).detach()
        x_norm = x_enc - mean_enc
        std_enc = torch.sqrt(torch.var(x_norm, dim=1, keepdim=True, unbiased=False) + 1e-5).detach()
        return x_norm / std_enc, mean_enc, std_enc

    def forecast(self, x_enc, x_mark_enc, x_dec, x_mark_dec):
        x_raw = x_enc.clone().detach()
        x_enc, mean_enc, std_enc = self._normalize(x_enc)

        tau = self.tau_learner(x_raw, std_enc).exp()
        delta = self.delta_learner(x_raw, mean_enc)

        x_dec = torch.cat(
            [x_enc[:, -self.label_len:, :], torch.zeros_like(x_dec[:, -self.pred_len:, :])],
            dim=1,
        ).to(x_enc.device)

        enc_out = self.enc_embedding(x_enc, x_mark_enc)
        enc_out, attns = self.encoder(enc_out, attn_mask=None, tau=tau, delta=delta)

        dec_out = self.dec_embedding(x_dec, x_mark_dec)
        dec_out = self.decoder(dec_out, enc_out, x_mask=None, cross_mask=None, tau=tau, delta=delta)
        dec_out = dec_out * std_enc + mean_enc
        return dec_out, attns

    def forward(self, x_enc, x_mark_enc, x_dec, x_mark_dec, mask=None):
        dec_out, attns = self.forecast(x_enc, x_mark_enc, x_dec, x_mark_dec)
        dec_out = dec_out[:, -self.pred_len:, :]
        if self.output_attention:
            return dec_out, attns
        return dec_out
