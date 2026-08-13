import pandas as pd
import requests
import time
import concurrent.futures

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
# Filtrar endereços que parecem válidos
df = df[df['address'].str.len() > 25].copy()

print(f"Validando {len(df)} endereços em paralelo...")

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    future_to_addr = {executor.submit(get_balance, str(row['address']).strip()): row for _, row in df.iterrows()}
    for future in concurrent.futures.as_completed(future_to_addr):
        row = future_to_addr[future]
        try:
            balance = future.result()
            results.append({
                'address': row['address'],
                'private_key': row['private_key'],
                'source': row['source'],
                'balance_satoshi': balance
            })
        except Exception as exc:
            results.append({
                'address': row['address'],
                'private_key': row['private_key'],
                'source': row['source'],
                'balance_satoshi': -1
            })

df_final = pd.DataFrame(results)
df_final.to_csv("wallets_validated_fast.csv", index=False)
found = df_final[df_final['balance_satoshi'] > 0]
print(f"Concluído. Encontrados {len(found)} endereços com saldo.")
if len(found) > 0:
    print(found[['address', 'balance_satoshi']])
