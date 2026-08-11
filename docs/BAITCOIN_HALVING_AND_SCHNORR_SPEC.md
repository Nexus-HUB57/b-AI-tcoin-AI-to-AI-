# Especificação Técnica: Halving Programado e Assinaturas Schnorr (BIP-340) no b-AI-tcoin

## 1. Halving Programado e Emissão Determinística

O protocolo do **b-AI-tcoin (BAIT)** adota um modelo de emissão deflacionária idêntico ao Bitcoin, garantindo escassez absoluta e previsibilidade inflacionária para os agentes autônomos e investidores institucionais.

### 1.1 Parâmetros de Emissão
* **Recompensa Inicial por Bloco:** 50 BAIT por bloco L1 minerado.
* **Intervalo de Halving:** A cada **210.000 blocos** (aproximadamente 4 anos considerando blocos de 30 segundos).
* **Fornecimento Máximo (Max Supply):** 21.000.000 BAIT.
* **Lógica Matemática de Subsídio:**
  ```python
  def get_block_subsidy(height: int) -> int:
      halvings = height // 210000
      if halvings >= 64:
          return 0
      subsidy = 50 * 10**8  # em satoshis de BAIT (BAIT-Sats)
      return subsidy >> halvings
  ```

---

## 2. Assinaturas Schnorr (BIP-340) no Protocolo

Para viabilizar microtransações em massa e agregação de assinaturas em enxames de IA, o b-AI-tcoin implementa o padrão **BIP-340 (Schnorr Signatures over secp256k1)**.

### 2.1 Vantagens Técnicas
1. **Linearidade e Agregação (MuSig2):** Permite que centenas de agentes autônomos em um enxame assinem uma única transação conjunta, gerando uma assinatura compacta de 64 bytes que ocupa menos espaço no mempool e reduz taxas de transação (*gas*).
2. **Resistência a Ataques de Maleabilidade:** Elimina vulnerabilidades de malleability presentes em assinaturas ECDSA tradicionais.
3. **Validação Otimizada:** Reduz o custo computacional de verificação criptográfica em nós validadores de alta performance.
