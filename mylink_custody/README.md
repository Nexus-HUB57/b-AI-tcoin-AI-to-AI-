# MyLink custody verification

Pacote isolado para auditoria read-only do Fundo MyLink. Não lê `sato.dat`, não armazena seed/private key, não assina e não transmite transações.

## Componentes

- `reconcile.py`: deriva endereços P2WPKH/P2TR de xpub e reconcilia UTXOs observadas.
- `bip322_advanced.py`: verifica BIP-322 P2WSH multisig padrão e Taproot script-path single-key `xonly CHECKSIG` com control block.
- `cron_reconcile.py`: job idempotente que lê xpub watch-only e endpoint HTTPS, grava relatório atômico e sai com código 1 se a reconciliação estiver bloqueada.

## Cron

Instalar dependências em um virtualenv dedicado e configurar as variáveis em um arquivo root-only fora do repositório:

```cron
17 * * * * . /etc/mylink-custody.env && /opt/trinity-venv/bin/python -m mylink_custody.cron_reconcile >> /var/log/trinity/mylink-reconcile.log 2>&1
```

O cron não deve receber a seed, private key ou `sato.dat`. `MYLINK_WATCH_XPUB` é somente watch-only. O endpoint deve ser HTTPS e a resposta deve conter apenas UTXOs públicas.

## Estado de produção

A integração deve permanecer em `BLOCKED` até que o endpoint seja validado contra um nó Bitcoin próprio, o descriptor/xpub seja conferido offline e o saldo seja reconciliado por `txid:vout`. O suporte de script-path aceita apenas o template explicitamente auditado; não interpretar scripts arbitrários como válidos.
