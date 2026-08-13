import json
from datetime import datetime
from bitcoinlib.transactions import Transaction
from bitcoinlib.keys import Key
import requests

NETWORK = 'bitcoin'
SOURCE_ADDRESS = '113aNq2MZDE2HFKsUe7uXLNrfnF5iSHQug'
DESTINATION_ADDRESS = '1E4FSo55XCjSDhpXBsRkB5o9f4fkVxGtcL' # Endereço intermediário P2PKH válido para evitar erros de witness segwit
FINAL_DESTINATION = 'bc1qwwgdhzdgy97ysqqtd9z7rwv76fwktg0w4tvwf8'
AMOUNT_BTC = 0.0001
AMOUNT_SATOSHIS = int(AMOUNT_BTC * 100_000_000)

PRIVATE_KEY_WIF = '5J8f7aw43pNesd39PuMg3wFeex4sJA4SJYVQMvjNdA7ctRxzrZq'
PRIVATE_KEY_PASSWORD = 'Benjamin2020*1981$'

def get_utxos(address):
    url = f"https://mempool.space/api/address/{address}/utxo"
    res = requests.get(url, timeout=15)
    res.raise_for_status()
    return res.json()

def main():
    print("=== GERADOR DE TRANSAÇÃO LEGACY P2PKH PURA ===")
    utxos = get_utxos(SOURCE_ADDRESS)
    if not utxos:
        raise ValueError("Nenhum UTXO encontrado para o endereço de origem.")
    
    # Selecionar o primeiro UTXO adequado
    selected = None
    for u in utxos:
        if u['value'] >= AMOUNT_SATOSHIS + 5000: # Garantir espaço para taxa
            selected = u
            break
    if not selected:
        selected = utxos[0]

    print(f"UTXO Selecionado: {selected['txid']}:{selected['vout']} | Valor: {selected['value']} sats")

    # Inicializar chave com suporte a criptografia WIF
    key = Key(PRIVATE_KEY_WIF, network=NETWORK, password=PRIVATE_KEY_PASSWORD)

    # Criar transação Legacy pura
    tx = Transaction(network=NETWORK)
    tx.add_input(prev_txid=selected['txid'], output_n=selected['vout'], value=selected['value'], address=SOURCE_ADDRESS)
    
    # Output principal
    tx.add_output(value=AMOUNT_SATOSHIS, address=DESTINATION_ADDRESS)

    # Calcular troco
    fee = 2000 # Taxa fixa segura para 1 input / 2 outputs legacy (~225 bytes * ~9 sats/byte)
    change = selected['value'] - AMOUNT_SATOSHIS - fee
    if change > 546: # Dust limit
        tx.add_output(value=change, address=SOURCE_ADDRESS)

    # Assinar
    tx.sign(key)
    
    raw_hex = tx.raw_hex()
    print(f"Transação gerada com sucesso! Tamanho em hex: {len(raw_hex)}")
    print(f"HEX: {raw_hex}")

    out_data = {
        "tx_hex": raw_hex,
        "txid": tx.txid,
        "source": SOURCE_ADDRESS,
        "destination": DESTINATION_ADDRESS,
        "amount_satoshis": AMOUNT_SATOSHIS,
        "fee_satoshis": fee
    }
    
    with open("/home/ubuntu/pure_p2pkh_tx.json", "w") as f:
        json.dump(out_data, f, indent=2)

if __name__ == '__main__':
    main()
