"""BAIT bridge conservation heuristic for Slither."""
from typing import List
from slither.detectors.abstract_detector import AbstractDetector, DetectorClassification
from slither.core.cfg.node import NodeType


class BaitConservationCheck(AbstractDetector):
    ARGUMENT = "bait-conservation"
    HELP = "totalMinted write without totalLockedOnL1 guard in same function"
    IMPACT = DetectorClassification.HIGH
    CONFIDENCE = DetectorClassification.MEDIUM

    WIKI = "https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-"
    WIKI_TITLE = "BAIT conservation (minted vs locked)"
    WIKI_DESCRIPTION = (
        "Bridge conservation requires totalMinted <= totalLockedOnL1. "
        "Writes to totalMinted should be guarded by that invariant."
    )
    WIKI_EXPLOIT_SCENARIO = (
        "If totalMinted increases without checking totalLockedOnL1, "
        "wBAIT could be minted without corresponding L1 lock evidence."
    )
    WIKI_RECOMMENDATION = (
        "Keep require(totalMinted + amount <= totalLockedOnL1) before "
        "incrementing totalMinted (see BridgeLock._executeLockMint)."
    )

    def _detect(self) -> List:
        results = []
        for contract in self.compilation_unit.contracts:
            if contract.is_interface or contract.is_library:
                continue
            for function in contract.functions_declared:
                writes_minted = False
                guards_locked = False
                for node in function.nodes:
                    for v in node.state_variables_written:
                        name = v.name if hasattr(v, "name") else str(v)
                        if name == "totalMinted":
                            writes_minted = True
                    if node.expression is not None:
                        expr = str(node.expression)
                        if "totalLockedOnL1" in expr and "totalMinted" in expr:
                            guards_locked = True
                if writes_minted and not guards_locked:
                    info = [
                        function,
                        " writes totalMinted without an in-function guard referencing totalLockedOnL1\n",
                    ]
                    results.append(self.generate_result(info))
        return results
