r"""Persistent Memory Store — WAL + Snapshots para armazenamento resistente a falhas.

Estrutura de armazenamento em disco::

    /data_path/
    ── <namespace>/
        ── current.json          │  último snapshot completo
        ── wal/
        ── ── 000001.log       │  segmentos do write-ahead log
        ── snapshots/
            ── snapshot_1700000000.json  │  snapshots periódicos

Ciclo de escrita:
    1. Anexar ao segmento WAL atual
    2. Se o segmento exceder 1 MB, rotacionar para o próximo
    3. A cada N escritas ou T segundos, criar um snapshot

Ciclo de leitura (recuperação):
    1. Carregar o último snapshot disponível
    2. Reaplicar todas as entradas WAL posteriores ao snapshot

Este módulo é thread-safe e utiliza travamento de arquivo (fcntl)
para garantir segurança contra acessos concorrentes.
"""

import json
import os
import fcntl
import time
import hashlib
import threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class MemoryNamespace(Enum):
    """Espaços de nomes isolados para cada módulo do ecossistema."""
    BLOCKCHAIN = "blockchain"
    AGENTS = "agents"
    STAKING = "staking"
    MARKETPLACE = "marketplace"
    ORACLE = "oracle"
    FAUCET = "faucet"
    LENDING = "lending"
    VAULTS = "vaults"
    OBSCURA = "obscura"
    REPUTATION = "reputation"
    CONFIG = "config"


@dataclass
class WALEntry:
    """Uma única entrada no write-ahead log.

    Cada entrada contém um timestamp, chave, valor, namespace e
    um checksum SHA-256 truncado para detecção de corrupção.
    """
    timestamp: float
    key: str
    value: Any
    namespace: str
    checksum: str = ""

    def to_dict(self) -> dict:
        """Serializa a entrada para um dicionário (JSON-serializável)."""
        return {
            "timestamp": self.timestamp,
            "key": self.key,
            "value": self.value,
            "namespace": self.namespace,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'WALEntry':
        """Desserializa uma entrada a partir de um dicionário."""
        return cls(
            timestamp=d["timestamp"],
            key=d["key"],
            value=d["value"],
            namespace=d["namespace"],
            checksum=d.get("checksum", ""),
        )

    def compute_checksum(self) -> str:
        """Calcula o checksum SHA-256 truncado (16 caracteres hex) da entrada.

        O checksum cobre timestamp, chave, valor serializado e namespace.
        """
        data = (
            f"{self.timestamp}:{self.key}"
            f":{json.dumps(self.value, sort_keys=True, default=str)}"
            f":{self.namespace}"
        )
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class MemoryStore:
    r"""Armazenamento chave-valor resistente a falhas com WAL e snapshots.

    Thread-safe por meio de travamento (threading.Lock + fcntl).

    Características:
        - WAL (write-ahead logging) para segurança contra falhas
        - Snapshots periódicos para recuperação rápida
        - Isolamento por namespace
        - Travamento de arquivo para acesso concorrente entre processos
        - Cache LRU para leituras frequentes

    Atributos de configuração:
        MAX_WAL_SEGMENT_SIZE: Tamanho máximo por segmento WAL (1 MB)
        SNAPSHOT_INTERVAL_WRITES: Snapshots a cada N escritas
        SNAPSHOT_INTERVAL_SECONDS: Snapshots a cada T segundos
        CACHE_SIZE: Capacidade máxima do cache em memória
    """

    MAX_WAL_SEGMENT_SIZE: int = 1_000_000       # 1 MB por segmento WAL
    SNAPSHOT_INTERVAL_WRITES: int = 100          # snapshot a cada 100 escritas
    SNAPSHOT_INTERVAL_SECONDS: float = 300.0     # ou a cada 5 minutos
    CACHE_SIZE: int = 10_000                     # entradas máximas no cache

    def __init__(self, data_path: str = "~/.baitcoin/memory") -> None:
        """Inicializa o armazenamento persistente.

        Args:
            data_path: Caminho base para os dados no disco.
                       Expandido com ``os.path.expanduser``.
        """
        self.data_path: str = os.path.expanduser(data_path)
        self._cache: Dict[str, Any] = {}
        self._cache_order: List[str] = []  # para LRU
        self._write_count: int = 0
        self._last_snapshot_time: float = time.time()
        self._lock: threading.Lock = threading.Lock()
        self._wal_segments: Dict[str, int] = {}  # namespace -> contador de segmento
        self._init_directories()

    def _init_directories(self) -> None:
        """Cria a árvore de diretórios necessária para todos os namespaces."""
        os.makedirs(self.data_path, exist_ok=True)
        for ns in MemoryNamespace:
            ns_path = os.path.join(self.data_path, ns.value)
            os.makedirs(ns_path, exist_ok=True)
            os.makedirs(os.path.join(ns_path, "wal"), exist_ok=True)
            os.makedirs(os.path.join(ns_path, "snapshots"), exist_ok=True)

    # ------------------------------------------------------------------
    # Cache LRU
    # ------------------------------------------------------------------

    def _cache_get(self, key: str) -> Optional[Any]:
        """Obtém um valor do cache LRU. Retorna None se ausente."""
        if key in self._cache:
            # Mover para o fim (mais recentemente usado)
            self._cache_order.remove(key)
            self._cache_order.append(key)
            return self._cache[key]
        return None

    def _cache_put(self, key: str, value: Any) -> None:
        """Insere um valor no cache LRU, evictando o mais antigo se necessário."""
        if key in self._cache:
            self._cache_order.remove(key)
        elif len(self._cache) >= self.CACHE_SIZE:
            # Evictar a entrada mais antiga
            oldest = self._cache_order.pop(0)
            del self._cache[oldest]
        self._cache[key] = value
        self._cache_order.append(key)

    def _cache_delete(self, key: str) -> None:
        """Remove um valor do cache LRU, se presente."""
        if key in self._cache:
            del self._cache[key]
            self._cache_order.remove(key)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def put(self, namespace: str, key: str, value: Any) -> None:
        r"""Escreve um par chave-valor com durabilidade via WAL.

        A operação é atômica dentro do lock: a entrada é
        primeiramente registrada no WAL e, em seguida, o cache é
        atualizado. Um snapshot é criado automaticamente quando
        os limiares de escrita ou tempo são atingidos.

        Args:
            namespace: O namespace lógico (ex: ``"blockchain"``).
            key: Identificador da chave dentro do namespace.
            value: Qualquer valor JSON-serializável.
        """
        with self._lock:
            entry = WALEntry(
                timestamp=time.time(),
                key=key,
                value=value,
                namespace=namespace,
            )
            entry.checksum = entry.compute_checksum()
            self._append_wal(namespace, entry)
            cache_key = f"{namespace}:{key}"
            self._cache_put(cache_key, value)
            self._write_count += 1
            if self._should_snapshot():
                self._create_snapshot(namespace)

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        r"""Lê um valor (cache primeiro, depois disco).

        Args:
            namespace: O namespace lógico.
            key: A chave desejada.
            default: Valor retornado se a chave não existir.

        Returns:
            O valor armazenado ou ``default``.
        """
        cache_key = f"{namespace}:{key}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._load_namespace(namespace)
        if data is not None and key in data:
            self._cache_put(cache_key, data[key])
            return data[key]
        return default

    def get_all(self, namespace: str) -> Dict[str, Any]:
        r"""Retorna todos os pares chave-valor de um namespace.

        Args:
            namespace: O namespace lógico.

        Returns:
            Dicionário com todos os dados do namespace (cópia).
        """
        data = self._load_namespace(namespace)
        if data is None:
            return {}
        for k, v in data.items():
            self._cache_put(f"{namespace}:{k}", v)
        return dict(data)

    def put_all(self, namespace: str, data: Dict[str, Any]) -> None:
        r"""Substitui completamente o estado de um namespace.

        Diferente de ``put`` individual, esta operação remove todas as
        chaves anteriores do namespace e as substitui pelo ``data``
        fornecido.  No WAL é registrado com o marcador ``__bulk__`` que,
        durante a reaplicação, substitui o estado em vez de mesclar.

        Args:
            namespace: O namespace lógico.
            data: Dicionário completo a ser persistido.
        """
        with self._lock:
            entry = WALEntry(
                timestamp=time.time(),
                key="__bulk__",
                value=data,
                namespace=namespace,
            )
            entry.checksum = entry.compute_checksum()
            self._append_wal(namespace, entry)
            # Limpar cache antigo do namespace e inserir novo
            prefix = f"{namespace}:"
            stale = [k for k in self._cache if k.startswith(prefix)]
            for k in stale:
                self._cache_delete(k)
            for k, v in data.items():
                self._cache_put(f"{prefix}{k}", v)
            self._write_count += 1
            if self._should_snapshot():
                self._create_snapshot(namespace)

    def delete(self, namespace: str, key: str) -> bool:
        r"""Remove uma chave do namespace. Retorna True se a chave existia.

        A deleção registra uma entrada ``__delete__`` no WAL, que durante
        a reaplicação remove a chave especificada. Isto evita que chaves
        excluídas reapareçam ao reaplicar entradas ``__bulk__`` anteriores.

        Args:
            namespace: O namespace lógico.
            key: A chave a ser removida.

        Returns:
            True se a chave existia e foi removida, False caso contrário.
        """
        with self._lock:
            data = self._load_namespace(namespace) or {}
            if key in data:
                self._cache_delete(f"{namespace}:{key}")
                # Registrar deleção como entrada WAL dedicada
                entry = WALEntry(
                    timestamp=time.time(),
                    key="__delete__",
                    value=key,
                    namespace=namespace,
                )
                entry.checksum = entry.compute_checksum()
                self._append_wal(namespace, entry)
                self._write_count += 1
                if self._should_snapshot():
                    self._create_snapshot(namespace)
                return True
            return False

    def namespace_exists(self, namespace: str) -> bool:
        r"""Verifica se um namespace possui diretório no disco.

        Args:
            namespace: Nome do namespace.

        Returns:
            True se o diretório do namespace existe.
        """
        return os.path.isdir(os.path.join(self.data_path, namespace))

    def list_namespaces(self) -> List[str]:
        r"""Lista todos os namespaces presentes no disco.

        Returns:
            Lista ordenada de nomes de namespaces.
        """
        if not os.path.isdir(self.data_path):
            return []
        return sorted(
            d for d in os.listdir(self.data_path)
            if os.path.isdir(os.path.join(self.data_path, d))
        )

    def get_stats(self) -> dict:
        r"""Retorna estatísticas operacionais do armazenamento.

        Returns:
            Dicionário com caminho, namespaces, chaves em cache,
            total de escritas e timestamp do último snapshot.
        """
        return {
            "data_path": self.data_path,
            "namespaces": self.list_namespaces(),
            "cached_keys": len(self._cache),
            "total_writes": self._write_count,
            "last_snapshot": self._last_snapshot_time,
        }

    def force_snapshot(self, namespace: Optional[str] = None) -> None:
        r"""Força a criação de um snapshot imediato.

        Args:
            namespace: Namespace específico ou None para todos.
        """
        with self._lock:
            if namespace:
                self._create_snapshot(namespace)
            else:
                for ns in self.list_namespaces():
                    self._create_snapshot(ns)

    def compact(self, namespace: str) -> int:
        r"""Compacta o WAL de um namespace: cria snapshot e remove segmentos antigos.

        Args:
            namespace: Namespace a ser compactado.

        Returns:
            Número de segmentos WAL removidos.
        """
        with self._lock:
            self._create_snapshot(namespace)
            wal_dir = os.path.join(self.data_path, namespace, "wal")
            removed = 0
            if os.path.isdir(wal_dir):
                for fname in os.listdir(wal_dir):
                    if fname.endswith(".log"):
                        try:
                            os.remove(os.path.join(wal_dir, fname))
                            removed += 1
                        except OSError:
                            pass
            self._wal_segments.pop(namespace, None)
            return removed

    # ------------------------------------------------------------------
    # Interno: WAL (Write-Ahead Log)
    # ------------------------------------------------------------------

    def _wal_path(self, namespace: str, segment: int) -> str:
        """Retorna o caminho absoluto de um segmento WAL."""
        return os.path.join(self.data_path, namespace, "wal", f"{segment:06d}.log")

    def _current_segment(self, namespace: str) -> int:
        """Retorna o número do segmento WAL atual para o namespace."""
        if namespace in self._wal_segments:
            return self._wal_segments[namespace]
        # Descobrir o último segmento existente no disco
        wal_dir = os.path.join(self.data_path, namespace, "wal")
        if os.path.isdir(wal_dir):
            segments = []
            for fname in os.listdir(wal_dir):
                if fname.endswith(".log"):
                    try:
                        segments.append(int(fname.split(".")[0]))
                    except ValueError:
                        pass
            if segments:
                self._wal_segments[namespace] = max(segments)
                return self._wal_segments[namespace]
        self._wal_segments[namespace] = 1
        return 1

    def _ensure_namespace_dir(self, namespace: str) -> None:
        """Garante que o diretório e subdiretórios de um namespace existam."""
        ns_path = os.path.join(self.data_path, namespace)
        os.makedirs(ns_path, exist_ok=True)
        os.makedirs(os.path.join(ns_path, "wal"), exist_ok=True)
        os.makedirs(os.path.join(ns_path, "snapshots"), exist_ok=True)

    def _append_wal(self, namespace: str, entry: WALEntry) -> None:
        r"""Anexa uma entrada ao segmento WAL atual, rotacionando se necessário.

        O arquivo é travado exclusivamente durante a escrita para
        garantir segurança entre processos.
        """
        self._ensure_namespace_dir(namespace)
        seg = self._current_segment(namespace)
        path = self._wal_path(namespace, seg)

        # Rotacionar se o segmento atual exceder o tamanho máximo
        if os.path.exists(path) and os.path.getsize(path) > self.MAX_WAL_SEGMENT_SIZE:
            seg += 1
            self._wal_segments[namespace] = seg
            path = self._wal_path(namespace, seg)

        with open(path, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry.to_dict(), default=str) + "\n")
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # ------------------------------------------------------------------
    # Interno: Snapshots
    # ------------------------------------------------------------------

    def _snapshot_path(self, namespace: str) -> str:
        """Retorna o caminho do snapshot atual de um namespace."""
        return os.path.join(self.data_path, namespace, "current.json")

    def _should_snapshot(self) -> bool:
        """Verifica se é hora de criar um novo snapshot."""
        return (
            self._write_count >= self.SNAPSHOT_INTERVAL_WRITES
            or time.time() - self._last_snapshot_time >= self.SNAPSHOT_INTERVAL_SECONDS
        )

    def _create_snapshot(self, namespace: str) -> None:
        r"""Cria um snapshot completo do namespace no disco.

        O snapshot é criado mesclando o último snapshot com o cache
        em memória, garantindo que o estado mais recente seja persistido.
        O arquivo é escrito de forma atômica (write-to-temp + rename).
        """
        data = self._load_namespace(namespace, replay_wal=True)
        if data is None:
            data = {}

        # Mesclar cache para garantir o estado mais recente
        for full_key, value in self._cache.items():
            if full_key.startswith(f"{namespace}:"):
                key = full_key[len(namespace) + 1:]
                data[key] = value

        self._ensure_namespace_dir(namespace)

        target_path = self._snapshot_path(namespace)
        temp_path = target_path + ".tmp"

        try:
            with open(temp_path, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, default=str, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            # Renomeação atômica
            os.replace(temp_path, target_path)
        except (IOError, OSError):
            # Limpar arquivo temporário em caso de erro
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise

        self._write_count = 0
        self._last_snapshot_time = time.time()

    # ------------------------------------------------------------------
    # Interno: Carregamento e Reaplicação
    # ------------------------------------------------------------------

    def _load_namespace(
        self, namespace: str, replay_wal: bool = True
    ) -> Optional[Dict[str, Any]]:
        r"""Carrega o estado completo de um namespace.

        Se ``replay_wal`` for True (padrão), o estado resultante
        inclui todas as entradas do WAL posteriores ao snapshot.
        Entradas corrompidas (checksum inválido) são ignoradas
        silenciosamente para maximizar a recuperação.

        Args:
            namespace: Nome do namespace.
            replay_wal: Se True, reaplica as entradas do WAL.

        Returns:
            Dicionário com o estado completo, ou dict vazio.
        """
        # 1. Carregar snapshot
        snapshot_path = self._snapshot_path(namespace)
        data: Dict[str, Any] = {}
        if os.path.exists(snapshot_path):
            try:
                with open(snapshot_path, 'r') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        data = loaded
            except (json.JSONDecodeError, IOError, OSError):
                pass

        if not replay_wal:
            return data

        # 2. Reaplicar entradas do WAL
        wal_dir = os.path.join(self.data_path, namespace, "wal")
        if not os.path.isdir(wal_dir):
            return data

        wal_files = sorted(
            f for f in os.listdir(wal_dir) if f.endswith('.log')
        )

        for wal_file in wal_files:
            wal_path = os.path.join(wal_dir, wal_file)
            try:
                with open(wal_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry_data = json.loads(line)
                            entry = WALEntry.from_dict(entry_data)

                            # Verificar integridade
                            expected = entry.compute_checksum()
                            if expected != entry.checksum:
                                # Entrada corrompida — ignorar
                                continue

                            if entry.key == "__delete__" and isinstance(entry.value, str):
                                data.pop(entry.value, None)
                            elif entry.key == "__bulk__" and isinstance(entry.value, dict):
                                # put_all substitui o estado inteiro
                                data = dict(entry.value)
                            elif entry.key not in ("__bulk__", "__delete__"):
                                data[entry.key] = entry.value
                        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                            continue
            except IOError:
                continue

        return data
