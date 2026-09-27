"""Static protocol test double; it is not a SysML parser."""

import json
from pathlib import Path
import sys


def source_range(line, col, token):
    return {"line": line, "col": col, "end_col": col + len(token)}


def symbol(name, kind, line, col, container=None, signature=None):
    return {
        "name": name,
        "kind": kind,
        "range": source_range(line, col, name),
        "container": container,
        "signature": signature,
    }


def reference(name, line, col, relation, source=None):
    return {
        "name": name,
        "range": source_range(line, col, name),
        "relation": relation,
        "source": source,
    }


def file_result(path, symbols=None, references=None, diagnostics=None, imports=None):
    return {
        "path": path,
        "symbols": symbols or [],
        "references": references or [],
        "diagnostics": diagnostics or [],
        "imports": imports or [],
    }


def result_for(source_file):
    path = source_file["path"]
    basename = Path(path).name
    if basename == "vehicle.sysml":
        return file_result(
            path,
            [
                symbol("Engine", "part_def", 2, 11, "VehiclePkg", "part def Engine {"),
                symbol("Vehicle", "part_def", 6, 11, "VehiclePkg", "part def Vehicle {"),
                symbol("engine", "part_usage", 7, 9, "Vehicle", "part engine: Engine;"),
                symbol("wheel", "part_usage", 8, 9, "Vehicle", "part wheel: Wheel;"),
                symbol("FuelPort", "port_def", 11, 12, "VehiclePkg", "port def FuelPort;"),
                symbol("Wheel", "part_def", 12, 11, "VehiclePkg", "part def Wheel;"),
            ],
            [
                reference("FuelPort", 3, 17, "typed_by", "fuelIn"),
                reference("Engine", 7, 17, "typed_by", "engine"),
                reference("Wheel", 8, 16, "typed_by", "wheel"),
            ],
        )
    if basename == "links.sysml":
        return file_result(
            path,
            [
                symbol("LinkPkg", "package", 1, 8, signature="package LinkPkg {"),
                symbol("Fleet", "part_def", 4, 13, "LinkPkg", "part def Fleet {"),
                symbol("lead", "part_usage", 5, 9, "Fleet", "part lead: Vehicle;"),
            ],
            [
                reference("Vehicle", 2, 22, "import", "LinkPkg"),
                reference("Vehicle", 5, 17, "typed_by", "lead"),
                reference("Vehicle", 6, 13, "allocate", "Fleet"),
                reference("Vehicle", 7, 10, "trace", "Fleet"),
            ],
            imports=["VehiclePkg::Vehicle"],
        )
    if basename == "behavior.sysml":
        return file_result(
            path,
            [
                symbol("BehaviorPkg", "package", 1, 8, signature="package BehaviorPkg {"),
                symbol("Controller", "part_def", 2, 13, "BehaviorPkg", "part def Controller {"),
                symbol("Idle", "state_def", 3, 14, "Controller", "state def Idle;"),
                symbol("Active", "state_def", 4, 14, "Controller", "state def Active;"),
                symbol("Start", "action_def", 8, 13, "BehaviorPkg", "action def Start;"),
            ],
            [
                reference("Idle", 5, 4, "transition", "Controller"),
                reference("Active", 5, 12, "transition", "Controller"),
            ],
        )
    if basename == "requirements.sysml":
        return file_result(
            path,
            [
                symbol("ReqPkg", "package", 1, 8, signature="package ReqPkg {"),
                symbol("R1", "requirement_def", 2, 18, "ReqPkg", "requirement def R1;"),
                symbol("req1", "requirement_usage", 3, 14, "ReqPkg", "requirement req1: R1;"),
                symbol("VerificationRig", "part_def", 5, 11, "ReqPkg", "part def VerificationRig {"),
            ],
            [
                reference("R1", 3, 21, "typed_by", "req1"),
                reference("R1", 6, 12, "satisfy", "VerificationRig"),
                reference("R1", 7, 11, "verify", "VerificationRig"),
            ],
        )
    if basename == "bad.sysml":
        return file_result(
            path,
            diagnostics=[
                {
                    "range": source_range(2, 0, "part def Broken {"),
                    "severity": "error",
                    "message": "Unclosed block",
                    "source": "SysML v2 Pilot Implementation",
                }
            ],
        )
    return file_result(path)


request = json.loads(sys.stdin.read())
response = {
    "parser": {
        "name": "SysML v2 Pilot Implementation (test double)",
        "version": "0.63.0",
        "standards": ["SysML 2.0", "KerML 1.0"],
    },
    "files": [result_for(source_file) for source_file in request["files"]],
}
print(json.dumps(response))
