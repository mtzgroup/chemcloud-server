from qcelemental.models import AtomicResult, OptimizationResult
from tcpb.config import settings as tcpb_settings

from chemcloud_server.routes.helpers import _b64_to_bytes, _bytes_to_b64


def test_b64_to_bytes_atomic_input(atomic_input):
    b64_string = "MTIz"

    tcfe_config = {"c0_b64": b64_string}
    # Test on OptimizationInput
    atomic_input.extras[tcpb_settings.tcfe_keywords] = tcfe_config
    _b64_to_bytes(atomic_input)
    assert isinstance(tcfe_config["c0"], bytes)
    assert tcfe_config["c0"] == b"123"
    assert tcfe_config.get("c0_b64") is None


def test_b64_to_bytes_opt_input(opt_input):
    b64_string = "MTIz"

    tcfe_config = {"c0_b64": b64_string}
    # Test on OptimizationInput
    opt_input.input_specification.extras[tcpb_settings.tcfe_keywords] = tcfe_config
    _b64_to_bytes(opt_input.input_specification)
    assert isinstance(tcfe_config["c0"], bytes)
    assert tcfe_config["c0"] == b"123"
    assert tcfe_config.get("c0_b64") is None


def test_bytes_to_b64_atomic_result(atomic_result):
    key = "c0"

    # Add a binary native file
    ar_dict = atomic_result.dict()
    ar_dict["protocols"] = {"native_files": "all"}
    ar_dict["native_files"] = {key: b"123"}

    # Process result
    mod_ar = AtomicResult(**ar_dict)
    _bytes_to_b64(mod_ar)

    # Assert has been encoded to b64 string
    assert mod_ar.native_files.get(key) is None
    assert isinstance(mod_ar.native_files.get(f"{key}_b64"), str)
    assert mod_ar.native_files.get(f"{key}_b64") == "MTIz"


def test_bytes_to_b64_optimization_result(opt_result):
    key = "c0"

    # Add a binary native file
    opt_dict = opt_result.dict()
    opt_dict["trajectory"][0]["protocols"] = {"native_files": "all"}
    opt_dict["trajectory"][0]["native_files"] = {key: b"123"}

    # Process result
    mod_opt_res = OptimizationResult(**opt_dict)
    _bytes_to_b64(mod_opt_res)

    for ar in mod_opt_res.trajectory:
        # Assert has been encoded to b64 string
        assert ar.native_files.get(key) is None
        assert isinstance(ar.native_files.get(f"{key}_b64"), str)
        assert ar.native_files.get(f"{key}_b64") == "MTIz"
