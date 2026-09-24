# Runbook de Pool P2P Público

Este runbook prepara a topologia, mas não provisiona servidores, altera firewall, publica DNS, assina transações ou movimenta fundos.

## Pré-requisitos externos

São necessários três servidores com IPs públicos e operadores independentes. Cada servidor deve possuir um `BAIT_NODE_ID` persistente, uma porta TCP P2P dedicada e um endereço de monitoramento. Os nomes DNS e as portas reais devem ser fornecidos pelo operador; não devem ser inventados no repositório.

Cada servidor deve executar o mesmo commit imutável. O firewall deve liberar somente a porta P2P para entrada e permitir saída para os outros dois seeds. A API pode ficar atrás de TLS e de uma camada de autenticação; não é necessário expor a API administrativa diretamente.

## Variáveis obrigatórias

```text
BAIT_NODE_ID=<identidade persistente do nó>
BAIT_AGENT_ID=<identidade do operador>
BAIT_P2P_PORT=18444
BAIT_P2P_SEEDS=<host-a>:18444,<host-b>:18444,<host-c>:18444
BAIT_API_HOST=127.0.0.1
```

Em Mainnet, três seeds externas distintas são obrigatórias. Seeds loopback são rejeitadas pelo daemon. O mesmo `BAIT_NODE_ID` não pode ser usado por dois operadores.

## Validação antes de publicar

Execute o serviço em testnet ou ambiente isolado. Confirme três handshakes em cada nó, compare os últimos 100 headers entre as três origens e valide que o endpoint `/api/v1/p2p/status` reporta `running: true`, `peer_count >= 3` e `handshake_peers >= 3`. Um TCP connect sem handshake não conta como peer.

Depois, configure `MAINNET_API_BASE_URL` e `ETH_RPC_URL` como variáveis de ambiente do CI e execute `scripts/mainnet_readiness_gate.py`. O resultado precisa ser `GO` antes de qualquer mudança de produção.

Para provar convergência entre operadores independentes, execute `scripts/verify_public_pool.py` repetindo `--api` três vezes com origens públicas diferentes. O verificador exige três handshakes por origem, cadeia válida e alturas convergentes.

## Limites

O Compose fornecido é uma topologia de referência local. Os três serviços usam a rede interna do Compose e, portanto, não são prova de descentralização por operadores independentes. Para Mainnet, substitua os nomes internos por hosts públicos reais, registre os operadores e gere evidências de handshake a partir de redes externas distintas.
