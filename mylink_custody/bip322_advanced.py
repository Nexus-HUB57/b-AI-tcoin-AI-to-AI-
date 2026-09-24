"""Bounded BIP-322 verification for standard multisig and Taproot script-path.

This module intentionally accepts only audited templates; it is not a general
Bitcoin script interpreter. It verifies virtual BIP-322 signatures without
broadcasting or holding private keys.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import Sequence

from coincurve import PublicKey, PublicKeyXOnly


class BIP322AdvancedError(ValueError):
    pass


def dsha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def tagged(tag: str, b: bytes) -> bytes:
    t=hashlib.sha256(tag.encode()).digest(); return hashlib.sha256(t+t+b).digest()


def varint(n: int) -> bytes:
    if n < 253: return bytes([n])
    if n <= 0xffff: return b"\xfd"+struct.pack("<H",n)
    if n <= 0xffffffff: return b"\xfe"+struct.pack("<I",n)
    return b"\xff"+struct.pack("<Q",n)


def bip322_message_hash(message: str) -> bytes:
    if not message or len(message.encode()) > 10000: raise BIP322AdvancedError("invalid message")
    return tagged("BIP0322-signed-message", message.encode())


def make_to_spend(script_pubkey: bytes, message: str) -> bytes:
    ss=b"\x00\x20"+bip322_message_hash(message)
    return struct.pack("<I",0)+b"\x01"+b"\0"*32+struct.pack("<I",0xffffffff)+varint(len(ss))+ss+struct.pack("<I",0)+b"\x01"+struct.pack("<Q",0)+varint(len(script_pubkey))+script_pubkey+struct.pack("<I",0)


def parse_witness(raw: bytes) -> list[bytes]:
    if not raw: raise BIP322AdvancedError("empty witness")
    n=raw[0]; p=1; out=[]
    for _ in range(n):
        if p >= len(raw): raise BIP322AdvancedError("truncated witness")
        size=raw[p]; p+=1
        if size == 253 or p+size > len(raw): raise BIP322AdvancedError("non-minimal or truncated witness")
        out.append(raw[p:p+size]); p+=size
    if p != len(raw): raise BIP322AdvancedError("trailing witness bytes")
    return out


def multisig_template(script: bytes) -> tuple[int,list[bytes]]:
    # OP_m, compressed pubkeys, OP_n, OP_CHECKMULTISIG.
    if len(script) < 3 or not 0x51 <= script[0] <= 0x60 or script[-1] != 0xae:
        raise BIP322AdvancedError("unsupported multisig script template")
    m=script[0]-0x50; p=1; keys=[]
    while p < len(script)-2:
        size=script[p]; p+=1
        if size != 33 or p+size > len(script): raise BIP322AdvancedError("only compressed multisig keys supported")
        keys.append(script[p:p+size]); p+=size
    if p+2 != len(script) or script[p] != 0x50+len(keys) or not 1 <= m <= len(keys) <= 16:
        raise BIP322AdvancedError("invalid multisig threshold")
    return m, keys


def p2wsh_sighash(to_spend: bytes, witness_script: bytes) -> bytes:
    outpoint=dsha256(to_spend)+struct.pack("<I",0)
    output=struct.pack("<Q",0)+b"\x01\x6a"
    payload=(struct.pack("<I",0)+dsha256(outpoint)+dsha256(struct.pack("<I",0))+outpoint+varint(len(witness_script))+witness_script+struct.pack("<Q",0)+struct.pack("<I",0)+dsha256(output)+struct.pack("<I",0)+struct.pack("<I",1))
    return dsha256(payload)


def verify_p2wsh_multisig(*, message: str, witness_raw: bytes, witness_program: bytes) -> bool:
    witness=parse_witness(witness_raw)
    if len(witness) < 3: raise BIP322AdvancedError("multisig witness is too short")
    script=witness[-1]
    if hashlib.sha256(script).digest() != witness_program: raise BIP322AdvancedError("witness script hash mismatch")
    m, keys=multisig_template(script)
    sigs=witness[1:-1]
    if len(sigs) != m: raise BIP322AdvancedError("signature count differs from threshold")
    digest=p2wsh_sighash(make_to_spend(b"\x00\x20"+witness_program,message),script)
    key_index=0
    for sig in sigs:
        if len(sig)<2 or sig[-1] != 1: return False
        verified=False
        while key_index < len(keys):
            try: verified=PublicKey(keys[key_index]).verify(sig[:-1],digest,hasher=None)
            except Exception: verified=False
            key_index += 1
            if verified: break
        if not verified: return False
    return True


def tapleaf_hash(script: bytes, leaf_version: int = 0xc0) -> bytes:
    if leaf_version & 1 or leaf_version < 0xc0 or leaf_version > 0xfe: raise BIP322AdvancedError("invalid TapLeaf version")
    return tagged("TapLeaf", bytes([leaf_version])+varint(len(script))+script)


def taproot_output_key(internal_key: bytes, merkle_root: bytes) -> tuple[bytes,bool]:
    if len(internal_key)!=32 or len(merkle_root) not in (0,32): raise BIP322AdvancedError("invalid Taproot control data")
    x=PublicKeyXOnly(internal_key)
    tweak=tagged("TapTweak",internal_key+merkle_root)
    try: x.tweak_add(tweak)
    except Exception as exc: raise BIP322AdvancedError("invalid Taproot tweak") from exc
    return x.format(), bool(x.parity)


def taproot_script_sighash(to_spend: bytes, output_key: bytes, script: bytes,
                           signature: bytes) -> bytes:
    if len(output_key) != 32 or len(signature) not in (64, 65):
        raise BIP322AdvancedError("invalid Taproot script-path signature")
    hash_type = signature[64] if len(signature) == 65 else 0
    if hash_type not in (0, 1): raise BIP322AdvancedError("only SIGHASH_DEFAULT/ALL supported")
    outpoint = dsha256(to_spend) + struct.pack("<I", 0)
    script_pubkey = b"\x51\x20" + output_key
    prevouts = hashlib.sha256(outpoint).digest()
    amounts = hashlib.sha256(struct.pack("<Q", 0)).digest()
    scripts = hashlib.sha256(varint(len(script_pubkey)) + script_pubkey).digest()
    sequences = hashlib.sha256(struct.pack("<I", 0)).digest()
    outputs = hashlib.sha256(struct.pack("<Q", 0) + b"\x01\x6a").digest()
    spend_type = 2  # ext_flag=1 (script path), no annex
    msg = (bytes([0, hash_type]) + prevouts + amounts + scripts + sequences + outputs
           + bytes([spend_type]) + struct.pack("<I", 0) + tapleaf_hash(script)
           + b"\x00" + struct.pack("<I", 0xffffffff))
    return tagged("TapSighash", msg)


def verify_taproot_script_path(*, message: str, witness_raw: bytes, output_key: bytes) -> bool:
    """Verify a key-path-independent Taproot proof for standard CHECKSIG script.

    Supported script template is `<xonly-pubkey> OP_CHECKSIG` and the control
    block must prove the script commits to the supplied 32-byte output key.
    """
    witness=parse_witness(witness_raw)
    if len(witness) != 3: raise BIP322AdvancedError("expected signature, script, control block")
    sig, script, control=witness
    if len(output_key)!=32 or len(control)<33 or (len(control)-33)%32: raise BIP322AdvancedError("invalid Taproot script-path data")
    leaf_version=control[0]&0xfe; parity=control[0]&1; internal=control[1:33]
    if len(script)!=34 or script[0]!=32 or script[-1]!=0xac: raise BIP322AdvancedError("only xonly CHECKSIG script supported")
    leaf=tapleaf_hash(script,leaf_version); root=leaf
    for i in range(33,len(control),32): root=tagged("TapBranch",min(root,control[i:i+32])+max(root,control[i:i+32]))
    derived, derived_parity=taproot_output_key(internal,root)
    if derived != output_key or derived_parity != bool(parity): raise BIP322AdvancedError("control block does not commit to output key")
    if len(sig) not in (64, 65): raise BIP322AdvancedError("invalid Schnorr signature")
    digest=taproot_script_sighash(make_to_spend(b"\x51\x20"+output_key,message),output_key,script,sig)
    return PublicKeyXOnly(script[1:33]).verify(sig[:64],digest)
