import pandas as pd
import requests
import time
import concurrent.futures
import os

def get_balance_blockchain_info(address):
    try:
        url = f"https://blockchain.info/q/addressbalance/{address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return int(response.text)
    except:
        pass
    return None

def get_balance_blockstream(address):
    try:
        url = f"https://blockstream.info/api/address/{address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['chain_stats']['funded_txo_sum'] - data['chain_stats']['spent_txo_sum']
    except:
        pass
    return None

def get_balance_blockcypher(address):
    try:
        url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()['balance']
    except:
        pass
    return None

def validate_address(address):
    if not address or pd.isna(address) or address == 'nan':
        return 0
    
    address = str(address).strip()
    if len(address) < 26:
        return 0
        
    # Tentar APIs em sequência para garantir redundância
    balance = get_balance_blockchain_info(address)
    if balance is None:
        balance = get_balance_blockstream(address)
    if balance is None:
        balance = get_balance_blockcypher(address)
        
    return balance if balance is not None else -1

def main():
    if not os.path.exists("consolidated_wallets.csv"):
        print("Arquivo consolidated_wallets.csv não encontrado.")
        return

    df = pd.read_csv("consolidated_wallets.csv")
    print(f"Iniciando validação profunda de {len(df)} registros...")
    
    results = []
    # Usar ThreadPoolExecutor para paralelismo moderado respeitando rate limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_idx = {executor.submit(validate_address, row['address']): i for i, row in df.iterrows()}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_idx)):
            idx = future_to_idx[future]
            try:
                balance = future.result()
                results.append({
                    'index': idx,
                    'balance_satoshi': balance
                })
            except Exception as e:
                results.append({'index': idx, 'balance_satoshi': -2})
            
            if (i + 1) % 50 == 0:
                print(f"Progresso: {i+1}/{len(df)} processados...")
            
            # Pequeno delay para evitar bloqueio agressivo por IP
            time.sleep(0.1)

    # Mapear resultados de volta ao dataframe original
    res_df = pd.DataFrame(results).set_index('index')
    df = df.join(res_df)
    
    df.to_csv("final_validated_wallets.csv", index=False)
    
    found = df[df['balance_satoshi'] > 0]
    print(f"\nVarredura concluída!")
    print(f"Total processado: {len(df)}")
    print(f"Endereços com saldo positivo: {len(found)}")
    if not found.empty:
        print(found[['address', 'balance_satoshi']])

if __name__ == "__main__":
    main()
