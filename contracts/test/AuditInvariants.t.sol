// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/BAITBridge.sol";
import "../src/FoundersVesting.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "../src/TimelockPauseWrapper.sol";

/**
 * @title AuditInvariants
 * @notice Tests para os invariantes identificados na auditoria PhD 2026-09-22:
 *   1. totalMinted <= totalLocked (Bridge)
 *   2. Replay protection EIP-712 (nonce + processedHashes)
 *   3. Circuit breaker (daily limit + pause)
 *   4. AccessControl em vez de Ownable puro
 *   5. FoundersVesting: cliff + linear + apenas owner
 *   6. TimelockPauseWrapper: 48h delay obrigatório
 */
contract AuditInvariants is Test {
    BAITBridge public bridge;
    MockBAIT public bait;

    // Chaves privadas reais (secp256k1 válidas)
    uint256 internal constant ADMIN_KEY   = 0xA11CE;
    uint256 internal constant PAUSER_KEY  = 0xB0B;
    uint256 internal constant RELAYER_KEY = 0xCAFE;
    uint256 internal constant ALICE_KEY   = 0xD00D;
    uint256 internal constant BOB_KEY     = 0xBEEF;
    uint256 internal constant DEAD_KEY    = 0xDEAD;

    address public admin;
    address public pauser;
    address public relayer;
    address public alice;
    address public bob;

    uint256 public constant DAILY_LIMIT = 10_000_000 * 1e8; // 10M BAIT (lock+mint compartilham)

    function setUp() public {
        // Derivar endereços das chaves privadas (secp256k1 válidas)
        admin   = vm.addr(ADMIN_KEY);
        pauser  = vm.addr(PAUSER_KEY);
        relayer = vm.addr(RELAYER_KEY);
        alice   = vm.addr(ALICE_KEY);
        bob     = vm.addr(BOB_KEY);

        // Mock ERC20 simples p/ tests (não usamos WBAIT real p/ isolar BAITBridge)
        bait = new MockBAIT();
        // Mint 1B BAIT para o test contract (cobre locks de até 100M)
        bait.mint(address(this), 1_000_000_000 * 1e8);

        bridge = new BAITBridge(
            address(bait),
            DAILY_LIMIT,
            admin,
            relayer,
            pauser
        );
        bait.transfer(address(bridge), 500_000_000 * 1e8); // funding inicial da bridge
    }

    // ---------------------------------------------------------------
    // 1. Invariante: totalMinted <= totalLocked (CRITICAL)
    // ---------------------------------------------------------------
    function test_Invariant_MintCannotExceedLocked() public {
        uint256 amount = 1000 * 1e8;

        // Lock primeiro
        bait.approve(address(bridge), amount);
        bridge.lock(amount, 42);
        assertEq(bridge.totalLocked(), amount);

        // Mint OK (até o limite)
        bytes memory sig = _signUnlock(alice, amount, 0, 1);
        vm.prank(relayer);
        bridge.mint(alice, amount, 1, sig);
        assertEq(bridge.totalMinted(), amount);

        // Tentar mint SEM novo lock → deve reverter com InvariantViolation
        bytes memory sig2 = _signUnlock(bob, amount, 0, 1);
        vm.prank(relayer);
        vm.expectRevert(abi.encodeWithSelector(
            BAITBridge.InvariantViolation.selector, amount, amount * 2
        ));
        bridge.mint(bob, amount, 1, sig2);
    }

    function test_Invariant_HoldsUnderFuzz(uint256 lockAmt, uint256 mintAmt) public {
        // Lock + mint compartilham o daily limit
        uint256 max = DAILY_LIMIT / 2;
        lockAmt = bound(lockAmt, 1e8, max);
        mintAmt = bound(mintAmt, 1e8, max);
        vm.assume(mintAmt <= lockAmt); // só testa cenário válido

        bait.approve(address(bridge), lockAmt);
        bridge.lock(lockAmt, 1);
        bytes memory sig = _signUnlock(alice, mintAmt, 0, 1);
        vm.prank(relayer);
        bridge.mint(alice, mintAmt, 1, sig);

        (uint256 L, uint256 M, bool ok) = bridge.getInvariant();
        assertTrue(ok, "invariant violated");
        assertEq(L, lockAmt);
        assertEq(M, mintAmt);
    }

    // ---------------------------------------------------------------
    // 2. Replay protection EIP-712
    // ---------------------------------------------------------------
    function test_ReplayProtection_NonceIncrements() public {
        bait.approve(address(bridge), 1_000 * 1e8);
        bridge.lock(1_000 * 1e8, 1);

        bytes memory sig1 = _signUnlock(alice, 100 * 1e8, 0, 1);
        vm.prank(relayer);
        bridge.mint(alice, 100 * 1e8, 1, sig1);
        assertEq(bridge.userNonces(alice), 1);

        bytes memory sig2 = _signUnlock(alice, 100 * 1e8, 1, 1);
        vm.prank(relayer);
        bridge.mint(alice, 100 * 1e8, 1, sig2);
        assertEq(bridge.userNonces(alice), 2);
    }

    function test_ReplayProtection_SameMsgHashReverts() public {
        bait.approve(address(bridge), 1_000 * 1e8);
        bridge.lock(1_000 * 1e8, 1);

        bytes memory sig = _signUnlock(alice, 100 * 1e8, 0, 1);
        vm.prank(relayer);
        bridge.mint(alice, 100 * 1e8, 1, sig);

        // Tentar reusar a mesma signature (mesmo nonce 0, mesmo hash)
        // Vai falhar pois nonce do userNonces[alice] já é 1; mas se um attacker
        // tentar forçar reuse, o processedHashes previne.
        // Forçamos: rebuild a msg usando nonce 0 mas processedHashes já está setado.
        // Isso requer que o attacker saiba o nonce antigo — improvável, mas o teste cobre.
        // Para o teste: tentamos passar a mesma sig — deve reverter InvalidSignature
        // porque userNonces[alice]++ resulta em nonce=1 na próxima chamada, e a
        // msgHash computada é diferente (nonce=1 vs nonce=0).
        vm.prank(relayer);
        vm.expectRevert(BAITBridge.InvalidSignature.selector);
        bridge.mint(alice, 100 * 1e8, 1, sig);
    }

    function test_ReplayProtection_InvalidSigner() public {
        bait.approve(address(bridge), 1_000 * 1e8);
        bridge.lock(1_000 * 1e8, 1);

        // Assina com chave de alguém que NÃO tem RELAYER_ROLE
        bytes memory sig = _signUnlock(alice, 100 * 1e8, 0, 1, vm.addr(DEAD_KEY));
        vm.prank(relayer);
        vm.expectRevert(BAITBridge.InvalidSignature.selector);
        bridge.mint(alice, 100 * 1e8, 1, sig);
    }

    // ---------------------------------------------------------------
    // 3. Circuit breaker
    // ---------------------------------------------------------------
    function test_CircuitBreaker_DailyLimitReverts() public {
        // Day 1: lock DAILY_LIMIT * 2 (lock nao consome daily limit) e mint DAILY_LIMIT
        bait.approve(address(bridge), DAILY_LIMIT * 2);
        bridge.lock(DAILY_LIMIT * 2, 1);

        bytes memory sig1 = _signUnlock(alice, DAILY_LIMIT, 0, 1);
        vm.prank(relayer);
        bridge.mint(alice, DAILY_LIMIT, 1, sig1);

        // Mint +1 wei deve falhar (atingiu daily limit)
        bytes memory sig2 = _signUnlock(bob, 1, 0, 1);
        vm.prank(relayer);
        vm.expectRevert(abi.encodeWithSelector(
            BAITBridge.DailyLimitExceeded.selector, 1, 0
        ));
        bridge.mint(bob, 1, 1, sig2);
    }

    function test_CircuitBreaker_ResetsAfterOneDay() public {
        // Day 1: lock 3x daily limit, mint 1x
        bait.approve(address(bridge), DAILY_LIMIT * 3);
        bridge.lock(DAILY_LIMIT * 3, 1);

        bytes memory sig1 = _signUnlock(alice, DAILY_LIMIT, 0, 1);
        vm.prank(relayer);
        bridge.mint(alice, DAILY_LIMIT, 1, sig1);

        // Avança 1 dia — contador reseta
        vm.warp(block.timestamp + 1 days);

        bytes memory sig2 = _signUnlock(alice, DAILY_LIMIT, 1, 1);
        vm.prank(relayer);
        bridge.mint(alice, DAILY_LIMIT, 1, sig2);
        assertEq(bridge.totalMinted(), DAILY_LIMIT * 2);
    }

    function test_CircuitBreaker_PauseBlocksMint() public {
        bait.approve(address(bridge), 1_000 * 1e8);
        bridge.lock(1_000 * 1e8, 1);

        vm.prank(pauser);
        bridge.pause();
        assertTrue(bridge.paused());

        bytes memory sig = _signUnlock(alice, 100 * 1e8, 0, 1);
        vm.prank(relayer);
        vm.expectRevert(abi.encodeWithSelector(Pausable.EnforcedPause.selector));
        bridge.mint(alice, 100 * 1e8, 1, sig);
    }

    // ---------------------------------------------------------------
    // 4. AccessControl — pause requer PAUSER_ROLE
    // ---------------------------------------------------------------
    function test_AccessControl_RandomUserCannotPause() public {
        vm.prank(alice);
        vm.expectRevert();
        bridge.pause();
    }

    function test_AccessControl_OnlyAdminCanChangeLimit() public {
        vm.prank(alice);
        vm.expectRevert();
        bridge.setDailyVolumeLimit(500);
    }

    // ---------------------------------------------------------------
    // 5. FoundersVesting: cliff + linear
    // ---------------------------------------------------------------
    function test_Vesting_NoReleaseBeforeCliff() public {
        FoundersVesting vesting = _deployVesting();
        vm.prank(admin);
        vesting.addBeneficiary(alice, 1000 * 1e8, 30 days);

        vm.expectRevert(abi.encodeWithSelector(
            FoundersVesting.CliffNotReached.selector, block.timestamp + 30 days
        ));
        vm.prank(alice);
        vesting.release();
    }

    function test_Vesting_LinearReleaseAfterCliff() public {
        FoundersVesting vesting = _deployVesting();
        vm.prank(admin);
        vesting.addBeneficiary(alice, 1000 * 1e8, 30 days);

        // Fund the vesting contract BEFORE advance time
        bait.transfer(address(vesting), 1000 * 1e8);

        // Avança 30 dias (cliff) + metade da duracao (2 anos de 4)
        vm.warp(block.timestamp + 30 days + 730 days);

        uint256 releasable = vesting.releasableAmountOf(alice);
        // ~50% vested
        assertApproxEqRel(releasable, 500 * 1e8, 0.05e18); // 5% tolerance

        vm.prank(alice);
        vesting.release();
        assertEq(bait.balanceOf(alice), releasable);
    }

    function test_Vesting_FullReleaseAfterDuration() public {
        FoundersVesting vesting = _deployVesting();
        vm.prank(admin);
        vesting.addBeneficiary(alice, 1000 * 1e8, 0);

        vm.warp(block.timestamp + 4 * 365 days);

        uint256 releasable = vesting.releasableAmountOf(alice);
        assertEq(releasable, 1000 * 1e8);

        bait.transfer(address(vesting), 1000 * 1e8); // funding
        vm.prank(alice);
        vesting.release();
        assertEq(bait.balanceOf(alice), 1000 * 1e8);
    }

    function test_Vesting_DoubleBeneficiaryReverts() public {
        FoundersVesting vesting = _deployVesting();
        vm.startPrank(admin);
        vesting.addBeneficiary(alice, 100 * 1e8, 0);
        vm.expectRevert(abi.encodeWithSelector(FoundersVesting.AlreadyBeneficiary.selector, alice));
        vesting.addBeneficiary(alice, 200 * 1e8, 0);
        vm.stopPrank();
    }

    // ---------------------------------------------------------------
    // 6. TimelockPauseWrapper: 48h delay obrigatório
    // ---------------------------------------------------------------
    function test_PauseWrapper_RejectsTimelockWithShortDelay() public {
        // Cria TimelockController com delay muito curto (1 hora)
        address[] memory proposers = new address[](1);
        address[] memory executors = new address[](1);
        proposers[0] = admin;
        executors[0] = address(0);
        TimelockController shortTimelock = new TimelockController(1 hours, proposers, executors, admin);

        vm.expectRevert(abi.encodeWithSelector(
            TimelockPauseWrapper.DelayTooShort.selector, 1 hours, 48 hours
        ));
        new TimelockPauseWrapper(shortTimelock, IPausableTarget(address(bridge)), admin);
    }

    function test_PauseWrapper_OnlyTimelockCanExecute() public {
        address[] memory proposers = new address[](1);
        address[] memory executors = new address[](1);
        proposers[0] = admin;
        executors[0] = address(0);
        TimelockController timelock = new TimelockController(48 hours, proposers, executors, admin);
        TimelockPauseWrapper wrapper = new TimelockPauseWrapper(timelock, IPausableTarget(address(bridge)), admin);

        // Tentar executar pause diretamente (sem ser o Timelock)
        vm.expectRevert(TimelockPauseWrapper.NotTimelock.selector);
        wrapper.executePause();
    }

    // ---------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------
    function _signUnlock(address recipient, uint256 amount, uint256 nonce, uint256 sourceChainId)
        internal
        view
        returns (bytes memory)
    {
        return _signUnlock(recipient, amount, nonce, sourceChainId, relayer);
    }

    function _signUnlock(address recipient, uint256 amount, uint256 nonce, uint256 sourceChainId, address signer)
        internal
        view
        returns (bytes memory)
    {
        bytes32 structHash = keccak256(abi.encode(
            keccak256("Unlock(address recipient,uint256 amount,uint256 nonce,uint256 sourceChainId)"),
            recipient, amount, nonce, sourceChainId
        ));
        bytes32 digest = keccak256(abi.encodePacked(
            "\x19\x01",
            bridge.domainSeparator(),
            structHash
        ));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(_keyOf(signer), digest);
        return abi.encodePacked(r, s, v);
    }

    function _keyOf(address signer) internal view returns (uint256) {
        if (signer == relayer) return RELAYER_KEY;
        if (signer == admin)   return ADMIN_KEY;
        if (signer == alice)   return ALICE_KEY;
        if (signer == bob)     return BOB_KEY;
        if (signer == vm.addr(DEAD_KEY)) return DEAD_KEY;
        revert("unknown signer");
    }

    function _deployVesting() internal returns (FoundersVesting) {
        return new FoundersVesting(
            address(bait),
            block.timestamp,
            4 * 365 days,
            admin,
            pauser
        );
    }
}

/**
 * @notice Mock minimal ERC20 para isolar o BAITBridge em tests.
 */
contract MockBAIT {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}
