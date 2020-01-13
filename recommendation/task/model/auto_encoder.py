from typing import List

import torch.nn as nn

import luigi

from recommendation.model.auto_encoder import UnconstrainedAutoEncoder, VariationalAutoEncoder, AttentiveVariationalAutoEncoder, HybridVAE
from recommendation.task.meta_config import RecommenderType
from recommendation.task.model.base import BaseTorchModelTraining, TORCH_ACTIVATION_FUNCTIONS, TORCH_WEIGHT_INIT, \
    TORCH_DROPOUT_MODULES
from recommendation.torch import MaskedZeroesLoss, SparseTensorLoss, MaskedZeroesWithNegativeSamplingLoss


class UnconstrainedAutoEncoderTraining(BaseTorchModelTraining):
    metrics = luigi.ListParameter(default=["loss", "precision", "recall"])

    encoder_layers: List[int] = luigi.ListParameter(default=[256, 128, 128, 64])
    decoder_layers: List[int] = luigi.ListParameter(default=[128, 128, 256])
    dropout_prob: float = luigi.FloatParameter(default=0)
    activation_function: str = luigi.ChoiceParameter(choices=TORCH_ACTIVATION_FUNCTIONS.keys(), default="selu")
    weight_init: str = luigi.ChoiceParameter(choices=TORCH_WEIGHT_INIT.keys(), default="lecun_normal")
    dropout_module: str = luigi.ChoiceParameter(choices=TORCH_DROPOUT_MODULES.keys(), default="alpha")
    loss_wrapper: str = luigi.ChoiceParameter(choices=["masked_zeroes", "masked_zeroes_with_negative_sampling", "none"],
                                              default="masked_zeroes")
    binary: bool = luigi.BoolParameter(default=False)

    def _get_loss_function(self):
        loss_wrapper = dict(masked_zeroes=MaskedZeroesLoss,
                            masked_zeroes_with_negative_sampling=MaskedZeroesWithNegativeSamplingLoss,
                            none=SparseTensorLoss)[self.loss_wrapper]
        return loss_wrapper(super()._get_loss_function())

    def create_module(self) -> nn.Module:
        dim = self.n_items \
            if self.project_config.recommender_type == RecommenderType.USER_BASED_COLLABORATIVE_FILTERING \
            else self.n_users
        return UnconstrainedAutoEncoder(dim, self.encoder_layers, self.decoder_layers, binary=self.binary,
                                        dropout_prob=self.dropout_prob,
                                        activation_function=TORCH_ACTIVATION_FUNCTIONS[self.activation_function],
                                        weight_init=TORCH_WEIGHT_INIT[self.weight_init],
                                        dropout_module=TORCH_DROPOUT_MODULES[self.dropout_module])


class VariationalAutoEncoderTraining(BaseTorchModelTraining):
    encoder_layers: List[int] = luigi.ListParameter(default=[256, 128, 128])
    decoder_layers: List[int] = luigi.ListParameter(default=[128, 128, 256])
    dropout_prob: float = luigi.FloatParameter(default=0)
    activation_function: str = luigi.ChoiceParameter(choices=TORCH_ACTIVATION_FUNCTIONS.keys(), default="selu")
    weight_init: str = luigi.ChoiceParameter(choices=TORCH_WEIGHT_INIT.keys(), default="lecun_normal")
    loss_function: str = luigi.ChoiceParameter(choices=["vae_loss", "focal_vae_loss"], default="vae_loss")
    dropout_module: str = luigi.ChoiceParameter(choices=TORCH_DROPOUT_MODULES.keys(), default="alpha")
    binary: bool = luigi.BoolParameter(default=False)
    
    def create_module(self) -> nn.Module:
        dim = self.n_items \
            if self.project_config.recommender_type == RecommenderType.USER_BASED_COLLABORATIVE_FILTERING \
            else self.n_users
        return VariationalAutoEncoder(dim, self.encoder_layers, self.decoder_layers, binary=self.binary, dropout_prob=self.dropout_prob,
                                      activation_function=TORCH_ACTIVATION_FUNCTIONS[self.activation_function],
                                      weight_init=TORCH_WEIGHT_INIT[self.weight_init],
                                      dropout_module=TORCH_DROPOUT_MODULES[self.dropout_module])

class AttentiveVariationalAutoEncoderTraining(BaseTorchModelTraining):
    encoder_layers: List[int] = luigi.ListParameter(default=[256, 128, 128])
    attention_layers: List[int] = luigi.ListParameter(default=[256,  128, 128])
    decoder_layers: List[int] = luigi.ListParameter(default=[128, 128, 256])
    dropout_prob: float = luigi.FloatParameter(default=0)
    activation_function: str = luigi.ChoiceParameter(choices=TORCH_ACTIVATION_FUNCTIONS.keys(), default="selu")
    weight_init: str = luigi.ChoiceParameter(choices=TORCH_WEIGHT_INIT.keys(), default="lecun_normal")
    loss_function: str = luigi.ChoiceParameter(choices=["attentive_vae_loss"], default="attentive_vae_loss")
    dropout_module: str = luigi.ChoiceParameter(choices=TORCH_DROPOUT_MODULES.keys(), default="alpha")
    binary: bool = luigi.BoolParameter(default=False)
    
    def create_module(self) -> nn.Module:
        dim = self.n_items \
            if self.project_config.recommender_type == RecommenderType.USER_BASED_COLLABORATIVE_FILTERING \
            else self.n_users
        return AttentiveVariationalAutoEncoder(dim, self.encoder_layers, self.attention_layers, self.decoder_layers, binary=self.binary, dropout_prob=self.dropout_prob,
                                      activation_function=TORCH_ACTIVATION_FUNCTIONS[self.activation_function],
                                      weight_init=TORCH_WEIGHT_INIT[self.weight_init],
                                      dropout_module=TORCH_DROPOUT_MODULES[self.dropout_module])

class HybridVAETraining(BaseTorchModelTraining):
    encoder_layers: List[int] = luigi.ListParameter(default=[256, 128, 128])
    decoder_layers: List[int] = luigi.ListParameter(default=[128, 128, 256])
    dropout_prob: float = luigi.FloatParameter(default=0)
    activation_function: str = luigi.ChoiceParameter(choices=TORCH_ACTIVATION_FUNCTIONS.keys(), default="selu")
    weight_init: str = luigi.ChoiceParameter(choices=TORCH_WEIGHT_INIT.keys(), default="lecun_normal")
    loss_function: str = luigi.ChoiceParameter(choices=["vae_loss", "focal_vae_loss"], default="vae_loss")
    dropout_module: str = luigi.ChoiceParameter(choices=TORCH_DROPOUT_MODULES.keys(), default="alpha")
    binary: bool = luigi.BoolParameter(default=False)
    n_factors: float = luigi.IntParameter(default=128)
    
    def create_module(self) -> nn.Module:
        if self.project_config.recommender_type == RecommenderType.USER_BASED_COLLABORATIVE_FILTERING:
            dim = self.n_items
            embedding_size = self.n_users
        else:
            dim = self.n_users
            embedding_size = self.n_items
        return HybridVAE(dim, self.encoder_layers, self.decoder_layers, embedding_size, self.n_factors, binary=self.binary, dropout_prob=self.dropout_prob,
                                      activation_function=TORCH_ACTIVATION_FUNCTIONS[self.activation_function],
                                      weight_init=TORCH_WEIGHT_INIT[self.weight_init],
                                      dropout_module=TORCH_DROPOUT_MODULES[self.dropout_module])