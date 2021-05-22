"""Quick example of how to perform a geomeTRIC optimization using force fields"""
import qcengine as qcng
from qcelemental.models.procedures import (
    OptimizationInput,
    OptimizationProtocols,
    QCInputSpecification,
    TrajectoryProtocolEnum,
)

from terachem_cloud.workers.tasks import compute_procedure as cp_task

water = qcng.get_molecule("water")
op = OptimizationProtocols(trajectory=TrajectoryProtocolEnum.all)
input_spec = QCInputSpecification(
    driver="gradient",
    model={"method": "UFF"},
)

inp = OptimizationInput(
    protocols=op,
    initial_molecule=water,
    input_specification=input_spec,
    keywords={"program": "rdkit"},
)

r = cp_task.delay(inp, "geometric")
r.status
o = r.get()
