"""
b'AI'tcoin Smart Contract Execution Engine (Phase C)

Implements a stack-based virtual machine for executing smart contract bytecode,
along with a ContractEngine that manages contract deployment, invocation,
state persistence, and gas metering.

Opcodes:
    PUSH <i32>   - Push 4-byte signed integer onto the stack
    POP          - Discard top of stack
    ADD          - Pop two, push sum
    SUB          - Pop two, push difference (a - b)
    MUL          - Pop two, push product
    DIV          - Pop two, push quotient (a / b, truncates toward zero)
    LT           - Pop two, push 1 if a < b else 0
    GT           - Pop two, push 1 if a > b else 0
    EQ           - Pop two, push 1 if a == b else 0
    JUMP <u16>   - Set PC to offset
    JUMPI <u16>  - Pop condition; if non-zero, set PC to offset
    STORE        - Pop key, pop value; store value at key in contract state
    LOAD         - Pop key; push state[key] (0 if missing)
    CALLER       - Push caller address hash (as int)
    VALUE        - Push value (satoshis) sent with the call
    RETURN       - Pop value; halt, return it as result
    LOG          - Pop value; append to execution logs
    STOP         - Halt execution with no return value

Bytecode layout for dispatchable contracts:
    The first 2 bytes encode the number of function entries N.
    Then N entries follow, each 6 bytes: 4-byte function_id + 2-byte offset.
    After the dispatch table comes the actual instruction body.
    function_id = first 4 bytes of SHA-256(function_name).
"""

from __future__ import annotations

import hashlib
import logging
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CONTRACT_SIZE: int = 64 * 1024  # 64 KB
MAX_GAS_PER_CONTRACT: int = 10_000_000

# Gas costs per opcode
_GAS_COSTS: dict[int, int] = {
    0x00: 2,  # PUSH
    0x01: 1,  # POP
    0x02: 3,  # ADD
    0x03: 3,  # SUB
    0x04: 3,  # MUL
    0x05: 5,  # DIV
    0x06: 2,  # LT
    0x07: 2,  # GT
    0x08: 2,  # EQ
    0x09: 3,  # JUMP
    0x0A: 4,  # JUMPI
    0x0B: 20,  # STORE (storage is expensive)
    0x0C: 20,  # LOAD
    0x0D: 2,  # CALLER
    0x0E: 2,  # VALUE
    0x0F: 3,  # RETURN
    0x10: 3,  # LOG
    0x11: 0,  # STOP
}


class OpCode(IntEnum):
    """Bytecode opcodes for the b'AI'tcoin contract VM."""
    PUSH = 0x00
    POP = 0x01
    ADD = 0x02
    SUB = 0x03
    MUL = 0x04
    DIV = 0x05
    LT = 0x06
    GT = 0x07
    EQ = 0x08
    JUMP = 0x09
    JUMPI = 0x0A
    STORE = 0x0B
    LOAD = 0x0C
    CALLER = 0x0D
    VALUE = 0x0E
    RETURN = 0x0F
    LOG = 0x10
    STOP = 0x11


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _function_id(name: str) -> int:
    """Derive a 4-byte function selector from a function name."""
    return int.from_bytes(hashlib.sha256(name.encode()).digest()[:4], "big")


def _derive_address(deployer_pubkey: str, nonce: int) -> str:
    """Derive a contract address from deployer public key and nonce.

    Uses SHA-256(deployer_pubkey || nonce) and returns the hex digest.
    """
    payload = f"{deployer_pubkey}:{nonce}".encode()
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# VM execution context
# ---------------------------------------------------------------------------

@dataclass
class _VMContext:
    """Execution context passed to the VM."""
    caller: str
    value: int
    contract_address: str
    function_name: str
    args: dict[str, Any]


# ---------------------------------------------------------------------------
# Contract VM
# ---------------------------------------------------------------------------

class ContractVM:
    """Minimal stack-based virtual machine for b'AI'tcoin smart contracts.

    The VM executes raw bytecode, maintains a value stack, and can read/write
    contract state.  Gas is metered per instruction.
    """

    def __init__(self) -> None:
        self._gas_used: int = 0
        self._logs: list[str] = []
        self._stopped: bool = False
        self._returned: bool = False
        self._return_value: Any = None

    # -- public read-only accessors --

    @property
    def gas_used(self) -> int:
        return self._gas_used

    @property
    def logs(self) -> list[str]:
        return list(self._logs)

    @property
    def return_value(self) -> Any:
        return self._return_value

    # -- execution --

    def execute(
        self,
        bytecode: bytes,
        state: dict[str, Any],
        ctx: _VMContext,
        gas_limit: int,
    ) -> bool:
        """Run *bytecode* with the given *state* and *ctx*.

        Returns ``True`` if execution completed successfully (STOP or RETURN),
        ``False`` on out-of-gas, stack underflow, or invalid opcode.
        """
        self._gas_used = 0
        self._logs = []
        self._stopped = False
        self._returned = False
        self._return_value = None

        stack: list[int] = []
        pc: int = 0
        caller_hash: int = int(ctx.caller[:8], 16)  # truncated caller identifier

        # Pre-load function arguments onto the stack (last arg on top)
        for _key, _val in ctx.args.items():
            stack.append(int(_val) if not isinstance(_val, int) else _val)

        # Resolve entry point: look for dispatch table at bytecode start
        entry_pc = self._resolve_entry(bytecode, ctx.function_name)
        if entry_pc is None:
            logger.warning(
                "Contract %s: function '%s' not found in dispatch table; starting from PC 0",
                ctx.contract_address,
                ctx.function_name,
            )
            entry_pc = 0
        pc = entry_pc

        while pc < len(bytecode) and not self._stopped and not self._returned:
            opcode_int = bytecode[pc]
            opcode = OpCode(opcode_int) if opcode_int in _GAS_COSTS else None

            if opcode is None:
                logger.error(
                    "Invalid opcode 0x%02X at PC=%d", opcode_int, pc
                )
                return False

            cost = _GAS_COSTS[opcode_int]
            self._gas_used += cost
            if self._gas_used > gas_limit:
                logger.warning("Out of gas at PC=%d (used=%d, limit=%d)", pc, self._gas_used, gas_limit)
                return False

            pc += 1

            if opcode == OpCode.PUSH:
                if pc + 4 > len(bytecode):
                    return False
                val = struct.unpack(">i", bytecode[pc : pc + 4])[0]
                stack.append(val)
                pc += 4

            elif opcode == OpCode.POP:
                if not stack:
                    return False
                stack.pop()

            elif opcode == OpCode.ADD:
                if len(stack) < 2:
                    return False
                b, a = stack.pop(), stack.pop()
                stack.append(a + b)

            elif opcode == OpCode.SUB:
                if len(stack) < 2:
                    return False
                b, a = stack.pop(), stack.pop()
                stack.append(a - b)

            elif opcode == OpCode.MUL:
                if len(stack) < 2:
                    return False
                b, a = stack.pop(), stack.pop()
                stack.append(a * b)

            elif opcode == OpCode.DIV:
                if len(stack) < 2:
                    return False
                b, a = stack.pop(), stack.pop()
                if b == 0:
                    return False
                # Truncate toward zero (Python's int division floors for negatives)
                stack.append(int(a / b))

            elif opcode == OpCode.LT:
                if len(stack) < 2:
                    return False
                b, a = stack.pop(), stack.pop()
                stack.append(1 if a < b else 0)

            elif opcode == OpCode.GT:
                if len(stack) < 2:
                    return False
                b, a = stack.pop(), stack.pop()
                stack.append(1 if a > b else 0)

            elif opcode == OpCode.EQ:
                if len(stack) < 2:
                    return False
                b, a = stack.pop(), stack.pop()
                stack.append(1 if a == b else 0)

            elif opcode == OpCode.JUMP:
                if pc + 2 > len(bytecode):
                    return False
                target = struct.unpack(">H", bytecode[pc : pc + 2])[0]
                pc = target

            elif opcode == OpCode.JUMPI:
                if pc + 2 > len(bytecode):
                    return False
                target = struct.unpack(">H", bytecode[pc : pc + 2])[0]
                pc += 2
                if not stack:
                    return False
                cond = stack.pop()
                if cond != 0:
                    pc = target

            elif opcode == OpCode.STORE:
                if len(stack) < 2:
                    return False
                key = str(stack.pop())
                val = stack.pop()
                state[key] = val

            elif opcode == OpCode.LOAD:
                if not stack:
                    return False
                key = str(stack.pop())
                stack.append(state.get(key, 0))

            elif opcode == OpCode.CALLER:
                stack.append(caller_hash)

            elif opcode == OpCode.VALUE:
                stack.append(ctx.value)

            elif opcode == OpCode.RETURN:
                if not stack:
                    self._return_value = None
                else:
                    self._return_value = stack.pop()
                self._returned = True

            elif opcode == OpCode.LOG:
                if not stack:
                    return False
                val = stack.pop()
                self._logs.append(str(val))

            elif opcode == OpCode.STOP:
                self._stopped = True

        return True

    # -- private helpers --

    @staticmethod
    def _resolve_entry(bytecode: bytes, function_name: str) -> int | None:
        """Parse the dispatch table at the start of *bytecode*.

        Layout::
            [0..1]  u16  number_of_entries
            [2..]   N x (u32 function_id, u16 offset)

        If the bytecode is too short or the function is not found,
        returns ``None``.
        """
        if len(bytecode) < 2:
            return None
        n_entries = struct.unpack(">H", bytecode[0:2])[0]
        if n_entries == 0 or n_entries > 256:
            # No dispatch table or absurdly large → skip
            return None
        expected_min = 2 + n_entries * 6
        if len(bytecode) < expected_min:
            return None
        target_fid = _function_id(function_name)
        for i in range(n_entries):
            offset = 2 + i * 6
            fid = struct.unpack(">I", bytecode[offset : offset + 4])[0]
            jump_to = struct.unpack(">H", bytecode[offset + 4 : offset + 6])[0]
            if fid == target_fid:
                return jump_to
        return None


# ---------------------------------------------------------------------------
# Bytecode assembler helpers
# ---------------------------------------------------------------------------

class Assembler:
    """Minimal assembler for building contract bytecode.

    Usage::

        asm = Assembler()
        asm.push(42)
        asm.add()
        asm.stop()
        code = asm.bytecode()
    """

    def __init__(self) -> None:
        self._buf: bytearray = bytearray()

    def _emit(self, *b: int) -> "Assembler":
        self._buf.extend(b)
        return self

    def push(self, value: int) -> "Assembler":
        self._emit(OpCode.PUSH)
        self._buf.extend(struct.pack(">i", value))
        return self

    def pop(self) -> "Assembler":
        return self._emit(OpCode.POP)

    def add(self) -> "Assembler":
        return self._emit(OpCode.ADD)

    def sub(self) -> "Assembler":
        return self._emit(OpCode.SUB)

    def mul(self) -> "Assembler":
        return self._emit(OpCode.MUL)

    def div(self) -> "Assembler":
        return self._emit(OpCode.DIV)

    def lt(self) -> "Assembler":
        return self._emit(OpCode.LT)

    def gt(self) -> "Assembler":
        return self._emit(OpCode.GT)

    def eq(self) -> "Assembler":
        return self._emit(OpCode.EQ)

    def jump(self, offset: int) -> "Assembler":
        self._emit(OpCode.JUMP)
        self._buf.extend(struct.pack(">H", offset & 0xFFFF))
        return self

    def jumpi(self, offset: int) -> "Assembler":
        self._emit(OpCode.JUMPI)
        self._buf.extend(struct.pack(">H", offset & 0xFFFF))
        return self

    def store(self) -> "Assembler":
        return self._emit(OpCode.STORE)

    def load(self) -> "Assembler":
        return self._emit(OpCode.LOAD)

    def caller(self) -> "Assembler":
        return self._emit(OpCode.CALLER)

    def value(self) -> "Assembler":
        return self._emit(OpCode.VALUE)

    def ret(self) -> "Assembler":
        return self._emit(OpCode.RETURN)

    def log(self) -> "Assembler":
        return self._emit(OpCode.LOG)

    def stop(self) -> "Assembler":
        return self._emit(OpCode.STOP)

    def raw(self, data: bytes) -> "Assembler":
        """Append raw bytes (useful for embedding a dispatch table)."""
        self._buf.extend(data)
        return self

    def current_offset(self) -> int:
        return len(self._buf)

    def bytecode(self) -> bytes:
        return bytes(self._buf)


def build_bytecode_with_dispatch(
    functions: dict[str, bytes],
) -> bytes:
    """Build a contract bytecode with a dispatch table.

    Parameters
    ----------
    functions:
        Mapping of ``function_name`` → raw instruction bytes (without dispatch).

    Returns
    -------
    bytes
        Complete bytecode: dispatch header + function bodies.
    """
    # Header: 2 bytes for N
    n = len(functions)
    header = struct.pack(">H", n)

    # Compute dispatch table entries and body offsets
    table_size = 2 + n * 6
    entries: list[tuple[int, int]] = []  # (function_id, offset)

    current_offset = table_size
    func_bodies: list[bytes] = []
    for name, body in functions.items():
        fid = _function_id(name)
        entries.append((fid, current_offset))
        func_bodies.append(body)
        current_offset += len(body)

    # Assemble
    buf = bytearray(header)
    for fid, offset in entries:
        buf.extend(struct.pack(">I", fid))
        buf.extend(struct.pack(">H", offset))
    for body in func_bodies:
        buf.extend(body)

    return bytes(buf)


# ---------------------------------------------------------------------------
# Contract Engine
# ---------------------------------------------------------------------------

class ContractEngine:
    """High-level smart contract manager for the b'AI'tcoin blockchain.

    Manages contract lifecycle (deploy, call, query) and maintains the
    in-memory contract state store.  All addresses are hex strings.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, dict[str, Any]] = {}
        self._nonce: dict[str, int] = {}  # deployer -> next nonce
        self._vm = ContractVM()
        logger.info("ContractEngine initialised")

    # -- deploy --

    def deploy_contract(
        self,
        deployer: str,
        code_hex: str,
        init_args: dict[str, Any] | None = None,
        gas_limit: int = MAX_GAS_PER_CONTRACT,
    ) -> dict[str, Any]:
        """Deploy a new smart contract.

        Parameters
        ----------
        deployer:
            Hex public key or address of the deployer.
        code_hex:
            Hex-encoded contract bytecode.
        init_args:
            Optional arguments passed to an ``init`` function.
        gas_limit:
            Maximum gas units the deployer is willing to spend.

        Returns
        -------
        dict
            ``{contract_address, gas_used, success}``
        """
        init_args = init_args or {}

        # Validate bytecode
        if not self.validate_contract_code(code_hex):
            return {
                "contract_address": "",
                "gas_used": 0,
                "success": False,
                "error": "Invalid contract code",
            }

        code: bytes = bytes.fromhex(code_hex)

        # Derive address
        nonce = self._nonce.get(deployer, 0)
        contract_address = _derive_address(deployer, nonce)

        # Check for collision
        if contract_address in self._contracts:
            return {
                "contract_address": "",
                "gas_used": 0,
                "success": False,
                "error": "Contract address collision",
            }

        # Initialise state
        state: dict[str, Any] = {}
        self._contracts[contract_address] = {
            "code": code,
            "state": state,
            "owner": deployer,
            "balance": 0,
            "created_at": time.time(),
        }
        self._nonce[deployer] = nonce + 1

        # Run optional init
        gas_used = 0
        if init_args and len(code) > 0:
            ctx = _VMContext(
                caller=deployer,
                value=0,
                contract_address=contract_address,
                function_name="init",
                args=init_args,
            )
            vm = ContractVM()
            ok = vm.execute(code, state, ctx, gas_limit)
            gas_used = vm.gas_used
            if not ok:
                logger.warning("Contract init failed for %s", contract_address)
                # Keep the contract but note the failure

        logger.info(
            "Deployed contract %s by %s (gas=%d)",
            contract_address,
            deployer,
            gas_used,
        )

        return {
            "contract_address": contract_address,
            "gas_used": gas_used,
            "success": True,
        }

    # -- call --

    def call_contract(
        self,
        caller: str,
        contract_address: str,
        function_name: str,
        args: dict[str, Any] | None = None,
        gas_limit: int = MAX_GAS_PER_CONTRACT,
        value: int = 0,
    ) -> dict[str, Any]:
        """Execute a function on a deployed contract.

        Parameters
        ----------
        caller:
            Hex address of the caller.
        contract_address:
            Hex address of the target contract.
        function_name:
            Name of the function to invoke.
        args:
            Named arguments forwarded to the VM as stack values.
        gas_limit:
            Maximum gas for this call.
        value:
            BAIT satoshis to send with the call (credited to contract).

        Returns
        -------
        dict
            ``{result, gas_used, success, logs}``
        """
        args = args or {}

        if contract_address not in self._contracts:
            return {
                "result": None,
                "gas_used": 0,
                "success": False,
                "logs": [],
                "error": "Contract not found",
            }

        contract = self._contracts[contract_address]
        code: bytes = contract["code"]
        state: dict[str, Any] = contract["state"]

        # Credit value to contract balance
        contract["balance"] += value

        ctx = _VMContext(
            caller=caller,
            value=value,
            contract_address=contract_address,
            function_name=function_name,
            args=args,
        )

        vm = ContractVM()
        ok = vm.execute(code, state, ctx, gas_limit)

        result = {
            "result": vm.return_value,
            "gas_used": vm.gas_used,
            "success": ok,
            "logs": vm.logs,
        }

        logger.debug(
            "call_contract(%s.%s) -> success=%s gas=%d",
            contract_address[:12],
            function_name,
            ok,
            vm.gas_used,
        )
        return result

    # -- queries --

    def get_contract_state(self, contract_address: str) -> dict[str, Any]:
        """Return the full state of a contract.

        Returns ``{code_hex, state, owner, balance}`` or an error dict.
        """
        if contract_address not in self._contracts:
            return {"error": "Contract not found"}
        c = self._contracts[contract_address]
        return {
            "code_hex": c["code"].hex(),
            "state": dict(c["state"]),
            "owner": c["owner"],
            "balance": c["balance"],
        }

    def get_contract_balance(self, contract_address: str) -> int:
        """Return the BAIT balance of a contract (0 if not found)."""
        if contract_address not in self._contracts:
            return 0
        return self._contracts[contract_address]["balance"]  # type: ignore[return-value]

    # -- validation --

    @staticmethod
    def validate_contract_code(code_hex: str) -> bool:
        """Validate contract bytecode.

        Checks:
        1. Valid hex encoding.
        2. Size within ``MAX_CONTRACT_SIZE``.
        3. All opcodes are recognised (no "dangerous" unknown opcodes).
        """
        try:
            code = bytes.fromhex(code_hex)
        except ValueError:
            logger.warning("validate_contract_code: invalid hex")
            return False

        if len(code) == 0 or len(code) > MAX_CONTRACT_SIZE:
            logger.warning(
                "validate_contract_code: size %d out of range", len(code)
            )
            return False

        # Determine where the instruction body starts.
        # If the bytecode begins with a dispatch table (2-byte N header
        # followed by N × 6 bytes of entries), skip it.
        body_start = 0
        if len(code) >= 2:
            n_entries = struct.unpack(">H", code[0:2])[0]
            if 0 < n_entries <= 256:
                table_end = 2 + n_entries * 6
                if len(code) >= table_end:
                    body_start = table_end

        # Scan for unknown opcodes in the instruction body
        i = body_start
        while i < len(code):
            op = code[i]
            if op not in _GAS_COSTS:
                logger.warning(
                    "validate_contract_code: unknown opcode 0x%02X at offset %d",
                    op,
                    i,
                )
                return False
            # Advance past operand bytes
            if op == OpCode.PUSH:
                i += 5  # opcode + 4 bytes
            elif op in (OpCode.JUMP, OpCode.JUMPI):
                i += 3  # opcode + 2 bytes
            else:
                i += 1

        return True

    # -- introspection --

    def list_contracts(self) -> list[str]:
        """Return all deployed contract addresses."""
        return list(self._contracts.keys())

    def contract_exists(self, contract_address: str) -> bool:
        """Check whether a contract is deployed at the given address."""
        return contract_address in self._contracts
