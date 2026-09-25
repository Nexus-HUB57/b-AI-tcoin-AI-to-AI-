// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console2.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title DryRunLifecycle
 * @notice Fork dry-run: deploy + full lifecycle without broadcasting.
 *   forge script script/DryRunLifecycle.s.sol:DryRunLifecycle --fork-url https://ethereum.publicnode.com -vv
 */
contract DryRunLifecycle is Script {
    address constant SAFE = address(uint160(0x5AFE));
    address constant OP0  = address(uint160(0x0A01));
    address constant OP1  = address(uint160(0x0A02));
    address constant OP2  = address(uint160(0x0A03));
    address constant OP3  = address(uint160(0x0A04));
    address constant OP4  = address(uint160(0x0A05));
    address constant USER = address(uint160(0x05E2));

    uint256 constant ONE = 10**8;
    uint256 constant AMOUNT = 1_000 * ONE;
    uint256 constant BURN_PARTIAL = 400 * ONE;

    function run() external {
        vm.deal(SAFE, 10 ether);
        vm.deal(OP0, 1 ether);
        vm.deal(OP1, 1 ether);
        vm.deal(OP2, 1 ether);
        vm.deal(OP3, 1 ether);
        vm.deal(OP4, 1 ether);
        vm.deal(USER, 1 ether);

        address[5] memory operators;
        operators[0] = OP0;
        operators[1] = OP1;
        operators[2] = OP2;
        operators[3] = OP3;
        operators[4] = OP4;

        address[] memory proposers = new address[](1);
        proposers[0] = SAFE;
        address[] memory executors = new address[](1);
        executors[0] = SAFE;

        console2.log("=== DRY-RUN DEPLOY (fork, no broadcast) ===");
        console2.log("block", block.number);

        TimelockController timelock = new TimelockController(48 hours, proposers, executors, SAFE);
        WBAIT wbait = new WBAIT(address(0), address(timelock));
        BridgeLock bridge = new BridgeLock(address(wbait), address(timelock), operators);
        wbait.initializeBridgeLock(address(bridge));

        wbait.transferOwnership(SAFE);
        bridge.transferOwnership(SAFE);
        vm.prank(SAFE);
        wbait.acceptOwnership();
        vm.prank(SAFE);
        bridge.acceptOwnership();

        console2.log("Timelock", address(timelock));
        console2.log("WBAIT   ", address(wbait));
        console2.log("Bridge  ", address(bridge));
        console2.log("Owner   ", wbait.owner());

        require(wbait.owner() == SAFE, "owner not Safe");
        require(address(wbait.bridgeLock()) == address(bridge), "not linked");
        require(wbait.totalSupply() == 0, "supply nonzero");

        console2.log("=== LIFECYCLE ===");
        bytes32 requestId = keccak256("dryrun-offer-2");
        bytes32 l1TxId = keccak256("l1-lock-txid-example");

        vm.prank(OP0);
        bridge.requestLockMint(requestId, l1TxId, USER, AMOUNT);
        console2.log("requested amount", AMOUNT);
        require(wbait.totalSupply() == 0, "must not mint on request");

        vm.prank(OP0);
        bridge.confirmLockMint(requestId);
        vm.prank(OP1);
        bridge.confirmLockMint(requestId);
        require(wbait.totalSupply() == 0, "must not mint at 2 confirms");
        vm.prank(OP2);
        bridge.confirmLockMint(requestId);

        require(wbait.totalSupply() == AMOUNT, "mint failed");
        require(wbait.balanceOf(USER) == AMOUNT, "user bal");
        require(bridge.totalMinted() == AMOUNT, "totalMinted");
        require(bridge.totalLockedOnL1() == AMOUNT, "totalLocked");
        require(bridge.totalMinted() <= bridge.totalLockedOnL1(), "invariant");
        console2.log("minted OK", wbait.totalSupply());

        vm.startPrank(USER);
        wbait.approve(address(bridge), BURN_PARTIAL);
        bridge.initiateBurnRelease(BURN_PARTIAL, "b'dryRunReleaseAddress");
        vm.stopPrank();

        require(wbait.balanceOf(USER) == AMOUNT - BURN_PARTIAL, "partial burn bal");
        require(wbait.totalSupply() == AMOUNT - BURN_PARTIAL, "partial burn supply");
        require(bridge.totalMinted() == AMOUNT - BURN_PARTIAL, "totalMinted after burn");
        require(bridge.totalMinted() <= bridge.totalLockedOnL1(), "invariant after burn");
        console2.log("burned partial", BURN_PARTIAL);
        console2.log("remaining supply", wbait.totalSupply());

        require(bridge.getBurnReleaseCount() == 1, "burn release not recorded");
        console2.log("burnReleaseCount", bridge.getBurnReleaseCount());

        console2.log("=== DRY-RUN LIFECYCLE PASS ===");
        console2.log("NO broadcast performed. Safe to proceed to checklist Go/No-Go.");
    }
}
