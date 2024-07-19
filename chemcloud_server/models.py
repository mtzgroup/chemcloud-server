from enum import Enum
from typing import Optional, TypeAlias

from pydantic import AnyHttpUrl, BaseModel, Field
from qcio import (
    DualProgramInput,
    FileInput,
    Files,
    OptimizationResults,
    ProgramInput,
    ProgramOutput,
    SinglePointResults,
)

# Convenience types
ProgramInputs: TypeAlias = FileInput | ProgramInput | DualProgramInput
ProgramInputsOrList: TypeAlias = ProgramInputs | list[ProgramInputs]
# Appears I must explicitly list all possible outputs here otherwise calling .model_dump
# on a ProgramOutputWrapper object will fail with when trying to return a response from
# /output/ with the following error:
# *** pydantic_core._pydantic_core.PydanticSerializationError: Error calling function `<lambda>`: TypeError: 'MockValSet' object cannot be converted to 'SchemaSerializer'  # noqa: E501
# There may be a more clever dynamic way to do this but this is OK for now.
ProgramOutputs: TypeAlias = (
    ProgramOutput[FileInput, Files]
    | ProgramOutput[ProgramInput, Files]
    | ProgramOutput[ProgramInput, SinglePointResults]
    | ProgramOutput[ProgramInput, OptimizationResults]
    | ProgramOutput[DualProgramInput, Files]
    | ProgramOutput[DualProgramInput, SinglePointResults]
    | ProgramOutput[DualProgramInput, OptimizationResults]
)
ProgramOutputsOrList: TypeAlias = ProgramOutputs | list[ProgramOutputs]


class SupportedPrograms(str, Enum):
    """
    Compute programs currently supported by this instance of ChemCloud.

    NOTE: To add more just make sure your BigChem instance has the program installed and
        then add the program name here. This SupportedPrograms filter exists so that
        client applications can query the server and know what programs are available.
    """

    PSI4 = "psi4"
    TERACHEM = "terachem"
    RDKIT = "rdkit"
    XTB = "xtb"
    GEOMETRIC = "geometric"
    # BigChem distributed algorithms
    BIGCHEM = "bigchem"


class TaskStatus(str, Enum):
    """Tasks status for a submitted compute job"""

    # States from https://github.com/celery/celery/blob/master/celery/states.py

    #: Task state is unknown (assumed pending since you know the id).
    PENDING = "PENDING"
    #: Task was received by a worker (only used in events).
    RECEIVED = "RECEIVED"
    #: Task was started by a worker (:setting:`task_track_started`).
    STARTED = "STARTED"
    #: Task succeeded
    SUCCESS = "SUCCESS"
    #: Task failed
    FAILURE = "FAILURE"
    #: Task was revoked.
    REVOKED = "REVOKED"
    #: Task was rejected (only used in events).
    REJECTED = "REJECTED"
    #: Task is waiting for retry.
    RETRY = "RETRY"
    IGNORED = "IGNORED"


class ProgramOutputWrapper(BaseModel):
    """
    Status and ProgramOutput(s) of a compute task. Main object returned by
    /compute/output/{task_id} in response to a query for a task's status and output.

    Args:
        status: The status of the task as reported by celery.
        program_output: The ProgramOutput object for the task. If the task is a group,
            this will be a list of ProgramOutputs. If the task is a single task, this
            will be a single ProgramOutput.
    """

    status: TaskStatus
    program_output: Optional[ProgramOutputsOrList] = None


class OAuth2Base(BaseModel):
    client_id: str
    client_secret: str


class OAuth2LoginBase(OAuth2Base):
    audience: str = ""
    scope: str = ""


class OAuth2PasswordFlow(OAuth2LoginBase):
    grant_type: str = Field("password", pattern="password")
    username: str
    password: str


class OAuth2AuthorizationCodeFlow(OAuth2LoginBase):
    grant_type: str = Field("authorization_code", pattern="authorization_code")
    code: str
    redirect_uri: AnyHttpUrl


class OAuth2RefreshFlow(OAuth2Base):
    grant_type: str = Field("refresh_token", pattern="refresh_token")
    refresh_token: str
