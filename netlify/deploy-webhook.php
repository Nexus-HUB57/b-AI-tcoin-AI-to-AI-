<?php
/**
 * b'AI'tcoin Auto-Deploy Webhook
 * 
 * Receives POST from GitHub Actions and pulls latest files from GitHub.
 * Install at: public_html/deploy-webhook.php
 * 
 * GitHub Actions sends POST with a shared secret.
 * This script downloads files from GitHub raw URLs.
 * 
 * Security: validates HMAC-SHA256 signature before deploying.
 */

// Configuration
define('DEPLOY_SECRET', getenv('DEPLOY_SECRET') ?: 'baitcoin-deploy-2024'); // Must match GitHub secret
define('GITHUB_RAW_BASE', 'https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/');
define('REPO_API', 'https://api.github.com/repos/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/commits/main');

// Response helper
function respond($status, $message, $extra = []) {
    http_response_code($status);
    header('Content-Type: application/json');
    echo json_encode(array_merge(['status' => $status, 'message' => $message], $extra));
    exit;
}

// Log function
function deploy_log($msg) {
    $log_file = __DIR__ . '/deploy.log';
    $time = date('Y-m-d H:i:s');
    file_put_contents($log_file, "[$time] $msg\n", FILE_APPEND);
}

// Only allow POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(405, 'Method not allowed. Use POST.');
}

// Validate signature
$signature = $_SERVER['HTTP_X_DEPLOY_SIGNATURE'] ?? '';
$payload = file_get_contents('php://input');
$expected_sig = hash_hmac('sha256', $payload, DEPLOY_SECRET);

if (!hash_equals($expected_sig, $signature)) {
    deploy_log('FAILED: Invalid signature from ' . ($_SERVER['REMOTE_ADDR'] ?? 'unknown'));
    respond(403, 'Invalid signature');
}

deploy_log('=== Deploy triggered ===');

// Parse request
$input = json_decode($payload, true) ?: [];
$target = $input['target'] ?? 'frontend'; // frontend, api, or all

$base_dir = dirname(__DIR__); // /home/USER/
$public_html = __DIR__;
$baitcoin_api_dir = $base_dir . '/baitcoin-api';

$results = [];
$errors = [];

// --- Frontend Deploy ---
if ($target === 'frontend' || $target === 'all') {
    deploy_log('Deploying frontend...');
    
    $files = [
        'netlify/index.html'        => 'index.html',
        'netlify/bainkr.html'       => 'bainkr.html',
        'netlify/whitepaper.pdf'    => 'whitepaper.pdf',
    ];
    
    // .htaccess from a separate raw URL (not in repo root)
    $htaccess_url = GITHUB_RAW_BASE . 'netlify/.htaccess';
    
    foreach ($files as $src => $dest) {
        $url = GITHUB_RAW_BASE . $src;
        $local_path = $public_html . '/' . $dest;
        
        $ctx = stream_context_create(['http' => ['timeout' => 30, 'ignore_errors' => true]]);
        $data = @file_get_contents($url, false, $ctx);
        
        if ($data !== false && strlen($data) > 100) {
            $ok = @file_put_contents($local_path, $data);
            if ($ok) {
                $results[] = "OK: $dest (" . strlen($data) . " bytes)";
                deploy_log("  OK: $dest");
            } else {
                $errors[] = "Write failed: $dest";
                deploy_log("  FAIL: $dest - write error");
            }
        } else {
            $errors[] = "Download failed: $src";
            deploy_log("  FAIL: $src - download error");
        }
    }
}

// --- API/Daemon Deploy ---
if ($target === 'api' || $target === 'all') {
    deploy_log('Deploying API codebase...');
    
    // Download codebase tarball from GitHub release or generate on-the-fly
    // Since we can't easily get a tarball, we download key files individually
    
    $api_files = [
        'main_daemon.py',
        'requirements.txt',
        'daemon_production.py',
        'baitcoin_api/server.py',
        'baitcoin_api/__init__.py',
        'baitcoin_core/__init__.py',
        'baitcoin_core/blockchain/chain.py',
        'baitcoin_core/blockchain/block.py',
        'baitcoin_core/blockchain/mempool.py',
        'baitcoin_core/consensus/difficulty.py',
        'baitcoin_core/consensus/pouw.py',
        'baitcoin_core/cryptography/schnorr.py',
        'baitcoin_core/network/node.py',
        'baitcoin_core/network/gossip.py',
        'baitcoin_ai/marketplace/services.py',
        'baitcoin_token/erc20_like/bait_token.py',
        'baitcoin_bank/staking/pool.py',
        'baitcoin_wallet/keys/manager.py',
        'baitcoin_memory/store.py',
    ];
    
    if (!is_dir($baitcoin_api_dir)) {
        @mkdir($baitcoin_api_dir, 0755, true);
    }
    
    foreach ($api_files as $file) {
        $url = GITHUB_RAW_BASE . $file;
        $local_path = $baitcoin_api_dir . '/' . $file;
        $local_dir = dirname($local_path);
        
        if (!is_dir($local_dir)) {
            @mkdir($local_dir, 0755, true);
        }
        
        $ctx = stream_context_create(['http' => ['timeout' => 20, 'ignore_errors' => true]]);
        $data = @file_get_contents($url, false, $ctx);
        
        if ($data !== false && strlen($data) > 10) {
            @file_put_contents($local_path, $data);
            $results[] = "API: $file";
        } else {
            $errors[] = "API download: $file";
        }
    }
    
    // Restart daemon signal
    $pid_file = $baitcoin_api_dir . '/daemon.pid';
    if (file_exists($pid_file)) {
        $pid = (int)file_get_contents($pid_file);
        if ($pid > 0 && posix_kill($pid, 0)) {
            posix_kill($pid, SIGHUP); // Signal daemon to reload
            deploy_log("  SIGHUP sent to daemon PID $pid");
            $results[] = "Daemon reload signal sent";
        }
    }
}

deploy_log("=== Deploy complete: " . count($results) . " OK, " . count($errors) . " errors ===");

respond(200, 'Deploy complete', [
    'deployed' => count($results),
    'errors' => count($errors),
    'details' => $results,
    'error_details' => $errors,
    'timestamp' => date('c'),
]);
