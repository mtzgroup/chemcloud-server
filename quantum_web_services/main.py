import qcengine as qcng
from fastapi import FastAPI
from qcelemental.models.results import AtomicInput, AtomicResult

app = FastAPI()


@app.get("/")
def hello_world():
    return {"Hello": "World"}


@app.post("/compute")
def compute(atomic_input: AtomicInput) -> AtomicResult:
    result = qcng.compute(atomic_input, "psi4")
    return result
