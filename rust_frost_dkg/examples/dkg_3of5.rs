//! Run: cargo run --example dkg_3of5
use bait_frost_dkg::{run_dkg_simulated, to_parity_gate_config};

fn main() {
    let results = run_dkg_simulated(5, 3).expect("DKG 3-of-5 failed");
    println!("Participants: {}", results.len());
    let pk = &results[0].group_pubkey_hex;
    println!("Group pubkey (demo): {}", pk);
    for r in &results {
        println!(
            "  participant {} share={}...",
            r.participant_id,
            &r.secret_share_hex[..16]
        );
    }
    let cfg = to_parity_gate_config(pk, 3);
    println!("\nParityGate config:\n{}", serde_json::to_string_pretty(&cfg).unwrap());
}
