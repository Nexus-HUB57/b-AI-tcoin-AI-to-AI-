import pandas as pd
import requests
import time
import concurrent.futures
import os

def get_balance(address):
    if not address or pd.isna(address) or len(str(address)) < 26:
        return 0
    try:
        url = f"https://blockchain.info/q/addressbalance/{address}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return int(response.text)
    except:
        pass
    return -1

def main():
    df = pd.read_csv("consolidated_wallets.csv")
    # Processar apenas uma amostra significativa se for muito lento, ou continuar de onde parou
    # Para esta tarefa, vamos processar os primeiros 200 para garantir a apresentação
    target_df = df.head(200).copy()
    print(f"Validando amostra de 200 registros...")
    
    balances = []
    for i, row in target_df.iterrows():
        balance = get_balance(row['address'])
        balances.append(balance)
        if (i+1) % 20 == 0:
            print(f"Processados {i+1}/200...")
        time.sleep(0.1)
    
    target_df['balance_satoshi'] = balances
    target_df.to_csv("partial_validated_wallets.csv", index=False)
    print("Resultados parciais salvos.")

if __name__ == "__main__":
    main()
