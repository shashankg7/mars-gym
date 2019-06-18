from typing import List

import torch.nn as nn

import luigi

from recommendation.model.auto_encoder import UnconstrainedAutoEncoder
from recommendation.task.model.base import BaseTorchModelTraining, TORCH_ACTIVATION_FUNCTIONS, TORCH_WEIGHT_INIT, \
    TORCH_DROPOUT_MODULES
from recommendation.torch import MaskedZeroesLoss


class UnconstrainedAutoEncoderTraining(BaseTorchModelTraining):
    metrics = luigi.ListParameter(default=["loss", "masked_zeroes_mse"])

    encoder_layers: List[int] = luigi.ListParameter(default=[256, 128, 128, 64])
    decoder_layers: List[int] = luigi.ListParameter(default=[128, 128, 256])
    dropout_prob: float = luigi.FloatParameter(default=None)
    activation_function: str = luigi.ChoiceParameter(choices=TORCH_ACTIVATION_FUNCTIONS.keys(), default="selu")
    weight_init: str = luigi.ChoiceParameter(choices=TORCH_WEIGHT_INIT.keys(), default="lecun_normal")
    dropout_module: str = luigi.ChoiceParameter(choices=TORCH_DROPOUT_MODULES.keys(), default="alpha")

    def _get_loss_function(self):
        return MaskedZeroesLoss(super()._get_loss_function())

    def create_module(self) -> nn.Module:
        return UnconstrainedAutoEncoder(self.project_config.input_columns[0].length, self.encoder_layers, self.decoder_layers, dropout_prob=self.dropout_prob,
                                        activation_function=TORCH_ACTIVATION_FUNCTIONS[
                                                     self.activation_function],
                                        weight_init=TORCH_WEIGHT_INIT[self.weight_init],
                                        dropout_module=TORCH_DROPOUT_MODULES[self.dropout_module])
