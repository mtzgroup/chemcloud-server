import requests
from qcelemental.models import AtomicInput, Molecule
from qcelemental.models.common_models import Model

molecule = Molecule.from_data("pubchem:water")
model = Model(method="B3LYP", basis="6-31g")
driver = "energy"
atomic_input = AtomicInput(molecule=molecule, model=model, driver=driver)

if __name__ == "__main__":
    r = requests.post(
        "http://localhost:8000/compute",
        data=atomic_input.json(),
    )
    print(r.status_code)
    print(r.json())
