#!/usr/bin/env python3
"""
BAIT Foundry Project Setup Script
Initializes Foundry project, installs dependencies, and compiles contracts.
Run after cloning the repo.
"""

import os
import subprocess
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts"

def run(cmd, cwd=None, check=True):
    """Run a shell command and print output."""
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    if check and result.returncode != 0:
        print(f"  ERROR: Command failed with code {result.returncode}")
    return result

def check_foundry():
    """Check if Foundry is installed."""
    result = run("forge --version", check=False)
    if result.returncode != 0:
        print("\n⚠️  Foundry not installed. Install with:")
        print("  curl -L https://foundry.paradigm.xyz | bash")
        print("  foundryup")
        return False
    return True

def init_foundry_project():
    """Initialize Foundry project structure if not already present."""
    print("\n📦 [1/5] Verificando estrutura Foundry...")
    
    required_dirs = ["src", "script", "test", "lib"]
    for d in required_dirs:
        (CONTRACTS_DIR / d).mkdir(exist_ok=True)
        print(f"  ✓ contracts/{d}/")
    
    # Check foundry.toml
    toml_path = CONTRACTS_DIR / "foundry.toml"
    if toml_path.exists():
        print(f"  ✓ foundry.toml exists")
    else:
        print(f"  ✗ foundry.toml missing — creating default")
        toml_path.write_text("""[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc_version = "0.8.20"
optimizer = true
optimizer_runs = 200
via_ir = false

[profile.default.fuzz]
runs = 256
max_test_rejects = 65536

[profile.ci]
fuzz = { runs = 1024 }
""")

def install_dependencies():
    """Install forge-std and openzeppelin-contracts."""
    print("\n📦 [2/5] Instalando dependências Foundry...")
    
    lib_dir = CONTRACTS_DIR / "lib"
    
    # forge-std
    forge_std = lib_dir / "forge-std"
    if forge_std.exists():
        print("  ✓ forge-std already installed")
    else:
        run("forge install foundry-rs/forge-std --no-commit", cwd=str(CONTRACTS_DIR), check=False)
        if forge_std.exists():
            print("  ✓ forge-std installed")
        else:
            print("  ⚠️  forge-std install failed — will need manual install")
    
    # openzeppelin-contracts
    oz = lib_dir / "openzeppelin-contracts"
    if oz.exists():
        print("  ✓ openzeppelin-contracts already installed")
    else:
        run("forge install OpenZeppelin/openzeppelin-contracts --no-commit", cwd=str(CONTRACTS_DIR), check=False)
        if oz.exists():
            print("  ✓ openzeppelin-contracts installed (v5.x)")
        else:
            print("  ⚠️  openzeppelin-contracts install failed — will need manual install")

def compile_contracts():
    """Compile contracts with forge build."""
    print("\n🔨 [3/5] Compilando contratos...")
    result = run("forge build", cwd=str(CONTRACTS_DIR), check=False)
    if result.returncode == 0:
        print("  ✓ Compilação bem-sucedida!")
    else:
        print("  ⚠️  Compilação falhou (deps podem estar faltando)")

def run_tests():
    """Run forge test."""
    print("\n🧪 [4/5] Rodando testes Foundry...")
    result = run("forge test --summary", cwd=str(CONTRACTS_DIR), check=False)
    if result.returncode == 0:
        print("  ✓ Todos os testes passaram!")
    else:
        print("  ⚠️  Alguns testes falharam (verifique output acima)")

def generate_deployment_env():
    """Generate .env.example for deployment."""
    print("\n🔐 [5/5] Gerando .env.example...")
    
    env_example = CONTRACTS_DIR / ".env.example"
    if env_example.exists():
        print("  ✓ .env.example already exists")
        return
    
    env_example.write_text("""# BAIT Foundry Deployment Environment
# Copy this to .env and fill in your values
# NEVER commit .env to git!

# Sepolia Testnet
SEPOLIA_RPC_URL=https://rpc.sepolia.org
DEPLOYER_PRIVATE_KEY=0x0000000000000000000000000000000000000000000000000000000000000000

# Ethereum Mainnet (USE WITH EXTREME CAUTION)
MAINNET_RPC_URL=https://eth.llamarpc.com
MAINNET_DEPLOYER_KEY=0x0000000000000000000000000000000000000000000000000000000000000000

# Etherscan API Key (for verification)
ETHERSCAN_API_KEY=YOUR_API_KEY_HERE

# Bridge Multisig Signers (3-of-5)
BRIDGE_SIGNER_1=0x0000000000000000000000000000000000000001
BRIDGE_SIGNER_2=0x0000000000000000000000000000000000000002
BRIDGE_SIGNER_3=0x0000000000000000000000000000000000000003
BRIDGE_SIGNER_4=0x0000000000000000000000000000000000000004
BRIDGE_SIGNER_5=0x0000000000000000000000000000000000000005

# Uniswap V3
UNISWAP_V3_FACTORY=0x1F98431f89416F6b6ACD4e8b4E0308A2DBb6f2e6
UNISWAP_V3_POSITION_MANAGER=0xC36442b4a45252C9A0f87E5D9a0570C16A4824a3
WETH=0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
""")
    print("  ✓ .env.example created")

def main():
    print("=" * 60)
    print("  BAIT Foundry Project Setup")
    print("  b'AI'tcoin — Contracts & Deployment")
    print("=" * 60)
    
    foundry_available = check_foundry()
    
    init_foundry_project()
    
    if foundry_available:
        install_dependencies()
        compile_contracts()
        run_tests()
    else:
        print("\n⚠️  Pulando install/compile/test — Foundry não disponível")
        print("  Instale Foundry e rode este script novamente.")
    
    generate_deployment_env()
    
    print("\n" + "=" * 60)
    print("  Setup concluído!")
    print("=" * 60)
    print(f"""
  Próximos passos:
  1. cd {CONTRACTS_DIR}
  2. cp .env.example .env  # Configure suas chaves
  3. forge build           # Compile
  4. forge test            # Test
  5. forge script script/DeployBAIT.s.sol --rpc-url $SEPOLIA_RPC_URL --broadcast  # Deploy Sepolia
    """)

if __name__ == "__main__":
    main()
