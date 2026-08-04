r"""
b'AI'tcoin Difficulty Adjustment Algorithm (DAA).

Implements an asymptotic difficulty adjustment targeting 30s block time:
- Adjustment interval: 2016 blocks (~16.8 hours at 30s/block)
- Target block time: 30 seconds
- Max adjustment per period: 4x up or 0.25x down
- Uses median block time of the last N blocks to avoid outliers
- Prevents timestamp manipulation attacks

This replaces the static difficulty (0x1d00ffff) with a dynamic
system that responds to hash rate changes.
"""

import time
from typing import List, Optional
from baitcoin_core.blockchain.block import Block


# Protocol constants
TARGET_BLOCK_TIME = 30          # seconds
ADJUSTMENT_INTERVAL = 2016       # blocks between adjustments
MAX_ADJUSTMENT_FACTOR = 4       # max 4x increase per period
MIN_ADJUSTMENT_FACTOR = 0.25    # max 0.25x decrease per period
MIN_DIFFICULTY = 1               # absolute minimum
MEDIAN_WINDOW = 11               # blocks for median timestamp calculation


class DifficultyAdjuster:
    r"""Manages dynamic difficulty adjustment for the blockchain.

    Usage::
        da = DifficultyAdjuster(initial_bits=0x1d00ffff)
        
        # After every 2016 blocks:
        if da.should_adjust(chain_height):
            new_bits = da.calculate(chain)
    """

    def __init__(self, initial_bits: int = 0x1d00ffff):
        self.current_bits = initial_bits
        self.last_adjustment_height = 0
        self._adjustment_count = 0

    def should_adjust(self, chain_height: int) -> bool:
        r"""Check if difficulty should be adjusted at this height."""
        if chain_height == 0:
            return False
        periods_since_last = (chain_height - self.last_adjustment_height) // ADJUSTMENT_INTERVAL
        return periods_since_last >= 1

    def calculate(self, chain: List[Block]) -> int:
        r"""Calculate new difficulty bits based on recent block times.

        Algorithm:
        1. Get the actual time span of the last ADJUSTMENT_INTERVAL blocks
        2. Calculate target time span = ADJUSTMENT_INTERVAL * TARGET_BLOCK_TIME
        3. New difficulty = old difficulty * (actual / target)
        4. Clamp to [1/4x, 4x] of old difficulty
        5. Convert back to compact bits format

        Returns:
            New compact target bits.
        """
        if len(chain) < 2:
            return self.current_bits

        # Get the block range for adjustment
        end_idx = len(chain) - 1
        start_idx = max(0, end_idx - ADJUSTMENT_INTERVAL + 1)

        if end_idx - start_idx < 10:
            # Not enough blocks for meaningful adjustment
            return self.current_bits

        # Calculate actual time span using median timestamps
        actual_time = self._median_block_time(chain, start_idx, end_idx)
        target_time = (end_idx - start_idx) * TARGET_BLOCK_TIME

        if actual_time <= 0:
            actual_time = TARGET_BLOCK_TIME

        # Calculate adjustment ratio
        ratio = target_time / actual_time

        # Clamp adjustment
        ratio = max(MIN_ADJUSTMENT_FACTOR, min(MAX_ADJUSTMENT_FACTOR, ratio))

        # Calculate new target
        old_target = self._bits_to_target(self.current_bits)
        new_target = int(old_target / ratio)

        # Clamp to minimum
        new_target = max(new_target, MIN_DIFFICULTY)

        # Convert back to compact bits
        new_bits = self._target_to_bits(new_target)

        self.current_bits = new_bits
        self.last_adjustment_height = end_idx
        self._adjustment_count += 1

        return new_bits

    def _median_block_time(self, chain: List[Block],
                            start_idx: int, end_idx: int) -> float:
        r"""Calculate median block time using a sliding window.

        Uses the median of block-to-block intervals to filter
        out timestamp manipulation outliers.
        """
        intervals = []
        for i in range(start_idx + 1, end_idx + 1):
            interval = chain[i].header.timestamp - chain[i - 1].header.timestamp
            if 0 < interval < 7200:  # max 2 hours per block
                intervals.append(interval)

        if not intervals:
            return TARGET_BLOCK_TIME * (end_idx - start_idx)

        intervals.sort()
        median = intervals[len(intervals) // 2]
        return median * (end_idx - start_idx)

    @staticmethod
    def _bits_to_target(bits: int) -> int:
        r"""Convert compact 'bits' format to full target value.

        Compact format (from Bitcoin):
        - Byte 0: exponent (number of significant bytes)
        - Bytes 1-2: coefficient (first 2-3 significant bytes)
        target = coefficient * 256^(exponent - 3)
        """
        exponent = bits >> 24
        coefficient = bits & 0x007fffff
        if exponent <= 3:
            target = coefficient >> (8 * (3 - exponent))
        else:
            target = coefficient << (8 * (exponent - 3))
        return max(target, MIN_DIFFICULTY)

    @staticmethod
    def _target_to_bits(target: int) -> int:
        r"""Convert full target value to compact 'bits' format.
        """
        if target == 0:
            return 0x01000400  # easiest possible

        # Find the size (number of bytes needed)
        size = (target.bit_length() + 7) // 8

        # Clamp to 3-byte coefficient
        if size <= 3:
            coefficient = target << (8 * (3 - size))
            exponent = 3
        else:
            coefficient = target >> (8 * (size - 3))
            exponent = size

        if coefficient > 0x007fffff:
            coefficient >>= 8
            exponent += 1

        return (exponent << 24) | (coefficient & 0x007fffff)

    def get_difficulty_info(self, chain: List[Block]) -> dict:
        r"""Get current difficulty information for the API."""
        target = self._bits_to_target(self.current_bits)
        return {
            "current_bits": hex(self.current_bits),
            "target": hex(target),
            "target_difficulty": 0xffff0000000000000000000000000000000000000000000000000000000000 // target if target > 0 else 0,
            "adjustment_interval": ADJUSTMENT_INTERVAL,
            "target_block_time": TARGET_BLOCK_TIME,
            "last_adjustment_height": self.last_adjustment_height,
            "adjustment_count": self._adjustment_count,
            "max_adjustment_factor": MAX_ADJUSTMENT_FACTOR,
            "min_adjustment_factor": MIN_ADJUSTMENT_FACTOR,
        }
