"""An example of how to apply GraphNetI3Modules in Icetray."""
from typing import TYPE_CHECKING, List, Dict, Sequence
from glob import glob
from os.path import join


from graphnet.data.constants import FEATURES
from graphnet.models import StandardModel
from graphnet.models.detector.icecube import IceCubeUpgrade
from graphnet.models.gnn import DynEdge
from graphnet.models.graph_builders import KNNGraphBuilder
from graphnet.models.task.reconstruction import EnergyReconstruction
from graphnet.utilities.logging import get_logger
from graphnet.training.loss_functions import LogCoshLoss
from graphnet.utilities.imports import has_icecube_package, has_torch_package
from graphnet.deployment.i3modules import (
    I3InferenceModule,
    GraphNeTI3Module,
)
from graphnet.data.extractors.i3featureextractor import (
    I3FeatureExtractorIceCubeUpgrade,
)
from graphnet.constants import (
    TEST_DATA_DIR,
    EXAMPLE_OUTPUT_DIR,
)


if has_icecube_package() or TYPE_CHECKING:
    from icecube import icetray, dataio  # pyright: reportMissingImports=false
    from I3Tray import I3Tray

if has_torch_package or TYPE_CHECKING:
    import torch
    from torch.optim.adam import Adam

logger = get_logger()


def apply_to_files(
    i3_files: List[str],
    gcd_file: str,
    output_folder: str,
    modules: Sequence[GraphNeTI3Module],
) -> None:
    """Will start an IceTray read/write chain with graphnet modules.

    The new i3 files will appear as copies of the original i3 files but with
    reconstructions added. Original i3 files are left untouched.
    """
    for i3_file in i3_files:
        tray = I3Tray()
        tray.context["I3FileStager"] = dataio.get_stagers()
        tray.AddModule(
            "I3Reader",
            "reader",
            FilenameList=[gcd_file, i3_file],
        )
        for i3_module in modules:
            tray.AddModule(i3_module)
        tray.Add(
            "I3Writer",
            Streams=[
                icetray.I3Frame.DAQ,
                icetray.I3Frame.Physics,
                icetray.I3Frame.TrayInfo,
                icetray.I3Frame.Simulation,
            ],
            filename=output_folder + "/" + i3_file.split("/")[-1],
        )
        tray.Execute()
        tray.Finish()
    return


def main() -> None:
    """GraphNeTI3Module in native IceTray Example."""
    # Configurations
    pulsemap = "SplitInIcePulses"
    # Constants
    features = FEATURES.UPGRADE
    input_folders = [f"{TEST_DATA_DIR}/i3/upgrade_genie_step4_140028_000998"]
    mock_model_path = f"{TEST_DATA_DIR}/models/mock_energy_model.pth"
    output_folder = f"{EXAMPLE_OUTPUT_DIR}/i3_deployment/upgrade"
    gcd_file = f"{TEST_DATA_DIR}/i3/upgrade_genie_step4_140028_000998/GeoCalibDetectorStatus_ICUpgrade.v58.mixed.V0.i3.bz2"
    features = FEATURES.UPGRADE
    input_files = []
    for folder in input_folders:
        input_files.extend(glob(join(folder, "*.i3.gz")))

    # Configure Deployment module
    deployment_module = I3InferenceModule(
        pulsemap=pulsemap,
        features=features,
        pulsemap_extractor=I3FeatureExtractorIceCubeUpgrade(pulsemap=pulsemap),
        model=mock_model_path,
        gcd_file=gcd_file,
        prediction_columns=["energy"],
        model_name="graphnet_deployment_example",
    )

    # Apply module to files in IceTray
    apply_to_files(
        i3_files=input_files,
        gcd_file=gcd_file,
        output_folder=output_folder,
        modules=[deployment_module],
    )


if __name__ == "__main__":
    main()
