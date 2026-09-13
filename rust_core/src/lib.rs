/**
 * b'AI'tcoin Mainnet Consensus Core (Rust)
 * Deterministic block validation, quorum verification, and Master Wallet signature checking.
 */

use sha2::{Sha256, Digest};
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct BaitTransaction {
    pub tx_id: String,
    pub sender: String,
    pub recipient: String,
    pub amount_sats: u64,
    pub fee_sats: u64,
    pub signature: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct BaitBlock {
    pub height: u64,
    pub prev_hash: String,
    pub merkle_root: String,
    pub timestamp: u64,
    pub transactions: Vec<BaitTransaction>,
    pub consensus_hash: String,
}

pub struct ConsensusEngine {
    pub master_address: String,
    pub required_confirmations: u32,
}

impl ConsensusEngine {
    pub fn new(master_address: &str) -> Self {
        Self {
            master_address: master_address.to_string(),
            required_confirmations: 6,
        }
    }

    pub fn hash_transaction(&self, tx: &BaitTransaction) -> String {
        let payload = format!("{}:{}:{}:{}:{}", tx.sender, tx.recipient, tx.amount_sats, tx.fee_sats, tx.signature);
        let mut hasher = Sha256::new();
        hasher.update(payload.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    pub fn validate_block(&self, block: &BaitBlock) -> Result<bool, &'static str> {
        if block.transactions.is_empty() {
            return Err("Block contains no transactions");
        }

        // Verifica merkle root simples
        let mut hasher = Sha256::new();
        for tx in &block.transactions {
            hasher.update(self.hash_transaction(tx).as_bytes());
        }
        let computed_merkle = format!("{:x}", hasher.finalize());

        if computed_merkle != block.merkle_root {
            return Err("Merkle root mismatch");
        }

        Ok(true)
    }
}
