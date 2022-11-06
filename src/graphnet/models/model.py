"""Base class(es) for building models."""

from abc import ABC, abstractmethod
import dill
import os.path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

try:
    from typing import final
except ImportError:  # Python version < 3.8

    # Identity decorator
    def final(f):  # type: ignore  # noqa: D103
        return f


from pytorch_lightning import LightningModule
import torch
from torch import Tensor
from torch_geometric.data import Data


from graphnet.utilities.logging import LoggerMixin

if TYPE_CHECKING:
    # Avoid cyclic dependency
    from graphnet.models.config import ModelConfig


class Model(LightningModule, LoggerMixin, ABC):
    """Base class for all models in graphnet."""

    @abstractmethod
    def forward(self, x: Union[Tensor, Data]) -> Union[Tensor, Data]:
        """Forward pass."""

    @final
    @property
    def config(self) -> "ModelConfig":
        """Return configuration to re-create the model."""
        try:
            return self._config
        except AttributeError:
            self.error(
                "ModelConfig was not set. "
                "Did you wrap the class constructor with `save_config`?"
            )
            raise

    def save(self, path: str) -> None:
        """Save entire model to `path`."""
        if not path.endswith(".pth"):
            self.info(
                "It is recommended to use the .pth suffix for model files."
            )
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        torch.save(self.cpu(), path, pickle_module=dill)
        self.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str) -> "Model":
        """Load entire model from `path`."""
        return torch.load(path, pickle_module=dill)

    def save_state_dict(self, path: str) -> None:
        """Save model `state_dict` to `path`."""
        if not path.endswith(".pth"):
            self.info(
                "It is recommended to use the .pth suffix for state_dict files."
            )
        torch.save(self.cpu().state_dict(), path)
        self.info(f"Model state_dict saved to {path}")

    def load_state_dict(
        self, path: Union[str, Dict]
    ) -> "Model":  # pylint: disable=arguments-differ
        """Load model `state_dict` from `path`."""
        if isinstance(path, str):
            state_dict = torch.load(path)
        else:
            state_dict = path
        return super().load_state_dict(state_dict)

    @final
    def save_config(self, path: str) -> None:
        """Save ModelConfig to `path` as YAML file."""
        self.config.dump(path)

    @classmethod
    def from_config(
        cls,
        source: Union["ModelConfig", str],
        trust: bool = False,
        load_modules: Optional[List[str]] = None,
    ) -> "Model":
        """Construct `Model` instance from `source` configuration.

        Arguments:
            trust: Whether to trust the ModelConfig file enough to `eval(...)`
                any lambda function expressions contained.

        Raises:
            ValueError: If the ModelConfig contains lambda functions but
                `trust = False`.
        """
        from graphnet.models.config import ModelConfig

        if isinstance(source, str):
            source = ModelConfig.load(source)

        assert isinstance(source, ModelConfig)
        return source.construct_model(trust=trust, load_modules=load_modules)
