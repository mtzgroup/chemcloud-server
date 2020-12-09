"""A simple script to exercise the web app and celery to compute a result."""
from getpass import getpass
from time import sleep

import httpx
from qcelemental.models import AtomicInput, AtomicResult, Molecule
from qcelemental.models.common_models import Model

HOST = "http://localhost:8000"
# HOST = "https://tcc.dev.mtzlab.com"
API_PREFIX = "/api/v1"
MOLECULE = "water"

if __name__ == "__main__":
    # Get auth token
    username = input("Please enter your username: ")
    password = getpass()
    print("Getting auth token...")
    data = {"grant_type": "password", "username": username, "password": password}
    r0 = httpx.post(
        f"{HOST}{API_PREFIX}/oauth/token",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data=data,
    )
    jwt = r0.json()["access_token"]

    # Generate Inputs
    print(f"Generating input for {MOLECULE}...")
    molecule = Molecule.from_data(f"pubchem:{MOLECULE}")
    model = Model(method="B3LYP", basis="6-31g")
    driver = "energy"
    atomic_input = AtomicInput(molecule=molecule, model=model, driver=driver)

    # POST compute job
    print("posting request...")
    r1 = httpx.post(
        f"{HOST}{API_PREFIX}/compute",
        headers={"Authorization": f"Bearer {jwt}"},
        data=atomic_input.json(),
        params={"engine": "psi4"},
    )
    task_id = r1.json()

    # Check job results
    def _get_result(task_id, token):
        result = httpx.get(
            f"{HOST}{API_PREFIX}/compute/result/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response = result.json()
        return response["status"], response["atomic_result"]

    status, atomic_result = _get_result(task_id, jwt)
    while status in {"PENDING", "STARTED"}:
        sleep(1)
        status, atomic_result = _get_result(task_id, jwt)
        print(f"Status: {status}")
        print("Waiting for result...")

    # Assure we can recreate models from results
    result = AtomicResult(**atomic_result)
    print(result)
    print(result.return_result)
