from __future__ import annotations

import pandas as pd

from ..config import CaseConfig, Formulation
from .common import ModelArtifacts, build_common_model


def build_model(
    case_config: CaseConfig,
    data: pd.DataFrame,
    *,
    relax_binaries: bool = False,
) -> ModelArtifacts:
    return build_common_model(
        case_config,
        data,
        Formulation.BASIC,
        relax_binaries=relax_binaries,
    )
