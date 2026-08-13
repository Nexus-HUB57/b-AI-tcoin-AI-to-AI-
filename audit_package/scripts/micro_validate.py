import pandas as pd
import requests
import time

def get_balance(address):
    try:
        url = f"https://blockchain.info/q/addressbalance/{address}"
        response = requests.get(url, timeout=3)
        return int(response.text) if response.status_code == 200 else 0
    except:
        return 0

df = pd.read_csv("consolidated_wallets.csv")
sample = df.head(20).copy()
balances = []
for addr in sample['address']:
    balances.append(get_balance(addr))
    time.sleep(0.1)
sample['balance_satoshi'] = balances
sample.to_csv("micro_results.csv", index=False)
print("Micro validação concluída.")
