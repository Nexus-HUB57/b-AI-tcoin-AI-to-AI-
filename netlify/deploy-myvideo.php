<?php
/**
 * b'AI'tcoin Full Deploy — MyVideo + Fundo + API v3.2
 * 
 * Deploy ALL frontend files including new MyVideo autonomous system.
 * Upload to public_html/ via cPanel File Manager, then access:
 * https://www.mybait.org/deploy-myvideo.php?secret=baitcoin-update-2024
 * 
 * After successful deploy, DELETE this file for security.
 */
error_reporting(E_ALL);
ini_set('display_errors', 1);
set_time_limit(180);

$SECRET = 'baitcoin-update-2024';
if (!isset($_GET['secret']) || $_GET['secret'] !== $SECRET) {
    http_response_code(401);
    die('Unauthorized. Use ?secret=baitcoin-update-2024');
}

$REPO_RAW = 'https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main';
$PUBLIC_HTML = __DIR__;
$HOME = dirname($PUBLIC_HTML);
$INSTALL_DIR = $HOME . '/baitcoin-api';

$results = [];
$errors = [];

function download_file($url, $dest) {
    $ctx = stream_context_create(['http' => ['timeout' => 30, 'ignore_errors' => true, 'user_agent' => 'baitcoin-deploy/1.0']]);
    $data = @file_get_contents($url, false, $ctx);
    if ($data !== false && strlen($data) > 50) {
        $ok = @file_put_contents($dest, $data);
        if ($ok) return strlen($data);
    }
    return 0;
}

header('Content-Type: text/plain; charset=utf-8');
echo "=== b'AI'tcoin Full Deploy (MyVideo + Fundo + API v3.2) ===\n";
echo "Time: " . date('Y-m-d H:i:s') . "\n";
echo "Dir:  $PUBLIC_HTML\n\n";

// ═══ 1. Static HTML Frontend ═══
echo "--- Frontend HTML ---\n";
$html_files = [
    'index.html', 'blockchain.html', 'bainkr.html', 'faucet.html',
    'fundo.html', 'swap.html', 'sdk.html', 'obscura.html',
    'myvideo.html', 'favicon.svg', '.htaccess',
];
foreach ($html_files as $fname) {
    $url = "$REPO_RAW/netlify/$fname";
    $dest = "$PUBLIC_HTML/$fname";
    echo "  $fname ... ";
    $size = download_file($url, $dest);
    if ($size > 100) {
        @chmod($dest, 0644);
        echo "OK ($size bytes)\n";
        $results[] = $fname;
    } else {
        echo "FAILED\n";
        $errors[] = "$fname (download)";
    }
}

// whitepaper
echo "  whitepaper.pdf ... ";
$size = download_file("$REPO_RAW/netlify/whitepaper.pdf", "$PUBLIC_HTML/whitepaper.pdf");
echo $size > 1000 ? "OK ($size bytes)\n" : "FAILED\n";

// ═══ 2. MyLink Sub-Pages ═══
echo "\n--- MyLink Sub-Pages ---\n";
$subpages = [
    ['mylink/fundo', 'fundo.html'],
    ['mylink/fundo/swap', 'swap.html'],
    ['mylink/myvideo', 'myvideo.html'],
];
foreach ($subpages as [$subdir, $fname]) {
    $dir = "$PUBLIC_HTML/$subdir";
    if (!is_dir($dir)) @mkdir($dir, 0755, true);
    $url = "$REPO_RAW/netlify/$fname";
    $dest = "$dir/index.html";
    echo "  $subdir/index.html ($fname) ... ";
    $size = download_file($url, $dest);
    if ($size > 100) {
        @chmod($dest, 0644);
        echo "OK ($size bytes)\n";
        $results[] = "$subdir/index.html";
    } else {
        echo "FAILED\n";
        $errors[] = "$subdir/index.html";
    }
}

// ═══ 3. API CGI Gateway ═══
echo "\n--- API CGI Gateway ---\n";
echo "  api.cgi ... ";
$size = download_file("$REPO_RAW/netlify/api.cgi", "$PUBLIC_HTML/api.cgi");
if ($size > 500) {
    @chmod("$PUBLIC_HTML/api.cgi", 0755);
    echo "OK ($size bytes)\n";
    $results[] = 'api.cgi';
} else {
    echo "FAILED\n";
    $errors[] = 'api.cgi';
}

// ═══ 4. Daemon Core ═══
echo "\n--- Daemon Core ---\n";
if (!is_dir($INSTALL_DIR)) @mkdir($INSTALL_DIR, 0755, true);
$daemon_files = ['main_daemon.py', 'daemon_wrapper.py', 'daemon_production.py', 'requirements.txt'];
foreach ($daemon_files as $fname) {
    $url = "$REPO_RAW/$fname";
    $dest = "$INSTALL_DIR/$fname";
    echo "  $fname ... ";
    $size = download_file($url, $dest);
    echo $size > 100 ? "OK ($size bytes)\n" : "FAILED\n";
}

// ═══ 5. Restart Daemon ═══
echo "\n--- Daemon Restart ---\n";
$pidfile = "$INSTALL_DIR/daemon.pid";
if (file_exists($pidfile)) {
    $pid = (int)trim(file_get_contents($pidfile));
    if ($pid > 0) {
        // Try to kill and let CGI restart it on next request
        @posix_kill($pid, SIGTERM);
        echo "  Sent SIGTERM to PID $pid\n";
        sleep(2);
        // Remove pidfile so CGI will cold-start
        @unlink($pidfile);
        echo "  Removed PID file — daemon will cold-start on next API request\n";
    }
} else {
    echo "  No PID file — daemon will cold-start on next API request\n";
}

// ═══ Summary ═══
echo "\n════════════════════════════════════════\n";
echo "Deployed: " . count($results) . " files\n";
echo "Errors:   " . count($errors) . "\n";
if ($errors) echo "Failed:   " . implode(', ', $errors) . "\n";
echo "\n✅ MyVideo autonomous system deployed to /mylink/myvideo/\n";
echo "✅ API endpoints: /api/v1/myvideo/orquestrar, /fila, /status\n";
echo "\n⚠️  DELETE THIS FILE (deploy-myvideo.php) FOR SECURITY!\n";
