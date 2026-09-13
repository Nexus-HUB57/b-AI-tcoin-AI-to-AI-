<?php
/**
 * b'AI'tcoin One-Time Updater
 * Coloque este arquivo em public_html/ via cPanel File Manager
 * Acesse https://www.mybait.org/update.php para executar
 * Após executar, delete este arquivo por segurança.
 */
error_reporting(E_ALL);
ini_set('display_errors', 1);
set_time_limit(120);

$REPO_RAW = 'https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main';
$PUBLIC_HTML = __DIR__;

$results = [];
$errors = [];

// Frontend HTML files
$files = [
    'netlify/index.html'       => 'index.html',
    'netlify/blockchain.html'  => 'blockchain.html',
    'netlify/bainkr.html'      => 'bainkr.html',
    'netlify/faucet.html'      => 'faucet.html',
    'netlify/.htaccess'        => '.htaccess',
    'netlify/api.cgi'          => 'api.cgi',
];

header('Content-Type: text/plain; charset=utf-8');
echo "=== b'AI'tcoin Updater ===\n";
echo "Hora: " . date('Y-m-d H:i:s') . "\n";
echo "Dir:  $PUBLIC_HTML\n\n";

foreach ($files as $src => $dest) {
    $url = $REPO_RAW . '/' . $src;
    $local = $PUBLIC_HTML . '/' . $dest;
    
    echo "Baixando $src ... ";
    $ctx = stream_context_create(['http' => ['timeout' => 30, 'ignore_errors' => true]]);
    $data = @file_get_contents($url, false, $ctx);
    
    if ($data !== false && strlen($data) > 100) {
        $ok = @file_put_contents($local, $data);
        if ($ok) {
            if ($dest === 'api.cgi') @chmod($local, 0755);
            echo "OK (" . strlen($data) . " bytes)\n";
            $results[] = $dest;
        } else {
            echo "FALHA (write error)\n";
            $errors[] = $dest . ' (write)';
        }
    } else {
        echo "FALHA (download " . strlen($data ?: '') . " bytes)\n";
        $errors[] = $dest . ' (download)';
    }
}

echo "\n=== Resultado ===\n";
echo "OK: " . count($results) . " | Falhas: " . count($errors) . "\n";
if ($errors) echo "Erros: " . implode(', ', $errors) . "\n";
echo "\nPRÓXIMO PASSO: delete este arquivo (update.php) por segurança.\n";
