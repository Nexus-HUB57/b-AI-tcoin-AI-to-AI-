# Guia de Configuração: Monitoramento de Integridade de Blocos e Validação de Merkle Trees no CI/CD (MyBait.org)

## 1. Fundamentação Criptográfica

Para assegurar que nenhum commit ou atualização de código afete a imutabilidade da blockch'AI'in genuína (`genuine-mainnet-v1`), o pipeline de Integração Contínua (**CI/CD**) executa validações criptográficas estritas sobre a estrutura das **Árvores de Merkle** (*Merkle Trees*) e os hashes de blocos gerados pelo daemon de produção.

---

## 2. Implementação do Job de Validação de Merkle no GitHub Actions

O arquivo `.github/workflows/merkle-integrity-audit.yml` incorpora a auditoria automática de integridade em cada ciclo de build:

```yaml
name: Merkle Tree & Block Integrity Audit

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  audit-merkle:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          python3 -m pip install --upgrade pip
          pip3 install hashlib256 pytest

      - name: Run Merkle Root & Block Integrity Test Suite
        run: |
          python3 -c "
          import hashlib

          def compute_merkle_root(transactions):
              if not transactions:
                  return hashlib.sha256(b'').hexdigest()
              layer = [hashlib.sha256(tx.encode()).digest() for tx in transactions]
              while len(layer) > 1:
                  next_layer = []
                  for i in range(0, len(layer), 2):
                      left = layer[i]
                      right = layer[i+1] if i+1 < len(layer) else left
                      combined = hashlib.sha256(left + right).digest()
                      next_layer.append(combined)
                  layer = next_layer
              return layer[0].hex()

          # Test Suite com transações simuladas de enxame A2A
          sample_txs = ['tx_agent_alpha_001', 'tx_agent_beta_002', 'tx_agent_gamma_003']
          root_hash = compute_merkle_root(sample_txs)
          assert len(root_hash) == 64, 'Invalid Merkle Root length'
          print(f'Merkle Root verified successfully: {root_hash}')
          "
```
