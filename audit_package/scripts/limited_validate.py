import pandas as pd
import requests
import time

def get_balance(address):
    if not address or pd.isna(address) or address == 'nan' or len(str(address)) < 26:
        return 0
    try:
        url = f"https://blockchain.info/q/addressbalance/{address}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return int(response.text)
    except:
        pass
    return 0

df = pd.read_csv("consolidated_wallets.csv")
df = df[df['address'].str.len() > 25].head(100).copy()

print(f"Validando os primeiros 100 endereços promissores...")

balances = []
for i, row in df.iterrows():
    addr = str(row['address']).strip()
    balance = get_balance(addr)
    balances.append(balance)
    if balance > 0:
        print(f"ACHADO: {addr} = {balance}")
    time.sleep(0.2)

df['balance_satoshi'] = balances
df.to_csv("wallets_limited_results.csv", index=False)
print("Salvo em wallets_limited_results.csv")
