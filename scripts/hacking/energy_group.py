"""Quick example of how to perform a group of energy calculations"""

from celery import group
from qcelemental.models import AtomicInput, Molecule

from terachem_cloud.workers.tasks import compute

water = Molecule.from_data("pubchem:water")
atomic_input = AtomicInput(
    molecule=water,
    model={"method": "B3LYP", "basis": "6-31g"},
    driver="energy",
    # keywords={"bad": "fake"},
)

fr = group(
    [compute.s(atomic_input, "terachem_pbs"), compute.s(atomic_input, "terachem_pbs")]
)()

print(fr.successful())
print(fr.ready())
print(fr.waiting())
print(fr.completed_count())

# gr = GroupResult(id=fr.id, results=fr.results)
# ar = compute.delay(atomic_input, "psi4")
