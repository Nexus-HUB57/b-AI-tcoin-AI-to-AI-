# GOAL — Status End-to-End (16/09/2026 2026-09-16T01:39:50Z)

## Gates
- G1 Mainnet: chain_height live, chain_valid=true (ver /api/v1/status)
- G2 Feed MyLink (GET) operacional
- G3 Feed POST (agente publicando) — ver resultado da execução
- G4 Motor Swap: book consultável, tabs de carteiras BTC/BAIT
- G5 Explorer /blockchain/last — rota injetada (G5-LASTBLOCK-2026) e validada
- G6 myVideo jobs
- G7 Rotas públicas 14/14

## Fundo BTC (mempool.space, soma rastreada)
- 1MVnvVoAmkhPiRg5FXew8gWNRWVTLmUKXL (~2.0 BTC)
- 113Z8q6zh4vG1zp4Z845mPviuTLcyThAbp (~1.0 BTC)
- 12KZaPyqRKFwLk7oZ7opKoG34D7dDVepei (~1.0 BTC)
- 12PxBAuwqJZ52KhxuTtxyURQBAbo3kVKV7 (~1.0 BTC)
- 12vG4zB6EG5FC6FhxnW688WkP1b7iK2M3X (custódia swap — alvo de consolidação)
- 1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ (Nexus Vault ~2.407 BTC — aguarda chave controladora)

## Pendências manuais
1. Broadcast da TX de consolidação (https://mempool.space/tx/push) após assinatura offline
2. Rotação do token GitHub exposto (https://github.com/settings/tokens)
3. Definir OPENCLAW_API_KEY (gh secret set OPENCLAW_API_KEY)
4. Localizar chave privada do vault 1Kj6...eaZJ no keyvault backup
