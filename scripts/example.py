"""A simple script to exercise the web app and celery to compute a result."""
import sys
from getpass import getpass
from pathlib import Path
from time import sleep

import httpx
from qcio import Molecule, ProgramFailure, ProgramInput, SinglePointOutput

HOSTS = {
    "local": "http://localhost:8000",
    "dev": "https://chemcloud.dev.mtzlab.com",
    "prod": "https://chemcloud.mtzlab.com",
}

API_PREFIX = "/api/v2"
current_dir = Path(__file__).resolve().parent
MOLECULE = current_dir / "h2o.xyz"


if __name__ == "__main__":
    # Set environment
    try:
        env = sys.argv[1]
    except IndexError:
        env = ""
    if env not in {"local", "dev", "prod"}:
        print("You must call this script with [local | dev | prod] as an argument.")
        sys.exit(1)

    HOST = HOSTS[env]
    # Get auth token
    username = input("Please enter your username: ")
    password = getpass()
    print("Getting auth token...")
    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "scope": "compute:public",
    }
    r0 = httpx.post(
        f"{HOST}{API_PREFIX}/oauth/token",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data=data,
    )
    try:
        r0.raise_for_status()
    except httpx.HTTPStatusError:
        print("Login information incorrect.")
        sys.exit(1)
    jwt = r0.json()["access_token"]

    # Generate Inputs
    print(f"Opening molecule structure: {MOLECULE}...")
    molecule = Molecule.open(MOLECULE)
    prog_inp = ProgramInput(
        molecule=molecule,
        model={"method": "b3lyp", "basis": "6-31g"},
        calctype="energy",
    )

    # POST compute job
    print("Sending job...")
    r1 = httpx.post(
        f"{HOST}{API_PREFIX}/compute",
        headers={"Authorization": f"Bearer {jwt}"},
        data=prog_inp.model_dump_json(),
        params={"program": "terachem"},
    )
    r1.raise_for_status()
    task_id = r1.json()
    print(f"Job sent! Task ID: {task_id}")

    # Check job results
    def _get_result(task_id, token):
        result = httpx.get(
            f"{HOST}{API_PREFIX}/compute/output/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        print(result)
        response = result.json()
        return response["state"], response["result"]

    status, output = _get_result(task_id, jwt)
    while status in {"PENDING", "STARTED"}:
        sleep(1)
        status, output_dict = _get_result(task_id, jwt)
        print(f"State: {status}")
        print("Waiting for result...")

    # Assure we can recreate models from results
    if output_dict["success"] is True:
        output = SinglePointOutput(**output_dict)
    else:
        output = ProgramFailure(**output_dict)

    print(output)
    print(getattr(output, "return_result", "Operation Failed!"))
