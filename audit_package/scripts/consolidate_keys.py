import os
import csv
import json
import re
import pandas as pd
from bs4 import BeautifulSoup

def extract_from_text(text):
    # Regex para endereços Bitcoin (Legacy, P2SH, Bech32)
    addr_pattern = r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|\b(bc1)[a-z0-9]{25,59}\b'
    # Regex para chaves privadas (WIF)
    key_pattern = r'\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b'
    
    addresses = re.findall(addr_pattern, text)
    # Addresses findall returns tuples for groups, flatten it
    addresses = [a[0] if isinstance(a, tuple) and a[0] else (a if isinstance(a, str) else '') for a in addresses]
    addresses = [a for a in addresses if a]
    
    keys = re.findall(key_pattern, text)
    
    return list(set(addresses)), list(set(keys))

def process_file(file_path):
    results = []
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.csv':
            df = pd.read_csv(file_path)
            # Tentar encontrar colunas 'address' e 'private_key'
            cols = df.columns.str.lower()
            addr_col = next((c for c in df.columns if 'addr' in c.lower()), None)
            key_col = next((c for c in df.columns if 'key' in c.lower() or 'priv' in c.lower()), None)
            
            for _, row in df.iterrows():
                addr = str(row[addr_col]) if addr_col else ""
                key = str(row[key_col]) if key_col else ""
                if addr or key:
                    results.append({'address': addr.strip(), 'private_key': key.strip(), 'source': file_path})
                    
        elif ext == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        addr = item.get('address') or item.get('addr', '')
                        key = item.get('private_key') or item.get('key', '') or item.get('priv', '')
                        results.append({'address': str(addr).strip(), 'private_key': str(key).strip(), 'source': file_path})
                elif isinstance(data, dict):
                    # Tentar encontrar chaves recursivamente ou chaves específicas
                    for k, v in data.items():
                        if isinstance(v, str):
                            addrs, keys = extract_from_text(v)
                            for a in addrs: results.append({'address': a, 'private_key': '', 'source': file_path})
                            for k_ in keys: results.append({'address': '', 'private_key': k_, 'source': file_path})
                            
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            addr_col = next((c for c in df.columns if 'addr' in c.lower()), None)
            key_col = next((c for c in df.columns if 'key' in c.lower() or 'priv' in c.lower()), None)
            for _, row in df.iterrows():
                addr = str(row[addr_col]) if addr_col else ""
                key = str(row[key_col]) if key_col else ""
                results.append({'address': addr.strip(), 'private_key': key.strip(), 'source': file_path})
                
        elif ext == '.rtf':
            # RTF é complexo, vamos tratar como texto bruto e limpar tags básicas ou usar regex
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                addrs, keys = extract_from_text(content)
                for a in addrs: results.append({'address': a, 'private_key': '', 'source': file_path})
                for k in keys: results.append({'address': '', 'private_key': k, 'source': file_path})
                
        else: # .txt e outros
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read()
                # Tentar encontrar pares endereço/chave por linha
                lines = content.splitlines()
                for line in lines:
                    addrs, keys = extract_from_text(line)
                    if addrs and keys:
                        results.append({'address': addrs[0], 'private_key': keys[0], 'source': file_path})
                    elif addrs:
                        for a in addrs: results.append({'address': a, 'private_key': '', 'source': file_path})
                    elif keys:
                        for k in keys: results.append({'address': '', 'private_key': k, 'source': file_path})
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

all_data = []
for f in files:
    if os.path.exists(f):
        all_data.extend(process_file(f))

# Remover duplicatas e salvar
df_final = pd.DataFrame(all_data).drop_duplicates(subset=['address', 'private_key'])
df_final.to_csv("consolidated_wallets.csv", index=False)
print(f"Total de registros únicos extraídos: {len(df_final)}")
