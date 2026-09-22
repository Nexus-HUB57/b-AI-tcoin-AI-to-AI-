// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../../src/WBAIT.sol";
import "../../src/BridgeLock.sol";

contract BridgeEchidna {
    WBAIT public wbait;
    BridgeLock public bridge;

    address constant OP1 = address(0x1001);
    address constant OP2 = address(0x1002);
    address constant OP3 = address(0x1003);
    address constant OP4 = address(0x1004);
    address constant OP5 = address(0x1005);

    constructor() {
        wbait = new WBAIT();
        address[5] memory ops = [OP1, OP2, OP3, OP4, OP5];
        bridge = new BridgeLock(address(wbait), ops);
        wbait.setBridgeLock(address(bridge));
    }

    function echidna_minted_leq_locked() public view returns (bool) {
        return bridge.totalMinted() <= bridge.totalLocked();
    }

    function echidna_conservation_holds() public view returns (bool) {
        return bridge.conservationHolds();
    }
}
