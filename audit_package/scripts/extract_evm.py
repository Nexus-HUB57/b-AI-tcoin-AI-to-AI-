import os
import re
import pandas as pd
import json

def extract_evm_data(text):
    # Regex para endereços Ethereum/EVM (0x seguido de 40 caracteres hex)
    evm_addr_pattern = r'\b0x[a-fA-F0-9]{40}\b'
    # Regex para chaves privadas EVM (64 caracteres hex, opcionalmente com 0x)
    evm_key_pattern = r'\b(?:0x)?[a-fA-F0-9]{64}\b'
    
    addresses = re.findall(evm_addr_pattern, text)
    keys = re.findall(evm_key_pattern, text)
    
    return list(set(addresses)), list(set(keys))

def process_file(file_path):
    results = []
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        content = ""
        if ext in ['.csv', '.xlsx', '.xls']:
            if ext == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            content = df.to_string()
        elif ext == '.json':
            with open(file_path, 'r') as f:
                content = json.dumps(json.load(f))
        else:
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
        
        addrs, keys = extract_evm_data(content)
        for a in addrs: results.append({'address': a, 'type': 'EVM', 'source': file_path})
        for k in keys: results.append({'private_key': k, 'type': 'EVM_KEY', 'source': file_path})
            
    except Exception as e:
        print(f"Erro ao processar {file_path}: {e}")
        
    return results

files = [
    "/home/ubuntu/upload/electrum-private-keys.csv",
    "/home/ubuntu/upload/privatekeys.txt",
    "/home/ubuntu/upload/priv.key.rtf",
    "/home/ubuntu/upload/electrum-private-keys2zero.csv",
    "/home/ubuntu/upload/electrum-private-keys3zero.csv",
    "/home/ubuntu/upload/electrum-private-keys08.03.csv",
    "/home/ubuntu/upload/electrum-private-keys09.03.csv",
    "/home/ubuntu/upload/electrum-private-keys09.03xprv.csv",
    "/home/ubuntu/upload/electrum-private-keyswallet0.csv",
    "/home/ubuntu/upload/keys(1).xlsx",
    "/home/ubuntu/upload/keys.json",
    "/home/ubuntu/upload/keys.xlsx"
]

all_evm = []
for f in files:
    if os.path.exists(f):
        all_evm.extend(process_file(f))

if all_evm:
    df_evm = pd.DataFrame(all_evm).drop_duplicates()
    df_evm.to_csv("evm_extracted_data.csv", index=False)
    print(f"Total de registros EVM extraídos: {len(df_evm)}")
else:
    print("Nenhum registro EVM encontrado.")
