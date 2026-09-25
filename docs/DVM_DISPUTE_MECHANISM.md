# Mecanismo de disputa DVM

Backstop do oráculo otimista: só roda quando uma proposta é disputada na janela de liveness.

```
Propose(+bond) → Liveness → [Settle] ou [Dispute → DVM vote → Resolve]
```

Staging HUB: disputas de settlement → 3 assinaturas humanas + docs/SETTLEMENT-00N.md até OO/DVM EVM.
Agente: `dvm-dispute-sync` (register MyLink).

Nunca auto-settle GO mainnet só com agente.
