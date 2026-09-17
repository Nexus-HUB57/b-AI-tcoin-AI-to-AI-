#!/bin/bash
# Faucet diaria dos 5 Agentes Fundadores (10 BAIT cada, cooldown 24h respeitado pela rota)
LOG=/home/baitcoin/.baitcoin/founders_faucet.log
echo "$(date -u +%FT%TZ) START" >> $LOG
curl -s -m 20 -X POST http://127.0.0.1:18445/api/v1/faucet/public-claim -H "Content-Type: application/json" -d '{"agent_id":"dola-ceo","address":"b'/t157yopg2u85cnSaZPcgrJH4HCLqwkCks68"}' >> $LOG 2>&1; echo >> $LOG
curl -s -m 20 -X POST http://127.0.0.1:18445/api/v1/faucet/public-claim -H "Content-Type: application/json" -d '{"agent_id":"ktd-orchestrator","address":"b'/t32oRLn8We5w3UnSqSTQnYZxukxsNHud7CCJj"}' >> $LOG 2>&1; echo >> $LOG
curl -s -m 20 -X POST http://127.0.0.1:18445/api/v1/faucet/public-claim -H "Content-Type: application/json" -d '{"agent_id":"chimera7-defi","address":"b'/tFaLTR3J7Tw6v7pf667tgK6oCFrnFJUmwJ"}' >> $LOG 2>&1; echo >> $LOG
curl -s -m 20 -X POST http://127.0.0.1:18445/api/v1/faucet/public-claim -H "Content-Type: application/json" -d '{"agent_id":"sentinel-oracle","address":"b'/t6z4pMD1dsq3Nf7V9mbGpLhoD8dVe3AGxP"}' >> $LOG 2>&1; echo >> $LOG
curl -s -m 20 -X POST http://127.0.0.1:18445/api/v1/faucet/public-claim -H "Content-Type: application/json" -d '{"agent_id":"prompt-compressor","address":"b'/t7MKu2btb2vMaBFRUPYBa6f8EiCLZZoS8p"}' >> $LOG 2>&1; echo >> $LOG
echo "$(date -u +%FT%TZ) END" >> $LOG
