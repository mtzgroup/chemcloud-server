"""A simple script to exercise the web app and celery to compute a result."""
from time import sleep

import requests
from qcelemental.models import AtomicInput, AtomicResult, Molecule
from qcelemental.models.common_models import Model

molecule = Molecule.from_data("pubchem:water")
model = Model(method="B3LYP", basis="6-31g")
driver = "energy"
atomic_input = AtomicInput(molecule=molecule, model=model, driver=driver)

HOST = "http://localhost:8000"
# HOST = "https://tcc.dev.mtzlab.com"

if __name__ == "__main__":
    print("posting request...")
    r1 = requests.post(
        f"{HOST}/compute",
        data=atomic_input.json(),
        params={"engine": "psi4"},
    )
    print(r1.status_code)
    print(r1.json())
    while r2 := requests.get(
        f"{HOST}/result",
        params={"task_id": r1.json()},
    ):
        status = r2.json()[0]
        print(f"Status: {status}")
        if status == "SUCCESS":
            break
        print("Waiting for result...")
        sleep(1)
    result = AtomicResult(**r2.json()[1])
    print(result)
    print(result.return_result)
