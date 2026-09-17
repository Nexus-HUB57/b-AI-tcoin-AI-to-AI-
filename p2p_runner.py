import asyncio, sys
sys.path.insert(0, "/home/baitcoin/app")
from baitcoin_core.network.p2p_real.node import P2PNode

async def main():
    node = P2PNode(host="0.0.0.0", port=18444, agent_id="baitcoin-seed-1")
    await node.start()
    print("P2P_LISTENING 0.0.0.0:18444", flush=True)
    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
