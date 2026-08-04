"""
b'AI'tcoin Anchor Contracts (Phase C)

Pre-built smart contract templates for the b'AI'tcoin ecosystem.
Each template includes valid VM bytecode and a JSON-like ABI.

Templates:
    - BAIT_ERC20_TEMPLATE:  ERC-20-like token contract
    - STAKING_POOL_TEMPLATE: Staking pool for BAIT tokens
    - ORACLE_TEMPLATE:       Oracle contract for AI agent data feeds
"""

from __future__ import annotations

import hashlib
import logging
import struct
from typing import Any

from baitcoin_core.contracts.contract_engine import (
    Assembler,
    OpCode,
    _function_id,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contract Builder – assembles bytecode with dispatch table & label resolution
# ---------------------------------------------------------------------------

class _LabelAssembler:
    """Assembler that supports named labels for JUMP/JUMPI targets.

    Usage::

        la = _LabelAssembler()
        la.push(1)
        la.label("loop")
        la.push(1)
        la.add()
        la.push("loop")
        la.jumpi()
        la.stop()
        bytecode = la.build({"my_func": la})  # not quite – see ContractBuilder
    """

    def __init__(self) -> None:
        self._ops: list[tuple[str, int | str]] = []  # (opcode_name, operand)
        self._labels: dict[str, int] = {}

    def _add(self, op: str, operand: int | str | None = None) -> "_LabelAssembler":
        self._ops.append((op, operand))
        return self

    # -- instructions --
    def push(self, value: int | str) -> "_LabelAssembler":
        return self._add("PUSH", value)

    def pop(self) -> "_LabelAssembler":
        return self._add("POP")

    def add(self) -> "_LabelAssembler":
        return self._add("ADD")

    def sub(self) -> "_LabelAssembler":
        return self._add("SUB")

    def mul(self) -> "_LabelAssembler":
        return self._add("MUL")

    def div(self) -> "_LabelAssembler":
        return self._add("DIV")

    def lt(self) -> "_LabelAssembler":
        return self._add("LT")

    def gt(self) -> "_LabelAssembler":
        return self._add("GT")

    def eq(self) -> "_LabelAssembler":
        return self._add("EQ")

    def jump(self, label: str) -> "_LabelAssembler":
        return self._add("JUMP", label)

    def jumpi(self, label: str) -> "_LabelAssembler":
        return self._add("JUMPI", label)

    def store(self) -> "_LabelAssembler":
        return self._add("STORE")

    def load(self) -> "_LabelAssembler":
        return self._add("LOAD")

    def caller(self) -> "_LabelAssembler":
        return self._add("CALLER")

    def value(self) -> "_LabelAssembler":
        return self._add("VALUE")

    def ret(self) -> "_LabelAssembler":
        return self._add("RETURN")

    def log(self) -> "_LabelAssembler":
        return self._add("LOG")

    def stop(self) -> "_LabelAssembler":
        return self._add("STOP")

    def label(self, name: str) -> "_LabelAssembler":
        """Define a label at the current position."""
        self._labels[name] = len(self._ops)
        return self

    # -- compilation --

    def _body_size(self) -> int:
        """Compute byte size of this function body (unresolved labels counted as 5)."""
        size = 0
        for op, operand in self._ops:
            if op == "PUSH":
                size += 5  # 1 opcode + 4 bytes
            elif op in ("JUMP", "JUMPI"):
                size += 3  # 1 opcode + 2 bytes
            else:
                size += 1
        return size


def _build_contract(functions: dict[str, _LabelAssembler]) -> bytes:
    """Build complete contract bytecode with dispatch table.

    Resolves all labels to absolute byte offsets within the full bytecode.
    """
    func_names = list(functions.keys())
    n = len(func_names)

    # 1. Compute body sizes
    body_sizes = {name: asm._body_size() for name, asm in functions.items()}

    # 2. Dispatch table layout
    table_size = 2 + n * 6

    # 3. Function offsets (absolute)
    func_offsets: dict[str, int] = {}
    offset = table_size
    for name in func_names:
        func_offsets[name] = offset
        offset += body_sizes[name]

    # 4. Build dispatch table
    buf = bytearray(struct.pack(">H", n))
    for name in func_names:
        fid = _function_id(name)
        buf.extend(struct.pack(">I", fid))
        buf.extend(struct.pack(">H", func_offsets[name]))

    # 5. Compile each function body, resolving labels
    opcode_map = {
        "PUSH": OpCode.PUSH,
        "POP": OpCode.POP,
        "ADD": OpCode.ADD,
        "SUB": OpCode.SUB,
        "MUL": OpCode.MUL,
        "DIV": OpCode.DIV,
        "LT": OpCode.LT,
        "GT": OpCode.GT,
        "EQ": OpCode.EQ,
        "JUMP": OpCode.JUMP,
        "JUMPI": OpCode.JUMPI,
        "STORE": OpCode.STORE,
        "LOAD": OpCode.LOAD,
        "CALLER": OpCode.CALLER,
        "VALUE": OpCode.VALUE,
        "RETURN": OpCode.RETURN,
        "LOG": OpCode.LOG,
        "STOP": OpCode.STOP,
    }

    for name in func_names:
        asm = functions[name]
        base = func_offsets[name]

        # Build label -> absolute byte offset map
        label_offsets: dict[str, int] = {}
        byte_pos = 0
        for op, operand in asm._ops:
            if isinstance(operand, str) and op != "PUSH":
                # This is a label definition check – labels stored in asm._labels as op-index
                pass
            if op == "PUSH":
                byte_pos += 5
            elif op in ("JUMP", "JUMPI"):
                byte_pos += 3
            else:
                byte_pos += 1

        # Resolve label indices to byte offsets
        for lbl_name, lbl_op_idx in asm._labels.items():
            # Count bytes up to that op index
            b = 0
            for i in range(lbl_op_idx):
                o, _ = asm._ops[i]
                if o == "PUSH":
                    b += 5
                elif o in ("JUMP", "JUMPI"):
                    b += 3
                else:
                    b += 1
            label_offsets[lbl_name] = base + b

        # Emit bytecode
        for op, operand in asm._ops:
            buf.append(opcode_map[op])
            if op == "PUSH":
                if isinstance(operand, str) and operand in label_offsets:
                    buf.extend(struct.pack(">i", label_offsets[operand]))
                else:
                    buf.extend(struct.pack(">i", int(operand)))
            elif op in ("JUMP", "JUMPI"):
                # operand is a label name
                target = label_offsets.get(str(operand), 0)
                buf.extend(struct.pack(">H", target & 0xFFFF))

    return bytes(buf)


# ---------------------------------------------------------------------------
# ERC-20-like Token Contract
# ---------------------------------------------------------------------------

def _build_erc20() -> tuple[bytes, list[dict[str, Any]]]:
    """Build ERC-20 token bytecode and ABI."""

    abi = [
        {"name": "name", "inputs": [], "outputs": ["string"], "type": "view"},
        {"name": "symbol", "inputs": [], "outputs": ["string"], "type": "view"},
        {"name": "decimals", "inputs": [], "outputs": ["uint8"], "type": "view"},
        {"name": "totalSupply", "inputs": [], "outputs": ["uint256"], "type": "view"},
        {"name": "balanceOf", "inputs": ["address"], "outputs": ["uint256"], "type": "view"},
        {"name": "transfer", "inputs": ["address", "uint256"], "outputs": ["bool"], "type": "payable"},
        {"name": "approve", "inputs": ["address", "uint256"], "outputs": ["bool"], "type": "payable"},
        {"name": "transferFrom", "inputs": ["address", "address", "uint256"], "outputs": ["bool"], "type": "payable"},
    ]

    # Simple string identifiers for name/symbol (must fit in signed int32)
    bait_hash = int.from_bytes(hashlib.sha256(b"BAIT").digest()[:4], "big") % (2**31 - 1)
    bait_symbol_hash = int.from_bytes(hashlib.sha256(b"BAIT_SYM").digest()[:4], "big") % (2**31 - 1)

    # --- name() ---
    f_name = _LabelAssembler()
    f_name.push(bait_hash).ret()

    # --- symbol() ---
    f_symbol = _LabelAssembler()
    f_symbol.push(bait_symbol_hash).ret()

    # --- decimals() ---
    f_decimals = _LabelAssembler()
    f_decimals.push(8).ret()

    # --- totalSupply() ---
    f_supply = _LabelAssembler()
    f_supply.push(21_000_000).ret()

    # --- balanceOf(account) ---
    # Stack: [account]. LOAD pops account (as key), pushes state[account].
    f_balanceof = _LabelAssembler()
    f_balanceof.load().ret()

    # --- transfer(to, amount) ---
    # Stack: [to, amount]
    f_transfer = _LabelAssembler()
    # Save amount to temp slot 5001
    (f_transfer
     .push(5001).store()          # state["5001"] = amount; stack: [to]
     .push(5000).store()          # state["5000"] = to; stack: []
     # Check sender balance
     .caller().load()            # [sender_bal]
     .push(5001).load()          # [sender_bal, amount]
     .lt()                      # [is_insufficient]
     .jumpi("fail")
     # Deduct from sender
     .caller().caller().load()  # [caller_hash, sender_bal]
     .push(5001).load()          # [caller_hash, sender_bal, amount]
     .sub()                     # [caller_hash, new_bal]
     .caller()                  # [caller_hash, new_bal, caller_hash]
     .store()                   # state[caller_hash] = new_bal; stack: [caller_hash]
     .pop()                     # stack: []
     # Add to recipient
     .push(5000).load()          # [to]
     .load()                    # [to_bal]
     .push(5001).load()          # [to_bal, amount]
     .add()                     # [to_bal + amount]
     .push(5000).load()          # [new_to_bal, to]
     .store()                   # state[to] = new_to_bal
     .push(1).log().ret()       # log success, return 1
     .label("fail")
     .push(0).ret())            # return 0 on failure

    # --- approve(spender, amount) ---
    # Stack: [spender, amount]
    # Store: state["8000"] = amount (simplified single-slot approval)
    f_approve = _LabelAssembler()
    (f_approve
     .push(8000).store()        # state["8000"] = amount; stack: [spender]
     .pop()                     # discard spender
     .push(1).ret())            # return success

    # --- transferFrom(from, to, amount) ---
    # Stack: [from, to, amount]
    f_xfer = _LabelAssembler()
    (f_xfer
     # Save all args
     .push(7002).store()        # state["7002"] = amount; stack: [from, to]
     .push(7001).store()        # state["7001"] = to; stack: [from]
     .push(7000).store()        # state["7000"] = from; stack: []
     # Get from's balance
     .push(7000).load()          # [from]
     .load()                    # [from_bal]
     .push(7002).load()          # [from_bal, amount]
     .lt()                      # [insufficient?]
     .jumpi("xfail")
     # Deduct from 'from'
     .push(7000).load()          # [from]
     .push(7000).load()          # [from, from]
     .load()                    # [from, from_bal]
     .push(7002).load()          # [from, from_bal, amount]
     .sub()                     # [from, new_from_bal]
     .push(7000).load()          # [from, new_from_bal, from]
     .store()                   # state[from] = new_from_bal; stack: [from]
     .pop()                     # stack: []
     # Add to 'to'
     .push(7001).load()          # [to]
     .load()                    # [to_bal]
     .push(7002).load()          # [to_bal, amount]
     .add()                     # [new_to_bal]
     .push(7001).load()          # [new_to_bal, to]
     .store()                   # state[to] = new_to_bal
     .push(1).ret()
     .label("xfail")
     .push(0).ret())

    bytecode = _build_contract({
        "name": f_name,
        "symbol": f_symbol,
        "decimals": f_decimals,
        "totalSupply": f_supply,
        "balanceOf": f_balanceof,
        "transfer": f_transfer,
        "approve": f_approve,
        "transferFrom": f_xfer,
    })

    return bytecode, abi


# ---------------------------------------------------------------------------
# Staking Pool Contract
# ---------------------------------------------------------------------------

def _build_staking() -> tuple[bytes, list[dict[str, Any]]]:
    """Build staking pool bytecode and ABI."""

    abi = [
        {"name": "stake", "inputs": ["uint256"], "outputs": ["bool"], "type": "payable"},
        {"name": "unstake", "inputs": ["uint256"], "outputs": ["bool"], "type": "payable"},
        {"name": "claimRewards", "inputs": [], "outputs": ["uint256"], "type": "payable"},
        {"name": "getStakerInfo", "inputs": ["address"], "outputs": ["uint256"], "type": "view"},
        {"name": "totalStaked", "inputs": [], "outputs": ["uint256"], "type": "view"},
    ]

    # --- stake(amount) ---
    # Stack: [amount]
    # Add amount to caller's staked balance at state[caller]
    # Add amount to total at state["6000"]
    f_stake = _LabelAssembler()
    (f_stake
     # Save amount to temp
     .push(9000).store()        # state["9000"] = amount; stack: []
     # Add to staker's balance
     .caller()                   # [caller]
     .caller().load()           # [caller, current_stake]
     .push(9000).load()          # [caller, current_stake, amount]
     .add()                     # [caller, new_stake]
     .caller()                  # [caller, new_stake, caller]
     .store()                   # state[caller] = new_stake; stack: [caller]
     .pop()                     # stack: []
     # Add to total
     .push(6000).load()          # [current_total]
     .push(9000).load()          # [current_total, amount]
     .add()                     # [new_total]
     .push(6000)                # [new_total, 6000]
     .store()                   # state["6000"] = new_total
     .push(1).log().ret())      # log, return 1

    # --- unstake(amount) ---
    # Stack: [amount]
    f_unstake = _LabelAssembler()
    (f_unstake
     .push(9001).store()        # state["9001"] = amount; stack: []
     # Check staker balance
     .caller().load()           # [staker_balance]
     .push(9001).load()          # [staker_balance, amount]
     .lt()                      # [insufficient?]
     .jumpi("ufail")
     # Deduct
     .caller()                   # [caller]
     .caller().load()           # [caller, current]
     .push(9001).load()          # [caller, current, amount]
     .sub()                     # [caller, new_balance]
     .caller()                  # [caller, new_balance, caller]
     .store()                   # state[caller] = new_balance; stack: [caller]
     .pop()                     # stack: []
     # Deduct from total
     .push(6000).load()          # [total]
     .push(9001).load()          # [total, amount]
     .sub()                     # [new_total]
     .push(6000).store()         # state["6000"] = new_total
     .push(1).ret()
     .label("ufail")
     .push(0).ret())

    # --- claimRewards() ---
    # Simplified: return state["6001"] (reward pool, set externally)
    f_claim = _LabelAssembler()
    (f_claim
     .push(6001).load()          # [rewards]
     .ret())

    # --- getStakerInfo(staker) ---
    # Stack: [staker]. Load state[staker].
    f_info = _LabelAssembler()
    f_info.load().ret()

    # --- totalStaked() ---
    # Return state["6000"]
    f_total = _LabelAssembler()
    (f_total
     .push(6000).load()          # [total]
     .ret())

    bytecode = _build_contract({
        "stake": f_stake,
        "unstake": f_unstake,
        "claimRewards": f_claim,
        "getStakerInfo": f_info,
        "totalStaked": f_total,
    })

    return bytecode, abi


# ---------------------------------------------------------------------------
# Oracle Contract
# ---------------------------------------------------------------------------

def _build_oracle() -> tuple[bytes, list[dict[str, Any]]]:
    """Build oracle contract bytecode and ABI."""

    abi = [
        {"name": "submitData", "inputs": ["bytes32", "string"], "outputs": ["bool"], "type": "payable"},
        {"name": "getValue", "inputs": ["string"], "outputs": ["uint256"], "type": "view"},
        {"name": "getLastUpdate", "inputs": [], "outputs": ["uint256"], "type": "view"},
        {"name": "getSources", "inputs": [], "outputs": ["uint256"], "type": "view"},
    ]

    # State layout:
    #   state["4000"] = number of sources
    #   state["4001"] = last update timestamp (simulated as counter)
    #   state[data_key] = data_hash value
    #   state["src_0"], state["src_1"], ... = source identifiers

    # --- submitData(data_hash, source) ---
    # Stack: [data_hash, source]
    # Store data_hash at a key derived from source
    # Increment source count, update timestamp
    f_submit = _LabelAssembler()
    (f_submit
     # Save args
     .push(9501).store()        # state["9501"] = source; stack: [data_hash]
     # Store data: state[source] = data_hash
     .push(9501).load()          # [data_hash, source]
     .store()                   # state[source] = data_hash; stack: []
     # Register source: state[current_count] = source
     .push(9501).load()          # [source]
     .push(4000).load()          # [source, current_count]
     .store()                   # state[current_count] = source; stack: []
     # Increment source count
     .push(4000).load()          # [count]
     .push(1).add()             # [count + 1]
     .push(4000).store()         # state["4000"] = count + 1
     # Update last update (increment as simulated timestamp)
     .push(4001).load()          # [old_ts]
     .push(1).add()             # [old_ts + 1]
     .push(4001).store()         # state["4001"] = new_ts
     .push(1).log().ret())

    # --- getValue(data_key) ---
    # Stack: [data_key]. Return state[data_key].
    f_getval = _LabelAssembler()
    f_getval.load().ret()

    # --- getLastUpdate() ---
    # Return state["4001"]
    f_lastupd = _LabelAssembler()
    (f_lastupd
     .push(4001).load()          # [timestamp]
     .ret())

    # --- getSources() ---
    # Return state["4000"] (source count)
    f_getsrc = _LabelAssembler()
    (f_getsrc
     .push(4000).load()          # [count]
     .ret())

    bytecode = _build_contract({
        "submitData": f_submit,
        "getValue": f_getval,
        "getLastUpdate": f_lastupd,
        "getSources": f_getsrc,
    })

    return bytecode, abi


# ---------------------------------------------------------------------------
# Build all templates at import time
# ---------------------------------------------------------------------------

def _make_template(
    name: str, description: str, bytecode: bytes, abi: list[dict[str, Any]],
) -> dict[str, Any]:
    """Package a contract template into the standard dict format."""
    return {
        "name": name,
        "description": description,
        "bytecode_hex": bytecode.hex(),
        "abi": abi,
    }


_erc20_code, _erc20_abi = _build_erc20()
BAIT_ERC20_TEMPLATE: dict[str, Any] = _make_template(
    name="BAIT_ERC20",
    description=(
        "ERC-20-like token contract for b'AI'tcoin. Supports name, symbol, "
        "decimals, totalSupply, balanceOf, transfer, approve, transferFrom."
    ),
    bytecode=_erc20_code,
    abi=_erc20_abi,
)

_staking_code, _staking_abi = _build_staking()
STAKING_POOL_TEMPLATE: dict[str, Any] = _make_template(
    name="BAIT_StakingPool",
    description=(
        "Staking pool contract. Users can stake BAIT, unstake, claim rewards, "
        "and query staker info and total staked amount."
    ),
    bytecode=_staking_code,
    abi=_staking_abi,
)

_oracle_code, _oracle_abi = _build_oracle()
ORACLE_TEMPLATE: dict[str, Any] = _make_template(
    name="BAIT_Oracle",
    description=(
        "Oracle contract for AI agents. Allows submitting off-chain data hashes, "
        "querying values by key, checking last update time, and listing sources."
    ),
    bytecode=_oracle_code,
    abi=_oracle_abi,
)

# Registry of all anchor templates by name
ANCHOR_REGISTRY: dict[str, dict[str, Any]] = {
    "BAIT_ERC20": BAIT_ERC20_TEMPLATE,
    "BAIT_StakingPool": STAKING_POOL_TEMPLATE,
    "BAIT_Oracle": ORACLE_TEMPLATE,
}


# ---------------------------------------------------------------------------
# Helper: deploy an anchor contract
# ---------------------------------------------------------------------------

def deploy_anchor(
    name: str,
    engine: Any,
    deployer: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Deploy a named anchor contract template.

    Parameters
    ----------
    name:
        Template name, e.g. ``"BAIT_ERC20"``, ``"BAIT_StakingPool"``,
        ``"BAIT_Oracle"``.
    engine:
        A :class:`ContractEngine` instance.
    deployer:
        Hex public key / address of the deployer.
    **kwargs:
        Forwarded to :meth:`ContractEngine.deploy_contract` as *init_args*.

    Returns
    -------
    dict
        Result from :meth:`ContractEngine.deploy_contract`, augmented with
        ``template_name`` and ``abi``.

    Raises
    ------
    ValueError
        If *name* is not a known anchor template.
    """
    if name not in ANCHOR_REGISTRY:
        available = ", ".join(sorted(ANCHOR_REGISTRY.keys()))
        raise ValueError(
            f"Unknown anchor template '{name}'. Available: {available}"
        )

    template = ANCHOR_REGISTRY[name]
    result = engine.deploy_contract(
        deployer=deployer,
        code_hex=template["bytecode_hex"],
        init_args=kwargs,
    )

    if result["success"]:
        result["template_name"] = name
        result["abi"] = template["abi"]
        logger.info(
            "Deployed anchor '%s' at %s", name, result["contract_address"]
        )

    return result
