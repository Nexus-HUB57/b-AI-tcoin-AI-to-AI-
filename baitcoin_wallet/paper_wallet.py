r"""
b'AI'tcoin Paper Wallet Generator.

Genera carteiras de papel offline para armazenamento frio de BAIT,
desenhadas para agentes AI. Inclui chave privada, chave publica,
endereco b'AI'tcoin, e HTML formatado para impressao em A4.

Funcoes:
  - generate_paper_wallet() -> dict
  - generate_paper_wallet_html(wallet_data) -> str
  - generate_paper_wallet_pdf_bytes(wallet_data) -> bytes  (fallback HTML)
"""

import os
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, Any

import ecdsa


# ==========================================================================
# Base58 encoding (same as baitcoin_explorer.indices)
# ==========================================================================

_BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def _base58_encode(data: bytes) -> str:
    r"""Base58 encode bytes."""
    n = int.from_bytes(data, 'big')
    result = ''
    while n > 0:
        n, r = divmod(n, 58)
        result = _BASE58_ALPHABET[r] + result
    for byte in data:
        if byte == 0:
            result = '1' + result
        else:
            break
    return result


def _pubkey_to_bait_address(pubkey_hex: str) -> str:
    r"""Converte pubkey hex para endereco b'AI'tcoin (unified BAITAddress).

    Phase A: Uses the unified BAITAddress system (Hash160 + Base58Check).
    Strips compression prefix from 33-byte compressed pubkeys.
    """
    try:
        pubkey_bytes = bytes.fromhex(pubkey_hex) if len(pubkey_hex) <= 128 else bytes.fromhex(pubkey_hex[:128])
        # Schnorr/BIP-340 uses x-only (32 bytes). Strip compression prefix if present.
        if len(pubkey_bytes) == 33 and pubkey_bytes[0] in (0x02, 0x03):
            pubkey_bytes = pubkey_bytes[1:33]
    except (ValueError, TypeError):
        return f"b'unknown_{hashlib.sha256(str(pubkey_hex).encode()).hexdigest()[:12]}"
    from baitcoin_core.blockchain.addresses import pubkey_to_address
    return pubkey_to_address(pubkey_bytes)


# ==========================================================================
# QR-like ASCII art placeholder
# ==========================================================================

def _ascii_qr_placeholder(data: str, label: str = "") -> str:
    r"""Generate an ASCII art QR-like placeholder box."""
    # Create a deterministic pattern from the data
    h = hashlib.sha256(data.encode()).hexdigest()
    grid_w, grid_h = 21, 21  # Standard QR size for version 1
    grid = []
    for row in range(grid_h):
        line = []
        for col in range(grid_w):
            # Finder patterns (top-left, top-right, bottom-left)
            if (row < 7 and col < 7) or (row < 7 and col >= grid_w - 7) or (row >= grid_h - 7 and col < 7):
                # Outer border
                if row in (0, 6, grid_h - 1, grid_h - 7) or col in (0, 6, grid_w - 1, grid_w - 7):
                    line.append('██')
                # Inner border
                elif row in (2, 4, grid_h - 3, grid_h - 5) or col in (2, 4, grid_w - 3, grid_w - 5):
                    line.append('  ')
                else:
                    line.append('██')
            # Timing patterns
            elif row == 6 or col == 6:
                if (row + col) % 2 == 0:
                    line.append('██')
                else:
                    line.append('  ')
            else:
                # Deterministic fill from hash
                idx = (row * grid_w + col) % len(h)
                if int(h[idx], 16) < 8:
                    line.append('██')
                else:
                    line.append('  ')
        grid.append(''.join(line))

    lines = []
    if label:
        lines.append(f"    ┌{'─' * (grid_w * 2 + 2)}┐")
        lines.append(f"    │ {'QR: ' + label:<{grid_w * 2}} │")
        lines.append(f"    ├{'─' * (grid_w * 2 + 2)}┤")
    else:
        lines.append(f"┌{'─' * (grid_w * 2 + 2)}┐")

    for row in grid:
        if label:
            lines.append(f"    │ {row} │")
        else:
            lines.append(f"│ {row} │")

    if label:
        lines.append(f"    └{'─' * (grid_w * 2 + 2)}┘")
    else:
        lines.append(f"└{'─' * (grid_w * 2 + 2)}┘")

    return '\n'.join(lines)


# ==========================================================================
# Core generation
# ==========================================================================

def generate_paper_wallet() -> Dict[str, Any]:
    r"""Generate a new b'AI'tcoin paper wallet.

    Returns dict with:
      - private_key: hex string (64 chars, secp256k1)
      - public_key: hex string (33 chars, compressed)
      - public_key_uncompressed: hex string (65 chars)
      - address: b'AI'tcoin address (bait + Base58Check)
      - qr_placeholder_address: ASCII art QR placeholder for address
      - qr_placeholder_private: ASCII art QR placeholder for private key
      - timestamp: ISO 8601 UTC creation time
      - warning: security warning message
    """
    # Generate secp256k1 keypair
    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    vk = sk.get_verifying_key()

    # Private key (32 bytes -> 64 hex chars)
    private_key_hex = sk.to_string().hex()

    # Verifying key raw bytes (64 bytes: x || y)
    vk_raw = vk.to_string()
    x_bytes = vk_raw[:32]  # 32 bytes
    y_bytes = vk_raw[32:]  # 32 bytes

    # Public key - compressed format (33 bytes -> 66 hex chars)
    prefix = b'\x02' if y_bytes[-1] % 2 == 0 else b'\x03'
    public_key_hex = (prefix + x_bytes).hex()

    # Public key - uncompressed format (65 bytes -> 130 hex chars)
    public_key_uncompressed_hex = ('04' + vk_raw.hex())

    # Compute b'AI'tcoin address
    address = _pubkey_to_bait_address(public_key_hex)

    # Timestamp
    now = datetime.now(timezone.utc)
    timestamp_iso = now.isoformat()
    timestamp_unix = now.timestamp()

    return {
        'private_key': private_key_hex,
        'public_key': public_key_hex,
        'public_key_uncompressed': public_key_uncompressed_hex,
        'address': address,
        'qr_placeholder_address': _ascii_qr_placeholder(address, 'Address'),
        'qr_placeholder_private': _ascii_qr_placeholder(private_key_hex, 'Private Key'),
        'timestamp': timestamp_iso,
        'timestamp_unix': timestamp_unix,
        'warning': (
            "WARNING: This private key grants full control over the funds at this address. "
            "Never share it with anyone. Store this paper wallet in a secure, offline location. "
            "If the private key is compromised, your BAIT tokens can be stolen."
        ),
    }


# ==========================================================================
# HTML generation
# ==========================================================================

def generate_paper_wallet_html(wallet_data: Dict[str, Any]) -> str:
    r"""Generate a standalone HTML page for printing a paper wallet.

    Features:
    - Dark theme with b'AI'tcoin branding (orange #ff6b35 / teal #00d4aa gradient)
    - A4 print-friendly layout with @media print rules (monochrome)
    - Side-by-side PUBLIC and PRIVATE sections
    - ASCII QR placeholder boxes
    - Footer with timestamp and "For AI Agent offline cold storage"
    """
    ts = wallet_data.get('timestamp', datetime.now(timezone.utc).isoformat())
    addr = wallet_data.get('address', '')
    pubkey = wallet_data.get('public_key', '')
    privkey = wallet_data.get('private_key', '')
    qr_addr = wallet_data.get('qr_placeholder_address', '')
    qr_priv = wallet_data.get('qr_placeholder_private', '')
    warning = wallet_data.get('warning', '')

    # Escape for HTML
    def esc(s):
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    qr_addr_escaped = esc(qr_addr).replace('\n', '&#10;')
    qr_priv_escaped = esc(qr_priv).replace('\n', '&#10;')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>b'AI'tcoin Paper Wallet</title>
<style>
  @page {{
    size: A4;
    margin: 15mm;
  }}

  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }}

  body {{
    font-family: 'Courier New', 'Consolas', 'Monaco', monospace;
    background: #0a0a0f;
    color: #e0e0e0;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px;
  }}

  .wallet-container {{
    width: 100%;
    max-width: 800px;
    background: linear-gradient(145deg, #0d0d14, #111118);
    border: 2px solid transparent;
    border-image: linear-gradient(145deg, #ff6b35, #00d4aa) 1;
    border-radius: 4px;
    padding: 30px;
    box-shadow: 0 0 40px rgba(255, 107, 53, 0.1), 0 0 40px rgba(0, 212, 170, 0.05);
  page-break-inside: avoid;
  }}

  .header {{
    text-align: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 2px solid;
    border-image: linear-gradient(90deg, #ff6b35, #00d4aa) 1;
  }}

  .header h1 {{
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(90deg, #ff6b35, #00d4aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 6px;
  }}

  .header .subtitle {{
    font-size: 12px;
    color: #666;
    letter-spacing: 3px;
    text-transform: uppercase;
  }}

  .sections {{
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
  }}

  .section {{
    flex: 1;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 20px;
    background: #0a0a10;
    page-break-inside: avoid;
  }}

  .section.public {{
    border-color: #00d4aa33;
  }}

  .section.private {{
    border-color: #ff6b3533;
  }}

  .section-label {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 14px;
    padding-bottom: 8px;
  }}

  .section.public .section-label {{
    color: #00d4aa;
    border-bottom: 1px solid #00d4aa33;
  }}

  .section.private .section-label {{
    color: #ff6b35;
    border-bottom: 1px solid #ff6b3533;
  }}

  .field {{
    margin-bottom: 14px;
  }}

  .field-label {{
    font-size: 10px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
  }}

  .field-value {{
    font-size: 13px;
    word-break: break-all;
    line-height: 1.5;
    color: #d0d0d0;
    padding: 8px;
    background: #08080c;
    border-radius: 4px;
    border: 1px solid #1a1a24;
  }}

  .section.private .field-value {{
    color: #ff6b35;
    border-color: #ff6b3522;
    }}

  .section.public .field-value {{
    color: #00d4aa;
    border-color: #00d4aa22;
  }}

  .qr-box {{
    margin-top: 10px;
    text-align: center;
    padding: 10px;
    background: #f5f5f5;
    border-radius: 4px;
    display: inline-block;
  }}

  .qr-box pre {{
    font-size: 4px;
    line-height: 4px;
    letter-spacing: 0;
    color: #000;
  }}

  .warning-box {{
    margin-top: 20px;
    padding: 14px 18px;
    background: rgba(255, 50, 50, 0.08);
    border: 1px solid rgba(255, 50, 50, 0.3);
    border-radius: 6px;
    color: #ff6b6b;
    font-size: 11px;
    line-height: 1.6;
    page-break-inside: avoid;
  }}

  .warning-box .warning-icon {{
    font-weight: 700;
    margin-right: 6px;
  }}

  .footer {{
    margin-top: 20px;
    padding-top: 14px;
    border-top: 1px solid #222;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 10px;
    color: #555;
  }}

  .footer .cold-storage {{
    color: #00d4aa;
    font-weight: 700;
    letter-spacing: 1px;
  }}

  /* Print rules */
  @media print {{
    body {{
      background: #fff;
      color: #000;
      padding: 0;
    }}

    .wallet-container {{
      background: #fff;
      border: 2px solid #000;
      border-image: none;
      box-shadow: none;
      padding: 20px;
    }}

    .header h1 {{
      -webkit-text-fill-color: #000;
      color: #000;
    }}

    .header .subtitle {{
      color: #666;
    }}

    .header {{
      border-bottom-color: #000;
      border-image: none;
      border-bottom: 2px solid #000;
    }}

    .section {{
      background: #fff;
      border-color: #333;
    }}

    .section.public, .section.private {{
      border-color: #333;
    }}

    .section-label {{
      color: #000 !important;
      border-bottom-color: #000 !important;
    }}

    .field-value {{
      background: #f8f8f8;
      border-color: #ccc;
      color: #000 !important;
    }}

    .warning-box {{
      background: #fff8f0;
      border-color: #cc0000;
      color: #333;
    }}

    .footer {{
      border-top-color: #ccc;
      color: #666;
    }}

    .footer .cold-storage {{
      color: #000;
    }}

    .qr-box {{
      background: #fff;
      border: 1px solid #ccc;
    }}

    .qr-box pre {{
      color: #000;
    }}
  }}
</style>
</head>
<body>
<div class="wallet-container">
  <div class="header">
    <h1>b'AI'tcoin Paper Wallet</h1>
    <div class="subtitle">Offline Cold Storage for AI Agents</div>
  </div>

  <div class="sections">
    <!-- PUBLIC SECTION -->
    <div class="section public">
      <div class="section-label">Public (Share)</div>
      <div class="field">
        <div class="field-label">Address</div>
        <div class="field-value">{esc(addr)}</div>
      </div>
      <div class="field">
        <div class="field-label">Public Key (Compressed)</div>
        <div class="field-value">{esc(pubkey)}</div>
      </div>
      <div style="text-align: center;">
        <div class="qr-box">
          <pre>{qr_addr_escaped}</pre>
        </div>
      </div>
    </div>

    <!-- PRIVATE SECTION -->
    <div class="section private">
      <div class="section-label">Private (Keep Secret)</div>
      <div class="field">
        <div class="field-label">Private Key</div>
        <div class="field-value">{esc(privkey)}</div>
      </div>
      <div style="text-align: center;">
        <div class="qr-box">
          <pre>{qr_priv_escaped}</pre>
        </div>
      </div>
    </div>
  </div>

  <div class="warning-box">
    <span class="warning-icon">&#9888;</span>
    {esc(warning)}
  </div>

  <div class="footer">
    <div class="cold-storage">For AI Agent Offline Cold Storage</div>
    <div>Created: {esc(ts)}</div>
  </div>
</div>
</body>
</html>"""
    return html


def generate_paper_wallet_pdf_bytes(wallet_data: Dict[str, Any]) -> bytes:
    r"""Return HTML bytes as a PDF fallback.

    PDF generation requires an external library (e.g. weasyprint, pdfkit).
    This function returns the HTML content as bytes, which can be:
      - Saved as .html and opened in a browser for "Print to PDF"
      - Passed to an external PDF converter
    """
    html = generate_paper_wallet_html(wallet_data)
    return html.encode('utf-8')
