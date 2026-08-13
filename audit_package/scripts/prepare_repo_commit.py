import os
import shutil
import subprocess

# Copiar consolidated_wallets.csv para AI_Store e b-AI-tcoin-AI-to-AI-
repos = ['AI_Store', 'b-AI-tcoin-AI-to-AI-']

for repo in repos:
    if os.path.exists(repo):
        # Criar diretório dedicado para relatórios de carteiras se não existir
        target_dir = os.path.join(repo, 'wallet_reports')
        os.makedirs(target_dir, exist_ok=True)
        
        # Copiar arquivo consolidado
        shutil.copy('consolidated_wallets.csv', os.path.join(target_dir, 'consolidated_wallets.csv'))
        print(f"Copiado para {target_dir}")

print("Preparação para commit concluída com sucesso.")
