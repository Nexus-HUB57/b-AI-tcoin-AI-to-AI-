# Monitoramento contínuo do Go-Live b'AI'tcoin — substituto manual

> O workflow de plataforma ("baitcoin-golive-healthcheck") NÃO pôde ser criado
> (falha no lado do servidor, mesmo após 2 tentativas — confirmado via
> `manage_workflow`: nenhum workflow foi criado; existe apenas o pré-existente
> "ONDA-46 · Deploy VPS oneverso", desabilitado, não relacionado).
> Este script é o substituto manual equivalente.

## O que faz
Roda `verify_golive.sh` (checklist C01–C11) contra `https://mybait.org`
a cada intervalo e registra cada execução com timestamp UTC.

## Instalação (1 comando — no servidor ou em qualquer máquina com internet)

### Opção A — loop contínuo (nohup)
```bash
curl -fsSL https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/golive_healthcheck.sh -o /usr/local/sbin/golive_healthcheck.sh
chmod +x /usr/local/sbin/golive_healthcheck.sh
nohup /usr/local/sbin/golive_healthcheck.sh > /dev/null 2>&1 &
```

### Opção B — cron (a cada hora)
```bash
curl -fsSL https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/golive_healthcheck.sh -o /usr/local/sbin/golive_healthcheck.sh
chmod +x /usr/local/sbin/golive_healthcheck.sh
( crontab -l 2>/dev/null | grep -v golive_healthcheck; echo '0 * * * * /usr/local/sbin/golive_healthcheck.sh --once >> /var/log/golive_healthcheck.log 2>&1' ) | crontab -
```

## Variáveis
- `GOLIVE_INTERVAL` — segundos entre execuções (padrão 3600)
- `GOLIVE_BASE` — URL base (padrão `https://mybait.org`)

## Log
- `/var/log/golive_healthcheck.log` (ou `~/golive_healthcheck.log` se não for gravável)

## Teste manual
```bash
bash /usr/local/sbin/golive_healthcheck.sh --once
```
