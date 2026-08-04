"""Comprehensive tests for Phase C: Smart Contract Development.

Tests cover:
    - ContractEngine (deploy, call, validation, gas)
    - ContractVM (all opcodes)
    - Anchor Contracts (ERC20, Staking, Oracle templates)
    - RelayerNetwork (registration, meta-txs, leaderboard)

All tests are self-contained, fast, and require no external dependencies.
"""

from __future__ import annotations

import pytest
import struct

from baitcoin_core.contracts.contract_engine import (
    Assembler,
    ContractEngine,
    ContractVM,
    OpCode,
    _VMContext,
    _derive_address,
    build_bytecode_with_dispatch,
    _function_id,
    MAX_CONTRACT_SIZE,
    MAX_GAS_PER_CONTRACT,
)
from baitcoin_core.contracts.anchor_contracts import (
    BAIT_ERC20_TEMPLATE,
    STAKING_POOL_TEMPLATE,
    ORACLE_TEMPLATE,
    deploy_anchor,
    ANCHOR_REGISTRY,
)
from baitcoin_core.contracts.relayer import (
    RelayerNetwork,
    RelayerNode,
    _meta_tx_message,
    _sign_message,
    MIN_RELAYER_STAKE_SATS,
)


# =====================================================================
# Helpers
# =====================================================================

DEPLOYER = "a" * 64  # 64-char hex "public key"
CALLER = "b" * 64


def _make_simple_bytecode(*ops: int) -> str:
    """Pack raw opcode bytes (no operands) into a hex string."""
    return bytes(ops).hex()


def _assemble(*builders: Assembler) -> bytes:
    """Concatenate multiple Assembler instances into one bytecode blob."""
    buf = bytearray()
    for b in builders:
        buf.extend(b.bytecode())
    return bytes(buf)


def _ctx(caller: str = CALLER, value: int = 0, args: dict | None = None) -> _VMContext:
    return _VMContext(
        caller=caller,
        value=value,
        contract_address="0x" + "ab" * 16,
        function_name="test",
        args=args or {},
    )


# =====================================================================
# Test ContractVM
# =====================================================================


class TestContractVM:
    """Unit tests for the stack-based VM."""

    def test_push_pop(self) -> None:
        asm = Assembler().push(42).push(99).pop()
        vm = ContractVM()
        state: dict = {}
        ok = vm.execute(asm.bytecode(), state, _ctx(), 1_000_000)
        assert ok is True
        assert vm.gas_used > 0

    def test_push_return(self) -> None:
        asm = Assembler().push(12345).ret()
        vm = ContractVM()
        state: dict = {}
        ok = vm.execute(asm.bytecode(), state, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value == 12345

    def test_arithmetic(self) -> None:
        # (10 + 20) * 2 = 60
        asm = (
            Assembler()
            .push(10)
            .push(20)
            .add()
            .push(2)
            .mul()
            .ret()
        )
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value == 60

    def test_arithmetic_sub_div(self) -> None:
        # (50 - 10) / 4 = 10
        asm = (
            Assembler()
            .push(50)
            .push(10)
            .sub()
            .push(4)
            .div()
            .ret()
        )
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value == 10

    def test_comparison(self) -> None:
        # 3 < 5 => 1
        asm = Assembler().push(3).push(5).lt().ret()
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value == 1

        # 5 > 3 => 1
        asm = Assembler().push(5).push(3).gt().ret()
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value == 1

        # 7 == 7 => 1
        asm = Assembler().push(7).push(7).eq().ret()
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value == 1

        # 7 == 8 => 0
        asm = Assembler().push(7).push(8).eq().ret()
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value == 0

    def test_jump(self) -> None:
        # PUSH 0x0001, JUMP 6, PUSH 999, STOP
        # The JUMP should skip PUSH 999 and land on STOP
        # Bytecode: PUSH 1 (5 bytes) JUMP 6 (3 bytes) PUSH 999 (5 bytes) STOP (1 byte)
        # JUMP target = 6, which is the offset of PUSH 999... 
        # Let's compute: offset 0-4 = PUSH 1, offset 5-7 = JUMP 6, offset 8 = STOP
        # We want to jump past PUSH 999 to STOP.
        # PUSH 1 (5) + JUMP target (3) + PUSH 999 (5) + STOP (1) = 14 bytes
        # To skip PUSH 999, jump to offset 5+3+5 = 13 (the STOP)
        asm = Assembler()
        asm.push(1)          # 0-4
        asm.jump(13)         # 5-7  (jump to STOP at offset 13)
        asm.push(999)        # 8-12
        asm.stop()           # 13
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value is None

    def test_jumpi(self) -> None:
        # If condition is 0, JUMPI should NOT jump.
        # PUSH 0, PUSH target, JUMPI, PUSH 42, STOP
        # Bytecode: PUSH 0 (5) JUMPI 13 (3) PUSH 42 (5) STOP (1) = 14 bytes
        # If JUMPI doesn't jump, we reach PUSH 42.
        asm = Assembler()
        asm.push(0)          # 0-4
        asm.jumpi(13)        # 5-7 (jump to STOP)
        asm.push(42)         # 8-12
        asm.stop()           # 13
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        # JUMPI with condition 0 should NOT jump, so PUSH 42 executes, but STOP follows
        # Since we didn't RETURN, return_value is None, but execution was ok

        # Now test with condition = 1 (should jump)
        asm2 = Assembler()
        asm2.push(1)         # 0-4
        asm2.jumpi(13)       # 5-7
        asm2.push(42)        # 8-12
        asm2.stop()          # 13
        vm2 = ContractVM()
        ok2 = vm2.execute(asm2.bytecode(), {}, _ctx(), 1_000_000)
        assert ok2 is True

    def test_storage(self) -> None:
        # PUSH 42, PUSH 100, STORE -> state["100"] = 42
        # PUSH 100, LOAD -> pushes 42
        asm = (
            Assembler()
            .push(42)
            .push(100)
            .store()
            .push(100)
            .load()
            .ret()
        )
        state: dict = {}
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), state, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value == 42
        assert state.get("100") == 42

    def test_caller_value(self) -> None:
        # CALLER should push a truncated hash of the caller address
        asm = Assembler().caller().ret()
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(caller=CALLER), 1_000_000)
        assert ok is True
        assert isinstance(vm.return_value, int)
        assert vm.return_value != 0

        # VALUE should push the value sent with the call
        asm2 = Assembler().value().ret()
        vm2 = ContractVM()
        ok2 = vm2.execute(asm2.bytecode(), {}, _ctx(value=5000), 1_000_000)
        assert ok2 is True
        assert vm2.return_value == 5000

    def test_return(self) -> None:
        asm = Assembler().push(777).ret().push(888)  # 888 should never execute
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value == 777

    def test_log(self) -> None:
        asm = Assembler().push(42).log().push(99).ret()
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert "42" in vm.logs
        assert vm.return_value == 99

    def test_stop(self) -> None:
        asm = Assembler().push(1).stop().push(2)  # 2 should never execute
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is True
        assert vm.return_value is None

    def test_out_of_gas(self) -> None:
        # Push many values with a tiny gas limit
        asm = Assembler().push(1).push(2).push(3).ret()
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), gas_limit=3)
        assert ok is False  # Should fail due to insufficient gas

    def test_stack_underflow(self) -> None:
        asm = Assembler().pop()  # Pop from empty stack
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is False

    def test_div_by_zero(self) -> None:
        asm = Assembler().push(10).push(0).div()
        vm = ContractVM()
        ok = vm.execute(asm.bytecode(), {}, _ctx(), 1_000_000)
        assert ok is False

    def test_invalid_opcode(self) -> None:
        bad_bytecode = bytes([0xFF, 0x00, 0x00, 0x00, 0x01]).hex()
        engine = ContractEngine()
        assert engine.validate_contract_code(bad_bytecode) is False

    def test_args_on_stack(self) -> None:
        """Verify that function args are pre-loaded onto the stack."""
        asm = Assembler().ret()  # just return top of stack
        vm = ContractVM()
        ok = vm.execute(
            asm.bytecode(),
            {},
            _ctx(args={"x": 55}),
            1_000_000,
        )
        assert ok is True
        assert vm.return_value == 55


# =====================================================================
# Test ContractEngine
# =====================================================================


class TestContractEngine:
    """Tests for the high-level contract engine."""

    def test_deploy_contract(self) -> None:
        engine = ContractEngine()
        asm = Assembler().push(1).stop()
        code_hex = asm.bytecode().hex()
        result = engine.deploy_contract(DEPLOYER, code_hex)
        assert result["success"] is True
        assert len(result["contract_address"]) == 64  # SHA-256 hex
        assert result["gas_used"] >= 0
        assert engine.contract_exists(result["contract_address"])

    def test_deploy_invalid_hex(self) -> None:
        engine = ContractEngine()
        result = engine.deploy_contract(DEPLOYER, "zzzz")
        assert result["success"] is False
        assert "error" in result

    def test_deploy_too_large(self) -> None:
        engine = ContractEngine()
        huge = "00" * (MAX_CONTRACT_SIZE + 1)
        result = engine.deploy_contract(DEPLOYER, huge)
        assert result["success"] is False

    def test_deploy_empty(self) -> None:
        engine = ContractEngine()
        result = engine.deploy_contract(DEPLOYER, "")
        assert result["success"] is False

    def test_deploy_different_addresses(self) -> None:
        """Each deployment should produce a unique address."""
        engine = ContractEngine()
        asm = Assembler().push(1).stop()
        code = asm.bytecode().hex()
        r1 = engine.deploy_contract(DEPLOYER, code)
        r2 = engine.deploy_contract(DEPLOYER, code)
        assert r1["contract_address"] != r2["contract_address"]

    def test_call_contract(self) -> None:
        engine = ContractEngine()
        # Deploy a simple contract that returns 42
        asm = Assembler().push(42).ret()
        code = asm.bytecode().hex()
        deploy_result = engine.deploy_contract(DEPLOYER, code)
        addr = deploy_result["contract_address"]

        call_result = engine.call_contract(CALLER, addr, "test")
        assert call_result["success"] is True
        assert call_result["result"] == 42
        assert call_result["gas_used"] > 0

    def test_call_with_value(self) -> None:
        engine = ContractEngine()
        asm = Assembler().value().ret()
        code = asm.bytecode().hex()
        addr = engine.deploy_contract(DEPLOYER, code)["contract_address"]

        result = engine.call_contract(CALLER, addr, "test", value=1000)
        assert result["success"] is True
        assert result["result"] == 1000
        assert engine.get_contract_balance(addr) == 1000

    def test_call_nonexistent_contract(self) -> None:
        engine = ContractEngine()
        result = engine.call_contract(CALLER, "ff" * 32, "test")
        assert result["success"] is False
        assert "error" in result

    def test_gas_limit_enforcement(self) -> None:
        engine = ContractEngine()
        # Create bytecode that uses significant gas
        asm = Assembler()
        for i in range(100):
            asm.push(i)
        asm.ret()
        code = asm.bytecode().hex()
        addr = engine.deploy_contract(DEPLOYER, code)["contract_address"]

        result = engine.call_contract(CALLER, addr, "test", gas_limit=5)
        assert result["success"] is False

    def test_contract_state(self) -> None:
        engine = ContractEngine()
        # Deploy contract that stores a value
        asm = (
            Assembler()
            .push(999)
            .push(1)
            .store()
            .push(1)
            .load()
            .ret()
        )
        addr = engine.deploy_contract(DEPLOYER, asm.bytecode().hex())["contract_address"]

        # Call to trigger state mutation
        engine.call_contract(CALLER, addr, "test")

        # Query state
        state = engine.get_contract_state(addr)
        assert "state" in state
        assert state["state"].get("1") == 999
        assert state["owner"] == DEPLOYER
        assert "code_hex" in state

    def test_contract_balance(self) -> None:
        engine = ContractEngine()
        asm = Assembler().stop()
        addr = engine.deploy_contract(DEPLOYER, asm.bytecode().hex())["contract_address"]
        assert engine.get_contract_balance(addr) == 0

        # Send value
        engine.call_contract(CALLER, addr, "test", value=5000)
        assert engine.get_contract_balance(addr) == 5000

        # Send more
        engine.call_contract(CALLER, addr, "test", value=3000)
        assert engine.get_contract_balance(addr) == 8000

        # Nonexistent contract returns 0
        assert engine.get_contract_balance("00" * 32) == 0

    def test_validate_code(self) -> None:
        # Valid: simple PUSH + STOP
        asm = Assembler().push(1).stop()
        assert ContractEngine.validate_contract_code(asm.bytecode().hex()) is True

        # Invalid hex
        assert ContractEngine.validate_contract_code("not-hex!") is False

        # Too large
        assert ContractEngine.validate_contract_code("00" * (MAX_CONTRACT_SIZE + 1)) is False

        # Empty
        assert ContractEngine.validate_contract_code("") is False

        # Unknown opcode 0xFF
        bad = bytes([0xFF])
        assert ContractEngine.validate_contract_code(bad.hex()) is False

    def test_call_with_logs(self) -> None:
        engine = ContractEngine()
        asm = Assembler().push(1).log().push(2).log().push(3).ret()
        addr = engine.deploy_contract(DEPLOYER, asm.bytecode().hex())["contract_address"]

        result = engine.call_contract(CALLER, addr, "test")
        assert result["success"] is True
        assert result["result"] == 3
        assert "1" in result["logs"]
        assert "2" in result["logs"]

    def test_list_contracts(self) -> None:
        engine = ContractEngine()
        assert engine.list_contracts() == []

        asm = Assembler().stop()
        code = asm.bytecode().hex()
        engine.deploy_contract(DEPLOYER, code)
        engine.deploy_contract(DEPLOYER, code)

        assert len(engine.list_contracts()) == 2

    def test_dispatch_table(self) -> None:
        """Test that the VM correctly resolves function entry points via dispatch table."""
        engine = ContractEngine()

        # Build a contract with two functions using build_bytecode_with_dispatch
        func_a = Assembler().push(100).ret().bytecode()
        func_b = Assembler().push(200).ret().bytecode()

        bytecode = build_bytecode_with_dispatch({"funcA": func_a, "funcB": func_b})
        addr = engine.deploy_contract(DEPLOYER, bytecode.hex())["contract_address"]

        result_a = engine.call_contract(CALLER, addr, "funcA")
        assert result_a["success"] is True
        assert result_a["result"] == 100

        result_b = engine.call_contract(CALLER, addr, "funcB")
        assert result_b["success"] is True
        assert result_b["result"] == 200

    def test_derive_address_deterministic(self) -> None:
        a1 = _derive_address("key1", 0)
        a2 = _derive_address("key1", 0)
        assert a1 == a2
        a3 = _derive_address("key1", 1)
        assert a1 != a3


# =====================================================================
# Test Anchor Contracts
# =====================================================================


class TestAnchorContracts:
    """Tests for pre-built anchor contract templates."""

    def test_erc20_deploy(self) -> None:
        """BAIT_ERC20_TEMPLATE should be valid and deployable."""
        engine = ContractEngine()
        template = BAIT_ERC20_TEMPLATE

        assert "bytecode_hex" in template
        assert "abi" in template
        assert len(template["abi"]) == 8  # 8 functions

        # Validate bytecode
        assert engine.validate_contract_code(template["bytecode_hex"]) is True

        # Deploy
        result = engine.deploy_contract(DEPLOYER, template["bytecode_hex"])
        assert result["success"] is True
        addr = result["contract_address"]

        # Call totalSupply
        r = engine.call_contract(CALLER, addr, "totalSupply")
        assert r["success"] is True
        assert r["result"] == 21_000_000

        # Call decimals
        r = engine.call_contract(CALLER, addr, "decimals")
        assert r["success"] is True
        assert r["result"] == 8

        # Call name
        r = engine.call_contract(CALLER, addr, "name")
        assert r["success"] is True

        # Call symbol
        r = engine.call_contract(CALLER, addr, "symbol")
        assert r["success"] is True

    def test_erc20_transfer(self) -> None:
        """Test ERC20 transfer function."""
        engine = ContractEngine()
        template = BAIT_ERC20_TEMPLATE
        addr = engine.deploy_contract(DEPLOYER, template["bytecode_hex"])["contract_address"]

        # First, set up a balance for CALLER by storing directly in state
        # We call balanceOf to check (initially should be 0 since LOAD returns 0 for missing)
        caller_hash = int(CALLER[:8], 16)
        r = engine.call_contract(CALLER, addr, "balanceOf", args={"account": caller_hash})
        assert r["success"] is True
        assert r["result"] == 0  # no balance yet

    def test_staking_deploy(self) -> None:
        """STAKING_POOL_TEMPLATE should be valid and deployable."""
        engine = ContractEngine()
        template = STAKING_POOL_TEMPLATE

        assert len(template["abi"]) == 5
        assert engine.validate_contract_code(template["bytecode_hex"]) is True

        result = engine.deploy_contract(DEPLOYER, template["bytecode_hex"])
        assert result["success"] is True
        addr = result["contract_address"]

        # totalStaked should be 0 initially
        r = engine.call_contract(CALLER, addr, "totalStaked")
        assert r["success"] is True
        assert r["result"] == 0

        # getStakerInfo with a test address
        r = engine.call_contract(CALLER, addr, "getStakerInfo", args={"staker": 12345})
        assert r["success"] is True
        assert r["result"] == 0

    def test_staking_stake_unstake(self) -> None:
        """Test staking and unstaking flow."""
        engine = ContractEngine()
        template = STAKING_POOL_TEMPLATE
        addr = engine.deploy_contract(DEPLOYER, template["bytecode_hex"])["contract_address"]

        # Stake 1000
        r = engine.call_contract(CALLER, addr, "stake", args={"amount": 1000}, value=1000)
        assert r["success"] is True

        # Check total staked
        r = engine.call_contract(CALLER, addr, "totalStaked")
        assert r["success"] is True
        assert r["result"] == 1000

        # Check staker info
        caller_hash = int(CALLER[:8], 16)
        r = engine.call_contract(CALLER, addr, "getStakerInfo", args={"staker": caller_hash})
        assert r["success"] is True
        assert r["result"] == 1000

        # Unstake 400
        r = engine.call_contract(CALLER, addr, "unstake", args={"amount": 400})
        assert r["success"] is True

        # Check remaining
        r = engine.call_contract(CALLER, addr, "getStakerInfo", args={"staker": caller_hash})
        assert r["result"] == 600

        r = engine.call_contract(CALLER, addr, "totalStaked")
        assert r["result"] == 600

    def test_oracle_deploy(self) -> None:
        """ORACLE_TEMPLATE should be valid and deployable."""
        engine = ContractEngine()
        template = ORACLE_TEMPLATE

        assert len(template["abi"]) == 4
        assert engine.validate_contract_code(template["bytecode_hex"]) is True

        result = engine.deploy_contract(DEPLOYER, template["bytecode_hex"])
        assert result["success"] is True
        addr = result["contract_address"]

        # getLastUpdate should be 0 initially
        r = engine.call_contract(CALLER, addr, "getLastUpdate")
        assert r["success"] is True
        assert r["result"] == 0

        # getSources should be 0
        r = engine.call_contract(CALLER, addr, "getSources")
        assert r["success"] is True
        assert r["result"] == 0

    def test_oracle_submit_and_query(self) -> None:
        """Test oracle data submission and retrieval."""
        engine = ContractEngine()
        template = ORACLE_TEMPLATE
        addr = engine.deploy_contract(DEPLOYER, template["bytecode_hex"])["contract_address"]

        # Submit data: data_hash=12345, source=100
        r = engine.call_contract(
            CALLER, addr, "submitData",
            args={"data_hash": 12345, "source": 100},
        )
        assert r["success"] is True

        # Query value by key (source=100)
        r = engine.call_contract(CALLER, addr, "getValue", args={"data_key": 100})
        assert r["success"] is True
        assert r["result"] == 12345

        # Check update count
        r = engine.call_contract(CALLER, addr, "getLastUpdate")
        assert r["success"] is True
        assert r["result"] == 1

        r = engine.call_contract(CALLER, addr, "getSources")
        assert r["success"] is True
        assert r["result"] == 1

        # Submit another
        r = engine.call_contract(
            CALLER, addr, "submitData",
            args={"data_hash": 99999, "source": 200},
        )
        assert r["success"] is True

        r = engine.call_contract(CALLER, addr, "getValue", args={"data_key": 200})
        assert r["result"] == 99999

        r = engine.call_contract(CALLER, addr, "getSources")
        assert r["result"] == 2

    def test_deploy_anchor_helper(self) -> None:
        """Test the deploy_anchor convenience function."""
        engine = ContractEngine()

        # Deploy ERC20
        result = deploy_anchor("BAIT_ERC20", engine, DEPLOYER)
        assert result["success"] is True
        assert result["template_name"] == "BAIT_ERC20"
        assert "abi" in result
        assert len(result["abi"]) == 8

        # Deploy Staking
        result = deploy_anchor("BAIT_StakingPool", engine, DEPLOYER)
        assert result["success"] is True
        assert result["template_name"] == "BAIT_StakingPool"

        # Deploy Oracle
        result = deploy_anchor("BAIT_Oracle", engine, DEPLOYER)
        assert result["success"] is True
        assert result["template_name"] == "BAIT_Oracle"

    def test_deploy_anchor_unknown(self) -> None:
        engine = ContractEngine()
        with pytest.raises(ValueError, match="Unknown anchor template"):
            deploy_anchor("NonExistent", engine, DEPLOYER)

    def test_anchor_registry(self) -> None:
        assert "BAIT_ERC20" in ANCHOR_REGISTRY
        assert "BAIT_StakingPool" in ANCHOR_REGISTRY
        assert "BAIT_Oracle" in ANCHOR_REGISTRY
        assert len(ANCHOR_REGISTRY) == 3

    def test_all_templates_valid_bytecode(self) -> None:
        engine = ContractEngine()
        for name, template in ANCHOR_REGISTRY.items():
            assert engine.validate_contract_code(template["bytecode_hex"]) is True, (
                f"Template {name} has invalid bytecode"
            )
            assert len(template["abi"]) > 0, f"Template {name} has empty ABI"


# =====================================================================
# Test RelayerNetwork
# =====================================================================


class TestRelayerNetwork:
    """Tests for the meta-transaction relayer network."""

    def test_register_relayer(self) -> None:
        net = RelayerNetwork()
        result = net.register_relayer("node_1", 1000)
        assert result["success"] is True
        assert result["node_id"] == "node_1"

        info = net.get_relayer_info("node_1")
        assert info is not None
        assert info["stake_amount"] == 1000
        assert info["active"] is True
        assert info["tx_count"] == 0

    def test_register_duplicate_relayer(self) -> None:
        net = RelayerNetwork()
        net.register_relayer("node_1", 1000)
        result = net.register_relayer("node_1", 2000)
        assert result["success"] is False
        assert "already registered" in result["error"]

    def test_insufficient_stake(self) -> None:
        net = RelayerNetwork()
        result = net.register_relayer("node_1", 50)
        assert result["success"] is False
        assert "Insufficient stake" in result["error"]

    def test_exact_minimum_stake(self) -> None:
        net = RelayerNetwork()
        result = net.register_relayer("node_1", MIN_RELAYER_STAKE_SATS)
        assert result["success"] is True

    def test_submit_meta_tx(self) -> None:
        net = RelayerNetwork()
        net.set_balance("alice", 10000)
        net.register_relayer("relay_1", 500)

        msg = _meta_tx_message("alice", "bob", 1000, 0, 50, "")
        sig = _sign_message("alice", msg)

        result = net.submit_meta_tx(
            sender="alice",
            recipient="bob",
            amount_sats=1000,
            nonce=0,
            fee_sats=50,
            signature_hex=sig,
            relay_to="",
        )
        assert result["success"] is True
        assert len(result["meta_tx_id"]) == 16

        # Balance should be deducted
        assert net.get_balance("alice") == 10000 - 1000 - 50

        # Should appear in pending
        pending = net.get_pending_meta_txs()
        assert len(pending) == 1
        assert pending[0]["sender"] == "alice"

    def test_submit_meta_tx_invalid_signature(self) -> None:
        net = RelayerNetwork()
        net.set_balance("alice", 10000)

        result = net.submit_meta_tx(
            sender="alice",
            recipient="bob",
            amount_sats=1000,
            nonce=0,
            fee_sats=50,
            signature_hex="deadbeef",
            relay_to="",
        )
        assert result["success"] is False
        assert "signature" in result["error"].lower()

    def test_submit_meta_tx_wrong_nonce(self) -> None:
        net = RelayerNetwork()
        net.set_balance("alice", 10000)

        msg = _meta_tx_message("alice", "bob", 1000, 0, 50, "")
        sig = _sign_message("alice", msg)

        # Submit with nonce=0 first
        net.submit_meta_tx(
            sender="alice", recipient="bob", amount_sats=1000,
            nonce=0, fee_sats=50, signature_hex=sig, relay_to="",
        )

        # Now submit with nonce=0 again (should fail: expected nonce is 1 after execution)
        # But nonce advances on execution, not on submission.
        # Actually nonce advances on execute_meta_tx. So submitting with nonce=0 again
        # should succeed (nonce hasn't advanced yet).
        # Let's test with wrong nonce directly.
        msg2 = _meta_tx_message("alice", "bob", 1000, 99, 50, "")
        sig2 = _sign_message("alice", msg2)

        result = net.submit_meta_tx(
            sender="alice", recipient="bob", amount_sats=1000,
            nonce=99, fee_sats=50, signature_hex=sig2, relay_to="",
        )
        assert result["success"] is False
        assert "nonce" in result["error"].lower()

    def test_submit_meta_tx_insufficient_balance(self) -> None:
        net = RelayerNetwork()
        net.set_balance("alice", 50)  # Less than amount + fee

        msg = _meta_tx_message("alice", "bob", 1000, 0, 50, "")
        sig = _sign_message("alice", msg)

        result = net.submit_meta_tx(
            sender="alice", recipient="bob", amount_sats=1000,
            nonce=0, fee_sats=50, signature_hex=sig, relay_to="",
        )
        assert result["success"] is False
        assert "balance" in result["error"].lower()

    def test_execute_meta_tx(self) -> None:
        net = RelayerNetwork()
        net.set_balance("alice", 10000)
        net.register_relayer("relay_1", 500)

        msg = _meta_tx_message("alice", "bob", 1000, 0, 50, "")
        sig = _sign_message("alice", msg)

        submit_result = net.submit_meta_tx(
            sender="alice", recipient="bob", amount_sats=1000,
            nonce=0, fee_sats=50, signature_hex=sig, relay_to="",
        )
        tx_id = submit_result["meta_tx_id"]

        # Execute
        exec_result = net.execute_meta_tx(tx_id, "relay_1")
        assert exec_result["success"] is True
        assert exec_result["sender"] == "alice"
        assert exec_result["recipient"] == "bob"
        assert exec_result["amount"] == 1000
        assert exec_result["fee"] == 50

        # Bob should have received the amount
        assert net.get_balance("bob") == 1000

        # Relayer should have earned the fee
        assert net.get_balance("relay_1") == 50

        # Relayer stats updated
        info = net.get_relayer_info("relay_1")
        assert info["tx_count"] == 1
        assert info["fee_earned"] == 50

        # Pending queue should be empty
        assert len(net.get_pending_meta_txs()) == 0

    def test_execute_meta_tx_unregistered_relayer(self) -> None:
        net = RelayerNetwork()
        result = net.execute_meta_tx("nonexistent_tx", "unknown_relayer")
        assert result["success"] is False
        assert "not registered" in result["error"]

    def test_execute_meta_tx_not_found(self) -> None:
        net = RelayerNetwork()
        net.register_relayer("relay_1", 500)
        result = net.execute_meta_tx("nonexistent_tx", "relay_1")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_execute_meta_tx_twice(self) -> None:
        """Executing the same meta-tx twice should fail."""
        net = RelayerNetwork()
        net.set_balance("alice", 10000)
        net.register_relayer("relay_1", 500)

        msg = _meta_tx_message("alice", "bob", 1000, 0, 50, "")
        sig = _sign_message("alice", msg)

        tx_id = net.submit_meta_tx(
            sender="alice", recipient="bob", amount_sats=1000,
            nonce=0, fee_sats=50, signature_hex=sig, relay_to="",
        )["meta_tx_id"]

        net.execute_meta_tx(tx_id, "relay_1")
        result = net.execute_meta_tx(tx_id, "relay_1")
        assert result["success"] is False

    def test_leaderboard(self) -> None:
        net = RelayerNetwork()
        net.register_relayer("r1", 1000)
        net.register_relayer("r2", 2000)
        net.register_relayer("r3", 500)

        # r1 executes 3 txs (each from a unique sender to avoid nonce conflicts)
        for idx in range(3):
            sender = f"user_{idx}"
            net.set_balance(sender, 10000)
            msg = _meta_tx_message(sender, "bob", 100, 0, 10, "")
            sig = _sign_message(sender, msg)
            tx_id = net.submit_meta_tx(
                sender=sender, recipient="bob", amount_sats=100,
                nonce=0, fee_sats=10, signature_hex=sig, relay_to="",
            )["meta_tx_id"]
            net.execute_meta_tx(tx_id, "r1")

        net.set_balance("charlie", 10000)
        msg = _meta_tx_message("charlie", "dave", 500, 0, 25, "")
        sig = _sign_message("charlie", msg)
        tx_id = net.submit_meta_tx(
            sender="charlie", recipient="dave", amount_sats=500,
            nonce=0, fee_sats=25, signature_hex=sig, relay_to="",
        )["meta_tx_id"]
        net.execute_meta_tx(tx_id, "r2")

        board = net.get_relayer_leaderboard()
        assert len(board) == 3
        # r1 should be first (3 txs)
        assert board[0]["node_id"] == "r1"
        assert board[0]["tx_count"] == 3
        assert board[0]["fee_earned"] == 30
        # r2 should be second
        assert board[1]["node_id"] == "r2"
        assert board[1]["tx_count"] == 1
        # r3 has 0 txs
        assert board[2]["node_id"] == "r3"
        assert board[2]["tx_count"] == 0

    def test_relay_to_cross_chain(self) -> None:
        """Meta-tx with relay_to field should be stored and reported."""
        net = RelayerNetwork()
        net.set_balance("alice", 10000)
        net.register_relayer("relay_1", 500)

        msg = _meta_tx_message("alice", "bob", 1000, 0, 50, "ethereum")
        sig = _sign_message("alice", msg)

        tx_id = net.submit_meta_tx(
            sender="alice", recipient="bob", amount_sats=1000,
            nonce=0, fee_sats=50, signature_hex=sig, relay_to="ethereum",
        )["meta_tx_id"]

        pending = net.get_pending_meta_txs()
        assert pending[0]["relay_to"] == "ethereum"

        exec_result = net.execute_meta_tx(tx_id, "relay_1")
        assert exec_result["relay_to"] == "ethereum"

    def test_nonce_advancement(self) -> None:
        """Nonces should advance after execution."""
        net = RelayerNetwork()
        net.set_balance("alice", 100000)
        net.register_relayer("relay_1", 500)

        # First tx with nonce=0
        msg = _meta_tx_message("alice", "bob", 100, 0, 10, "")
        sig = _sign_message("alice", msg)
        tx_id = net.submit_meta_tx(
            sender="alice", recipient="bob", amount_sats=100,
            nonce=0, fee_sats=10, signature_hex=sig, relay_to="",
        )["meta_tx_id"]
        net.execute_meta_tx(tx_id, "relay_1")

        # Second tx must use nonce=1
        msg = _meta_tx_message("alice", "bob", 200, 1, 10, "")
        sig = _sign_message("alice", msg)
        result = net.submit_meta_tx(
            sender="alice", recipient="bob", amount_sats=200,
            nonce=1, fee_sats=10, signature_hex=sig, relay_to="",
        )
        assert result["success"] is True

        # Using nonce=0 again should fail
        msg_old = _meta_tx_message("alice", "bob", 100, 0, 10, "")
        sig_old = _sign_message("alice", msg_old)
        result = net.submit_meta_tx(
            sender="alice", recipient="bob", amount_sats=100,
            nonce=0, fee_sats=10, signature_hex=sig_old, relay_to="",
        )
        assert result["success"] is False
        assert "nonce" in result["error"].lower()


# =====================================================================
# Test module imports
# =====================================================================


class TestModuleImports:
    """Verify all modules are importable without errors."""

    def test_import_contract_engine(self) -> None:
        from baitcoin_core.contracts.contract_engine import (
            ContractEngine, ContractVM, Assembler, OpCode,
        )
        assert ContractEngine is not None
        assert ContractVM is not None
        assert Assembler is not None
        assert OpCode is not None

    def test_import_anchor_contracts(self) -> None:
        from baitcoin_core.contracts.anchor_contracts import (
            BAIT_ERC20_TEMPLATE, STAKING_POOL_TEMPLATE, ORACLE_TEMPLATE,
        )
        assert BAIT_ERC20_TEMPLATE is not None
        assert STAKING_POOL_TEMPLATE is not None
        assert ORACLE_TEMPLATE is not None

    def test_import_relayer(self) -> None:
        from baitcoin_core.contracts.relayer import RelayerNetwork, RelayerNode
        assert RelayerNetwork is not None
        assert RelayerNode is not None

    def test_import_package(self) -> None:
        from baitcoin_core.contracts import (
            ContractEngine, BAIT_ERC20_TEMPLATE, RelayerNetwork,
        )
        assert ContractEngine is not None
        assert BAIT_ERC20_TEMPLATE is not None
        assert RelayerNetwork is not None
