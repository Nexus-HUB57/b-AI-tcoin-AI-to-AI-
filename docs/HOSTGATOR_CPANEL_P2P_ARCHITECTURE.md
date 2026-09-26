# Arquitetura HostGator/cPanel para P2P público

## Decisão arquitetural

O HostGator/cPanel é o front door HTTP/CGI de `mybait.org`. Os quatro full nodes P2P devem rodar em hosts independentes com processo persistente, IP público, firewall configurável e porta TCP P2P acessível.

```text
HostGator cPanel
  ├── frontend e API HTTP
  ├── webhook de deploy
  └── monitoramento

Hosts independentes
  ├── node-a.mybait.org — full node P2P
  ├── node-b.mybait.org — full node P2P
  ├── node-c.mybait.org — full node P2P
  └── node-d.mybait.org — full node P2P
```

Não é permitido tratar quatro aliases no mesmo cPanel/VPS como quatro peers independentes. Isso falharia o objetivo de descentralização e é rejeitado pelo preflight.

## Por que cPanel não provisiona full nodes

O daemon exige processo persistente, armazenamento WAL, identidade de nó, seeds externos e porta TCP de entrada. CGI e cron de hospedagem compartilhada não fornecem garantias suficientes de uptime, isolamento, firewall ou encaminhamento TCP.

O cPanel pode publicar a API somente leitura e encaminhar observabilidade. Ele não substitui os quatro hosts P2P.

## Secrets esperados no ambiente `production`

Os valores devem ser cadastrados no GitHub Actions como secrets do ambiente `production`. Nunca versionar chaves ou valores.

| Secret | Finalidade |
|---|---|
| `NODE_A_SSH_HOST` / `_PORT` / `_USER` / `_KEY` | Acesso administrativo ao host A |
| `NODE_B_SSH_HOST` / `_PORT` / `_USER` / `_KEY` | Acesso administrativo ao host B |
| `NODE_C_SSH_HOST` / `_PORT` / `_USER` / `_KEY` | Acesso administrativo ao host C |
| `NODE_D_SSH_HOST` / `_PORT` / `_USER` / `_KEY` | Acesso administrativo ao host D |
| `NODE_[A-D]_SSH_KNOWN_HOSTS` | Pinning da identidade SSH de cada host |

Os quatro `NODE_*_SSH_HOST` devem ser distintos. O preflight rejeita loopback, hosts duplicados, DNS ausente, SSH inacessível e ausência de Docker/systemd.

As variáveis de API já existentes permanecem em Actions Variables:

```text
BAIT_PEER_API_1
BAIT_PEER_API_2
BAIT_PEER_API_3
BAIT_PEER_API_4
```

## Fluxo seguro

1. Provisionar os quatro hosts fora do cPanel.
2. Configurar firewall e porta TCP P2P.
3. Criar DNS para os quatro hosts.
4. Cadastrar os secrets no ambiente `production`.
5. Executar `P2P host preflight`.
6. Corrigir qualquer falha de DNS, SSH, runtime ou API.
7. Executar `Verify public pool` com `--min-peers 3 --require-tip-hash`.
8. Somente após `GO`, considerar qualquer promoção de produção.

O workflow `p2p-host-preflight.yml` é deliberadamente **somente validação**. Ele não cria VPS, não altera DNS, não abre firewall, não copia chaves, não instala o daemon e não movimenta capital.

## Status atual

Enquanto os quatro hosts não existirem, o preflight deve retornar `NO-GO`. Isso é esperado e evita declarar descentralização com aliases ou um único servidor.
