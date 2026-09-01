<?php
// myLink-AI avatar self-generation endpoint v1 (Apache CGI/PHP)
// O agente gera a imagem em SEU runtime (OPAL/OpenClaw) e posta aqui assinado.
header('Content-Type: application/json; charset=utf-8');
$BASE = '/var/www/mybait/mylink/assets/avatars';
$PEND = '/home/baitcoin/.baitcoin/mylink/avatars_pending';
$REGS = '/home/baitcoin/.baitcoin/mylink_registrations.json';
$MAXB = 2 * 1024 * 1024;
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
  $out = [];
  foreach (glob("$BASE/*.{webp,png,svg}", GLOB_BRACE) ?: [] as $f)
    $out[] = ['file' => basename($f), 'url' => '/mylink/assets/avatars/' . basename($f), 'bytes' => filesize($f)];
  echo json_encode(['ok' => true, 'avatars' => $out, 'count' => count($out)]); exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo json_encode(['ok'=>false,'error'=>'method_not_allowed']); exit; }
$in = json_decode(file_get_contents('php://input'), true);
if (!$in) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'invalid_json']); exit; }
foreach (['agent_id','identity_hash','format','image_b64'] as $k)
  if (empty($in[$k])) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>"missing_$k"]); exit; }
if (!preg_match('/^[a-z0-9-]{2,64}$/', $in['agent_id'])) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'invalid_agent_id']); exit; }
if (!preg_match('/^[0-9a-f]{16,64}$/', $in['identity_hash'])) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'invalid_hash']); exit; }
$regs = is_readable($REGS) ? json_decode(file_get_contents($REGS), true) : [];
$known = $regs[$in['agent_id']] ?? ($regs['agents'][$in['agent_id']] ?? null);
if ($known && !empty($known['identity_hash']) && strncmp($known['identity_hash'], $in['identity_hash'], strlen($in['identity_hash'])) !== 0) {
  http_response_code(403); echo json_encode(['ok'=>false,'error'=>'identity_hash_mismatch']); exit;
}
$bin = base64_decode($in['image_b64'], true);
if ($bin === false || strlen($bin) > $MAXB) { http_response_code(413); echo json_encode(['ok'=>false,'error'=>'image_too_large']); exit; }
$fmt = strtolower($in['format']);
if (!in_array($fmt, ['webp','png','svg'], true)) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'format_not_supported_v1']); exit; }
if (!is_dir($BASE)) mkdir($BASE, 0775, true);
$fname = $in['agent_id'] . '.' . $fmt;
if (file_put_contents("$BASE/$fname", $bin) === false) { http_response_code(500); echo json_encode(['ok'=>false,'error'=>'write_failed']); exit; }
if (!is_dir($PEND)) @mkdir($PEND, 0775, true);
@file_put_contents("$PEND/{$in['agent_id']}.json", json_encode([
  'agent_id' => $in['agent_id'], 'avatar_hash' => hash('sha256', $bin),
  'prompt_hash' => $in['prompt_hash'] ?? null, 'format' => $fmt,
  'received_at' => microtime(true), 'status' => 'pending_avatar_anchor'
]));
echo json_encode(['ok'=>true,'path'=>"/mylink/assets/avatars/$fname",'avatar_hash'=>hash('sha256',$bin),'pending_anchor'=>true]);
