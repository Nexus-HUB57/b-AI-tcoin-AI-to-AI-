r"""
Peer Discovery - Descoberta de nós via DHT simplificado.

Implementa descoberta de peers usando:
- Kademlia-like XOR distance
- Bucket routing table
- BOOTSTRAP via seeds conhecidos
- Announce de novo nó na rede
"""
import hashlib
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict


@dataclass
class PeerAddress:
    """Endereço de um peer na rede."""
    peer_id: str
    host: str
    port: int
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    failures: int = 0
    score: float = 50.0

    def touch(self) -> None:
        self.last_seen = time.time()

    def is_alive(self, max_age: float = 7200) -> bool:
        return (time.time() - self.last_seen) < max_age

    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "score": self.score,
            "alive": self.is_alive(),
        }


class RoutingTable:
    """Tabela de roteamento Kademlia-like.

    Organiza peers em k-buckets baseados em XOR distance.
    Cada bucket mantém até K peers.
    """

    K = 16  # Peers por bucket
    BUCKET_COUNT = 256  # 1 byte de prefixo

    def __init__(self, own_id: str):
        self.own_id = own_id
        try:
            self.own_distance = int(own_id, 16)
        except ValueError:
            self.own_distance = int(hashlib.sha256(own_id.encode()).hexdigest(), 16)
        self.buckets: Dict[int, OrderedDict[str, PeerAddress]] = {
            i: OrderedDict() for i in range(self.BUCKET_COUNT)
        }

    def _bucket_index(self, peer_id: str) -> int:
        try:
            distance = int(peer_id, 16) ^ self.own_distance
        except ValueError:
            distance = int(hashlib.sha256(peer_id.encode()).hexdigest(), 16) ^ self.own_distance
        prefix = distance.bit_length() - 1
        return max(0, min(prefix, self.BUCKET_COUNT - 1))

    def add_peer(self, peer: PeerAddress) -> bool:
        idx = self._bucket_index(peer.peer_id)
        bucket = self.buckets[idx]
        if peer.peer_id in bucket:
            bucket.move_to_end(peer.peer_id)
            bucket[peer.peer_id].touch()
            return True
        if len(bucket) < self.K:
            bucket[peer.peer_id] = peer
            return True
        # Evict least-recently-seen
        oldest_key = next(iter(bucket))
        if bucket[oldest_key].score < peer.score:
            bucket.popitem(last=False)
            bucket[peer.peer_id] = peer
            return True
        return False

    def find_closest(self, target_id: str, count: int = K) -> List[PeerAddress]:
        try:
            target = int(target_id, 16)
        except ValueError:
            target = int(hashlib.sha256(target_id.encode()).hexdigest(), 16)
        all_peers = []
        for bucket in self.buckets.values():
            for peer in bucket.values():
                if peer.is_alive():
                    try:
                        dist = int(peer.peer_id, 16) ^ target
                    except ValueError:
                        dist = int(hashlib.sha256(peer.peer_id.encode()).hexdigest(), 16) ^ target
                    all_peers.append((dist, peer))
        all_peers.sort(key=lambda x: x[0])
        return [p for _, p in all_peers[:count]]

    def get_all_peers(self) -> List[PeerAddress]:
        return [p for b in self.buckets.values() for p in b.values() if p.is_alive()]

    def get_alive_count(self) -> int:
        return sum(1 for b in self.buckets.values() for p in b.values() if p.is_alive())

    def remove_peer(self, peer_id: str) -> None:
        idx = self._bucket_index(peer_id)
        self.buckets[idx].pop(peer_id, None)

    def penalize(self, peer_id: str) -> None:
        idx = self._bucket_index(peer_id)
        peer = self.buckets[idx].get(peer_id)
        if peer:
            peer.failures += 1
            peer.score = max(0, peer.score - 10)
            if peer.failures >= 5:
                self.remove_peer(peer_id)

    def reward(self, peer_id: str) -> None:
        idx = self._bucket_index(peer_id)
        peer = self.buckets[idx].get(peer_id)
        if peer:
            peer.score = min(100, peer.score + 2)
            peer.failures = 0


class PeerDiscovery:
    """Serviço de descoberta de peers para a rede b'AI'tcoin.

    Combina:
    - Routing table Kademlia-like
    - Seed nodes estáticos
    - Announce periódico
    """

    def __init__(self, own_id: str, seeds: Optional[List[Tuple[str, int]]] = None):
        self.own_id = own_id
        self.routing = RoutingTable(own_id)
        self.seeds = seeds or []
        self._discovered_history: List[str] = []

        # Add seeds to routing table
        for host, port in self.seeds:
            pid = hashlib.sha256(f"{host}:{port}".encode()).hexdigest()[:16]
            self.routing.add_peer(PeerAddress(peer_id=pid, host=host, port=port))

    def announce(self, host: str, port: int) -> str:
        """Registra este nó na rede."""
        pid = hashlib.sha256(f"{host}:{port}".encode()).hexdigest()[:16]
        self.routing.add_peer(PeerAddress(peer_id=pid, host=host, port=port, score=100.0))
        return pid

    def discover(self, target_id: str = "", count: int = 16) -> List[dict]:
        """Encontra peers mais próximos do target."""
        target = target_id or self.own_id
        peers = self.routing.find_closest(target, count)
        return [p.to_dict() for p in peers]

    def add_peer(self, peer_id: str, host: str, port: int) -> bool:
        """Adiciona peer descoberto."""
        peer = PeerAddress(peer_id=peer_id, host=host, port=port)
        added = self.routing.add_peer(peer)
        if added:
            self._discovered_history.append(peer_id)
        return added

    def remove_peer(self, peer_id: str) -> None:
        self.routing.remove_peer(peer_id)

    def get_random_peers(self, count: int = 8) -> List[dict]:
        """Retorna peers aleatórios para gossip."""
        all_peers = self.routing.get_all_peers()
        import random
        selected = random.sample(all_peers, min(count, len(all_peers)))
        return [p.to_dict() for p in selected]

    def get_stats(self) -> dict:
        return {
            "own_id": self.own_id,
            "known_peers": self.routing.get_alive_count(),
            "seeds": len(self.seeds),
            "total_discovered": len(self._discovered_history),
        }
