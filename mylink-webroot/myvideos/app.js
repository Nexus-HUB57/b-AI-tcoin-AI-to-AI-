// MYVIDEOS — ponte KAIR-S-SONICA × b'AI'tcoin — v5 PRODUCAO REAL (Tesouro AI Store + fila real)
// V1: zero mock otimista — saldo/faucet falham VISIVELMENTE quando a API falha.
// V2: queima real — producao registra burn para o endereco de queima on-chain.
const BAIT_API = 'https://mybait.org/api/api/v1';
const TREASURY = "b'/t32oRLn8We5w3UnSqSTQnYZxukxsNHud7CCJj"; // AI Store Treasury — endereco OFICIAL que recebe os BAIT dos videos
const BURN_ADDRESS = "b'/t1111111111111111111114oLvT2"; // queima deterministica (reservado)
const COST = { image: { simple: 1, complex: 2, realistic: 3 }, video: { simple: 1, complex: 2, realistic: 3 } };
const BURN_ONBOARD = 100;
const FAUCET_DAILY = 10;
let wallet = null, balance = 0, onboardedOnchain = false;
const $ = (id) => document.getElementById(id);
const fmt = (n) => `${n} BAIT`;
function fb(el, msg, ok) { $(el).textContent = msg; $(el).className = 'feedback ' + (ok ? 'ok' : 'err'); }
async function baitFetch(path, opts = {}) {
  const res = await fetch(`${BAIT_API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!res.ok) throw new Error(`BAIT API ${res.status}`);
  return res.json();
}
async function connectWallet() {
  const addr = $('wallet').value.trim();
  if (!addr || !addr.startsWith("b'/t") || addr.length < 20) {
    fb('wallet-feedback', "Informe um endereço BAIT válido (formato b'/t…).", false); return;
  }
  fb('wallet-feedback', 'Consultando mainnet…', true);
  let data;
  try { data = await baitFetch(`/wallet/${addr}/balance`); }
  catch (e) {
    // V1: FALHA VISIVEL — sem saldo ficticio, sem habilitar producao
    wallet = null; balance = 0; $('balance').textContent = '—';
    $('faucet').disabled = true; $('submit').disabled = true;
    fb('wallet-feedback', `❌ Mainnet indisponível (${e.message}). Saldo NÃO carregado — produção bloqueada até confirmação on-chain.`, false);
    return;
  }
  wallet = addr;
  if (data && typeof data.balance === 'number') {
    balance = data.balance; onboardedOnchain = true;
    fb('wallet-feedback', `✅ Carteira reconhecida on-chain — saldo real: ${fmt(balance)}.`, true);
  } else {
    balance = 0; onboardedOnchain = false;
    fb('wallet-feedback', `⚠️ Endereço sem histórico on-chain. Saldo 0 — use o faucet oficial (/faucet) para receber 10 BAIT reais antes de produzir. O bônus de ${BURN_ONBOARD} BAIT de boas-vindas só é creditado via TX de onboarding (aguardando ativação do endpoint).`, false);
  }
  $('balance').textContent = fmt(balance);
  $('faucet').disabled = false; $('submit').disabled = false;
  updateCost();
}
async function claimFaucet() {
  if (!wallet) return;
  fb('wallet-feedback', 'Solicitando faucet on-chain…', true);
  let res;
  try { res = await baitFetch('/faucet/claim', { method: 'POST', body: JSON.stringify({ agent_id: ($('agent-id') && $('agent-id').value.trim()) || wallet, address: wallet }) }); }
  catch (e) { fb('wallet-feedback', `❌ Faucet falhou (${e.message}). Nenhum BAIT creditado — tente novamente ou use /faucet.`, false); return; }
  // V1: soma SOMENTE se a API confirmou
  const credited = (res && (res.ok || res.credited || res.tx_id)) ? FAUCET_DAILY : 0;
  if (credited > 0) {
    balance += credited; $('balance').textContent = fmt(balance);
    fb('wallet-feedback', `✅ +${credited} BAIT confirmados on-chain${res.tx_id ? ' · tx ' + res.tx_id.slice(0, 12) + '…' : ''}. Próximo resgate em 24h.`, true);
    $('faucet').disabled = true;
  } else {
    fb('wallet-feedback', `⚠️ Faucet respondeu sem crédito (cooldown 24h ou endereço inelegível). Saldo inalterado: ${fmt(balance)}.`, false);
  }
}
function estimateCost() {
  const f = $('job-form');
  const units = f.kind.value === 'video' ? Math.max(1, Math.round(Number(f.duration.value) / 10)) : 1;
  return COST[f.kind.value][f.tier.value] * units;
}
function updateCost() { $('cost-preview').textContent = `Custo estimado: ${fmt(estimateCost())} (→ Tesouro AI Store ${TREASURY.slice(0, 14)}…)`; }
async function submitJob(ev) {
  ev.preventDefault();
  if (!wallet) { fb('job-feedback', '❌ Conecte uma carteira on-chain primeiro.', false); return; }
  const cost = estimateCost();
  if (!onboardedOnchain) { fb('job-feedback', '❌ Produção bloqueada: saldo não confirmado on-chain (endereço sem histórico). Use /faucet para receber BAIT real.', false); return; }
  if (balance < cost) { fb('job-feedback', `❌ Saldo insuficiente (${fmt(balance)} < ${fmt(cost)}). Aguarde o faucet diário.`, false); return; }
  const f = $('job-form');
  fb('job-feedback', 'Registrando pagamento on-chain ao Tesouro AI Store…', true);
  // V2: QUEIMA REAL — registra burn para o endereco de queima; sem tx, sem producao
  let burn;
  try {
    burn = await baitFetch('/wallet/transfer', { method: 'POST', body: JSON.stringify({
      from: wallet, to: TREASURY, amount: cost,
      memo: `myvideos:${f.kind.value}:${f.tier.value}` }) });
  } catch (e) {
    fb('job-feedback', `❌ Pagamento NÃO confirmado (${e.message}). Nenhum BAIT debitado, tarefa NÃO enfileirada. Produção real exige TX de burn.`, false); return;
  }
  const txid = burn && (burn.tx_id || burn.txid || (burn.ok ? 'confirmada' : null));
  if (!txid) { fb('job-feedback', '❌ API não confirmou o pagamento. Saldo inalterado, tarefa não enfileirada.', false); return; }
  balance -= cost; $('balance').textContent = fmt(balance);
  const job = { kind: f.kind.value, tier: f.tier.value,
    duration: f.kind.value === 'video' ? Number(f.duration.value) : null,
    prompt: f.prompt.value.trim(), burn: cost, burn_tx: txid, status: 'queued', ts: new Date().toISOString() };
  const li = document.createElement('li');
  li.innerHTML = `<span>${job.kind.toUpperCase()} · ${job.tier} · ${job.prompt.slice(0, 60)}…</span><span class="cost">-${cost} BAIT 💰 · tx ${String(txid).slice(0, 12)}… · ${job.status}</span>`;
  $('jobs').prepend(li);
  fb('job-feedback', `✅ ${cost} BAIT pagos on-chain ao Tesouro AI Store (tx ${String(txid).slice(0, 16)}…). Tarefa na fila KAIR-S-SONICA — entrega via runtime do agente/OpenClaw.`, true);
  try { await baitFetch('/myvideos/job', { method: 'POST', body: JSON.stringify({ kind: job.kind, tier: job.tier, duration: job.duration, prompt: job.prompt, burn_tx: txid, wallet }) }); } catch (e) { /* fila registra no proximo retry */ }
  f.prompt.value = '';
}
$('connect').addEventListener('click', connectWallet);
$('faucet').addEventListener('click', claimFaucet);
$('job-form').addEventListener('submit', submitJob);
$('job-form').addEventListener('input', updateCost);
updateCost();
