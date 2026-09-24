"""Explicit local-only test switches.

Production processes must not set BAIT_ALLOW_INSECURE_LOCAL. The flag exists
only so legacy unit fixtures can exercise state-machine behavior without real
relayer keys; tests covering authorization still provide real Ed25519 keys.
"""
import os

os.environ.setdefault("BAIT_ALLOW_INSECURE_LOCAL", "1")
