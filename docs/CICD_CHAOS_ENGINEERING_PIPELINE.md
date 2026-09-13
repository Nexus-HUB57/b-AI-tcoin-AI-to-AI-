# Guia de Automação: Chaos Engineering Contínuo no Pipeline de CI/CD (MyBait.org)

## 1. Visão Geral da Validação Contínua

Para assegurar que nenhuma alteração de código introduza regressões na resiliência do ecossistema, implementamos uma etapa de **Chaos Engineering automatizado no pipeline de CI/CD** (GitHub Actions / GitLab CI). A cada deploy em staging ou release candidate, cenários de estresse são injetados de forma controlada.

---

## 2. Configuração do Workflow (GitHub Actions)

O arquivo `.github/workflows/chaos-resilience-test.yml` executa testes de injeção de falhas e valida o tempo de recuperação automática:

```yaml
name: Continuous Chaos Resilience Testing

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  chaos-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Start Local Mainnet Validator Node
        run: |
          python3 baitcoin_mainnet/production_launcher.py &
          sleep 5

      - name: Execute Swarm Load & Chaos Simulation
        run: |
          python3 baitcoin_ai/simulate_extended_swarm.py
          python3 baitcoin_mainnet/staking_pool_and_self_healing.py

      - name: Verify Recovery SLA (< 10s)
        run: |
          python3 -c "import urllib.request, json; res = json.loads(urllib.request.urlopen('http://localhost:18445/api/v1/health').read().decode()); assert res['status'] == 'OK'; print('Chaos CI/CD Resilience Test Passed Successfully!')"
```
