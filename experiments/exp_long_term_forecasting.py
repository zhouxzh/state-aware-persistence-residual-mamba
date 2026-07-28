import random

from data_provider.data_factory import data_provider
from experiments.exp_basic import Exp_Basic
from utils.tools import EarlyStopping, adjust_learning_rate, visual
from utils.metrics import metric
import torch
import torch.nn as nn
from torch import optim
import os
import subprocess
import time
import warnings
import json
import numpy as np

warnings.filterwarnings('ignore')


class Exp_Long_Term_Forecast(Exp_Basic):
    def __init__(self, args):
        super(Exp_Long_Term_Forecast, self).__init__(args)

    def _metric_feature_slice(self, data):
        if self.args.features == 'MS':
            return data[..., -1:]
        return data

    def _rmsse_insample(self):
        train_data, _ = self._get_data(flag='train')
        insample = train_data.data_x
        if getattr(train_data, 'scale', False) and self.args.inverse:
            insample = train_data.inverse_transform(insample)
        return self._metric_feature_slice(insample)

    def _build_model(self):
        model = self.model_dict[self.args.model].Model(self.args).float()

        if self.args.use_multi_gpu and self.args.use_gpu:
            model = nn.DataParallel(model, device_ids=self.args.device_ids)
        return model

    def _get_data(self, flag):
        data_set, data_loader = data_provider(self.args, flag)
        return data_set, data_loader

    def _wait_for_thermal_resume(self):
        guard_temp = int(getattr(self.args, 'thermal_guard_temp', 0) or 0)
        if guard_temp <= 0 or not self.args.use_gpu:
            return
        resume_temp = int(getattr(self.args, 'thermal_resume_temp', guard_temp - 5))
        poll_seconds = float(getattr(self.args, 'thermal_poll_seconds', 5.0))
        gpu_id = int(getattr(self.args, 'gpu', 0))
        announced = False
        while True:
            try:
                result = subprocess.run(
                    [
                        'nvidia-smi',
                        f'--id={gpu_id}',
                        '--query-gpu=temperature.gpu',
                        '--format=csv,noheader,nounits',
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                temperature = int(result.stdout.strip().splitlines()[0])
            except (OSError, subprocess.SubprocessError, ValueError, IndexError) as exc:
                print(f'Thermal guard disabled after temperature query failed: {exc}')
                return
            if temperature < guard_temp and not announced:
                return
            if announced and temperature <= resume_temp:
                print(f'GPU thermal guard resumed at {temperature}C')
                return
            if not announced:
                print(
                    f'GPU thermal guard pausing at {temperature}C; '
                    f'waiting for <= {resume_temp}C'
                )
                announced = True
            time.sleep(max(1.0, poll_seconds))

    def _maybe_wait_for_thermal_resume(self, batch_index):
        check_batches = int(getattr(self.args, 'thermal_check_batches', 0) or 0)
        if check_batches > 0 and batch_index % check_batches == 0:
            self._wait_for_thermal_resume()

    def _inverse_transform_batch(self, data_set, array):
        shape = array.shape
        flat = array.reshape(-1, shape[-1])
        if self.args.features == 'MS' and shape[-1] == 1 and hasattr(data_set, 'inverse_transform_target'):
            restored = data_set.inverse_transform_target(flat)
        else:
            restored = data_set.inverse_transform(flat)
        return restored.reshape(shape)

    def _concat_prediction_batches(self, batches):
        if not batches:
            raise ValueError('prediction batches must not be empty')
        return np.concatenate(batches, axis=0)

    def _select_optimizer(self):
        model_optim = optim.Adam(self.model.parameters(), lr=self.args.learning_rate)
        return model_optim

    def _select_criterion(self):
        criterion = nn.MSELoss()
        return criterion

    def _forward_batch(self, batch_x, batch_y, batch_x_mark, batch_y_mark):
        batch_x = batch_x.float().to(self.device)
        batch_y = batch_y.float().to(self.device)

        if 'PEMS' in self.args.data or 'Solar' in self.args.data:
            batch_x_mark = None
            batch_y_mark = None
        else:
            batch_x_mark = batch_x_mark.float().to(self.device)
            batch_y_mark = batch_y_mark.float().to(self.device)

        dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
        dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)
        if self.args.use_amp:
            with torch.cuda.amp.autocast():
                if self.args.output_attention:
                    outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                else:
                    outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
        else:
            if self.args.output_attention:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
            else:
                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)

        f_dim = -1 if self.args.features == 'MS' else 0
        outputs = outputs[:, -self.args.pred_len:, f_dim:]
        batch_y = batch_y[:, -self.args.pred_len:, f_dim:]
        return outputs, batch_y, batch_x

    def _collect_predictions(self, data_set, data_loader, visual_dir=None):
        preds = []
        trues = []

        self.model.eval()
        with torch.no_grad():
            for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(data_loader):
                self._maybe_wait_for_thermal_resume(i)
                outputs, targets, batch_x_device = self._forward_batch(batch_x, batch_y, batch_x_mark, batch_y_mark)
                outputs_scaled = outputs.detach().cpu().numpy()
                targets_scaled = targets.detach().cpu().numpy()
                outputs_np = outputs_scaled
                targets_np = targets_scaled

                if data_set.scale and self.args.inverse:
                    outputs_np = self._inverse_transform_batch(data_set, outputs_np)
                    targets_np = self._inverse_transform_batch(data_set, targets_np)

                preds.append(outputs_np)
                trues.append(targets_np)

                if visual_dir is not None and i % 20 == 0:
                    input_np = batch_x_device.detach().cpu().numpy()
                    if data_set.scale and self.args.inverse:
                        input_np = self._inverse_transform_batch(data_set, input_np)
                    gt = np.concatenate((input_np[0, :, -1], targets_np[0, :, -1]), axis=0)
                    pd = np.concatenate((input_np[0, :, -1], outputs_np[0, :, -1]), axis=0)
                    visual(gt, pd, os.path.join(visual_dir, str(i) + '.pdf'))

        preds = self._concat_prediction_batches(preds)
        trues = self._concat_prediction_batches(trues)
        print('test shape:', preds.shape, trues.shape)
        return preds, trues

    def _metric_dict(self, preds, trues):
        insample = self._rmsse_insample()
        mae, mse, rmse, mape, mspe, rmsse = metric(preds, trues, insample=insample)
        return {
            'mae': float(mae),
            'mse': float(mse),
            'rmse': float(rmse),
            'mape': float(mape),
            'mspe': float(mspe),
            'rmsse': float(rmsse),
        }

    def evaluate(self, setting=None, load_checkpoint=False, save_artifacts=False,
                 save_visuals=False, write_result_log=False, write_tensorboard=False,
                 flag='test'):
        test_data, test_loader = self._get_data(flag=flag)
        if load_checkpoint:
            if setting is None:
                raise ValueError('setting is required when load_checkpoint=True')
            print('loading model')
            checkpoint_path = os.path.join(self.args.checkpoints, setting, 'checkpoint.pth')
            self.model.load_state_dict(torch.load(checkpoint_path))

        visual_dir = None
        if save_visuals:
            if setting is None:
                raise ValueError('setting is required when save_visuals=True')
            visual_dir = './test_results/' + setting + '/'
            if not os.path.exists(visual_dir):
                os.makedirs(visual_dir)

        preds, trues = self._collect_predictions(test_data, test_loader, visual_dir=visual_dir)
        metrics = self._metric_dict(preds, trues)

        if write_tensorboard:
            if setting is None:
                raise ValueError('setting is required when write_tensorboard=True')
            writer = self._get_writer(setting)
            if writer is not None:
                writer.add_scalar('test/mse', metrics['mse'], 0)
                writer.add_scalar('test/mae', metrics['mae'], 0)
                writer.add_scalar('test/rmse', metrics['rmse'], 0)
                writer.add_scalar('test/rmsse', metrics['rmsse'], 0)
                writer.add_scalar('test/mape', metrics['mape'], 0)
                writer.add_scalar('test/mspe', metrics['mspe'], 0)
                writer.flush()

        if write_result_log:
            if setting is None:
                raise ValueError('setting is required when write_result_log=True')
            f = open("result_long_term_forecast.txt", 'a')
            f.write(setting + "  \n")
            f.write(
                'mse:{}, mae:{}, rmse:{}, rmsse:{}'.format(
                    metrics['mse'], metrics['mae'], metrics['rmse'], metrics['rmsse']
                )
            )
            f.write('\n')
            f.write('\n')
            f.close()

        if save_artifacts:
            if setting is None:
                raise ValueError('setting is required when save_artifacts=True')
            folder_path = os.path.join(getattr(self.args, 'results_root', './results/'), setting) + '/'
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            np.save(
                folder_path + 'metrics.npy',
                np.array([
                    metrics['mae'], metrics['mse'], metrics['rmse'],
                    metrics['mape'], metrics['mspe'], metrics['rmsse']
                ])
            )
            np.save(folder_path + 'pred.npy', preds)
            np.save(folder_path + 'true.npy', trues)
            origin_dates = None
            if hasattr(test_data, 'forecast_origin_dates'):
                origin_dates = test_data.forecast_origin_dates()
                if len(origin_dates) != len(preds):
                    raise ValueError(
                        f'Origin-date count {len(origin_dates)} does not match predictions {len(preds)}'
                    )
                np.save(folder_path + 'origin_dates.npy', origin_dates)
            with open(folder_path + 'meta.json', 'w') as f:
                json.dump(
                    {
                        'inverse': bool(self.args.inverse),
                        'scale': bool(getattr(test_data, 'scale', False)),
                        'features': self.args.features,
                        'target': self.args.target,
                        'freq': self.args.freq,
                        'metric_names': ['mae', 'mse', 'rmse', 'mape', 'mspe', 'rmsse'],
                        'rmsse_seasonality': 1,
                        'seed': int(getattr(self.args, 'seed', 2023)),
                        'split_dates': getattr(self.args, 'split_dates', None),
                        'origin_dates_file': 'origin_dates.npy' if origin_dates is not None else None,
                        'model': self.args.model,
                        'model_id': self.args.model_id,
                        'prediction_horizon': int(self.args.pred_len),
                        'evaluation_split': flag,
                        'protocol_version': getattr(self.args, 'protocol_version', ''),
                        'protocol_sha256': getattr(self.args, 'protocol_sha256', ''),
                        'dataset_sha256': getattr(self.args, 'data_sha256', ''),
                    },
                    f,
                    indent=2,
                )

        return {
            **metrics,
            'preds': preds,
            'trues': trues,
        }

    def vali(self, vali_data, vali_loader, criterion):
        total_loss = []
        self.model.eval()
        with torch.no_grad():
            for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(vali_loader):
                self._maybe_wait_for_thermal_resume(i)
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_y.float()

                if 'PEMS' in self.args.data or 'Solar' in self.args.data:
                    batch_x_mark = None
                    batch_y_mark = None
                else:
                    batch_x_mark = batch_x_mark.float().to(self.device)
                    batch_y_mark = batch_y_mark.float().to(self.device)

                # decoder input
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
                dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)
                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                        else:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
                else:
                    if self.args.output_attention:
                        outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                    else:
                        outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
                f_dim = -1 if self.args.features == 'MS' else 0
                outputs = outputs[:, -self.args.pred_len:, f_dim:]
                batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)

                pred = outputs.detach().cpu()
                true = batch_y.detach().cpu()

                loss = criterion(pred, true)

                total_loss.append(loss)
        total_loss = np.average(total_loss)
        self.model.train()
        return total_loss

    def train(self, setting):
        train_data, train_loader = self._get_data(flag='train')
        vali_data, vali_loader = self._get_data(flag='val')
        writer = self._get_writer(setting)

        path = os.path.join(self.args.checkpoints, setting)
        if not os.path.exists(path):
            os.makedirs(path)

        time_now = time.time()

        train_steps = len(train_loader)
        early_stopping = EarlyStopping(patience=self.args.patience, verbose=True)

        model_optim = self._select_optimizer()
        criterion = self._select_criterion()

        if self.args.use_amp:
            scaler = torch.cuda.amp.GradScaler()

        for epoch in range(self.args.train_epochs):
            iter_count = 0
            train_loss = []

            self.model.train()
            epoch_time = time.time()
            for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(train_loader):
                self._maybe_wait_for_thermal_resume(i)
                iter_count += 1
                model_optim.zero_grad()
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_y.float().to(self.device)
                if 'PEMS' in self.args.data or 'Solar' in self.args.data:
                    batch_x_mark = None
                    batch_y_mark = None
                else:
                    batch_x_mark = batch_x_mark.float().to(self.device)
                    batch_y_mark = batch_y_mark.float().to(self.device)

                # decoder input
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
                dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)

                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                        else:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)

                        f_dim = -1 if self.args.features == 'MS' else 0
                        outputs = outputs[:, -self.args.pred_len:, f_dim:]
                        batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)
                        loss = criterion(outputs, batch_y)
                        train_loss.append(loss.item())
                else:
                    if self.args.output_attention:
                        outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                    else:
                        outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)

                    f_dim = -1 if self.args.features == 'MS' else 0
                    outputs = outputs[:, -self.args.pred_len:, f_dim:]
                    batch_y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)
                    loss = criterion(outputs, batch_y)
                    train_loss.append(loss.item())

                if writer is not None:
                    global_step = epoch * train_steps + i
                    writer.add_scalar('train/loss_step', loss.item(), global_step)

                if (i + 1) % 100 == 0:
                    iter_count = 0
                    time_now = time.time()

                if self.args.use_amp:
                    scaler.scale(loss).backward()
                    scaler.step(model_optim)
                    scaler.update()
                else:
                    loss.backward()
                    model_optim.step()

            epoch_time_sec = time.time() - epoch_time
            train_loss = np.average(train_loss)
            self._wait_for_thermal_resume()
            vali_loss = self.vali(vali_data, vali_loader, criterion)
            self._wait_for_thermal_resume()
            current_lr = model_optim.param_groups[0]['lr']
            if writer is not None:
                writer.add_scalar('train/loss_epoch', train_loss, epoch + 1)
                writer.add_scalar('val/loss', vali_loss, epoch + 1)
                writer.add_scalar('train/learning_rate', current_lr, epoch + 1)
                writer.add_scalar('train/epoch_time_sec', epoch_time_sec, epoch + 1)
            early_stopping(vali_loss, self.model, path)
            if early_stopping.early_stop:
                print("Early stopping")
                break

            adjust_learning_rate(model_optim, epoch + 1, self.args)

            # get_cka(self.args, setting, self.model, train_loader, self.device, epoch)

        best_model_path = path + '/' + 'checkpoint.pth'
        self.model.load_state_dict(torch.load(best_model_path))

        return self.model

    def test(self, setting, test=0):
        self.evaluate(
            setting=setting,
            load_checkpoint=bool(test),
            save_artifacts=True,
            save_visuals=True,
            write_result_log=True,
            write_tensorboard=True,
        )
        return
    def get_input(self, setting):
        test_data, test_loader = self._get_data(flag='test')
        inputs = []
        for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(test_loader):
            input = batch_x.detach().cpu().numpy()
            inputs.append((input))
        folder_path = './results/' + setting + '/'
        np.save(folder_path + 'input.npy', inputs)

    def predict(self, setting, load=False):
        pred_data, pred_loader = self._get_data(flag='pred')

        if load:
            path = os.path.join(self.args.checkpoints, setting)
            best_model_path = path + '/' + 'checkpoint.pth'
            self.model.load_state_dict(torch.load(best_model_path))

        preds = []

        self.model.eval()
        with torch.no_grad():
            for i, (batch_x, batch_y, batch_x_mark, batch_y_mark) in enumerate(pred_loader):
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_y.float()
                batch_x_mark = batch_x_mark.float().to(self.device)
                batch_y_mark = batch_y_mark.float().to(self.device)

                # decoder input
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
                dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)
                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                        else:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
                else:
                    if self.args.output_attention:
                        outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                    else:
                        outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
                outputs = outputs.detach().cpu().numpy()
                if pred_data.scale and self.args.inverse:
                    outputs = self._inverse_transform_batch(pred_data, outputs)
                preds.append(outputs)

        preds = self._concat_prediction_batches(preds)

        # result save
        folder_path = './results/' + setting + '/'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        np.save(folder_path + 'real_prediction.npy', preds)

        return
