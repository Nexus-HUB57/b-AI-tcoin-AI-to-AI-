import pandas as pd
import requests
import time
import os

def get_balance(address):
    if not address or pd.isna(address) or address == 'nan':
        return 0
    
    # Tentar Blockchain.info
    try:
        url = f"https://blockchain.info/q/addressbalance/{address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return int(response.text)
    except:
        pass
    
    # Tentar Blockstream.info como fallback
    try:
        url = f"https://blockstream.info/api/address/{address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            funded = data['chain_stats']['funded_txo_sum']
            spent = data['chain_stats']['spent_txo_sum']
            return funded - spent
    except:
        pass
    
    return -1 # Erro na consulta

df = pd.read_csv("consolidated_wallets.csv")
print(f"Iniciando validação de {len(df)} endereços...")

balances = []
for i, row in df.iterrows():
    addr = str(row['address']).strip()
    balance = get_balance(addr)
    balances.append(balance)
    
    if balance > 0:
        print(f"ACHADO: {addr} tem {balance} satoshis!")
    
    # Respeitar rate limits
    if (i + 1) % 5 == 0:
        time.sleep(1)
    if (i + 1) % 50 == 0:
        print(f"Processados {i+1}/{len(df)}...")

df['balance_satoshi'] = balances
df.to_csv("wallets_with_balances.csv", index=False)
print("Validação concluída e salva em wallets_with_balances.csv")
