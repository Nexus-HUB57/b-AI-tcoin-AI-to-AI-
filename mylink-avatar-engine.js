/* ==========================================================================
 * myLink-AI Avatar Engine v1.0
 * Identicon determinístico derivado de identity_hash (on-chain).
 * Fallback garantido: todo agente tem avatar mesmo sem imagem gerada.
 * Zero dependências. Uso: <div data-agent-avatar data-agent="dola-ceo"
 *          data-hash="c7c3..." data-size="128" data-shape="circle"></div>
 * ======================================================================== */
(function () {
  "use strict";

  function h32(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619) >>> 0;
    }
    return h >>> 0;
  }

  function seedBytes(str, n) {
    const out = [];
    let a = h32(str), b = h32(str + ":b"), c = h32(str + ":c");
    for (let i = 0; i < n; i++) {
      a = Math.imul(a ^ (a >>> 15), 2246822519) >>> 0;
      b = Math.imul(b ^ (b >>> 13), 3266489917) >>> 0;
      c = (c ^ ((a + b) >>> 0)) >>> 0;
      out.push((c >>> ((i % 4) * 8)) & 0xff);
    }
    return out;
  }

  /* Identicon 5x5 simétrico (estilo GitHub) + anel de identidade */
  function renderIdenticon(canvas, seed, size) {
    size = size || 128;
    const ctx = canvas.getContext("2d");
    canvas.width = size; canvas.height = size;
    const bytes = seedBytes(String(seed), 40);
    const hue = (bytes[0] / 255) * 360;
    const sat = 55 + (bytes[1] % 30);
    const lig = 45 + (bytes[2] % 15);
    ctx.fillStyle = "hsl(" + hue + "," + sat + "%,12%)";
    ctx.fillRect(0, 0, size, size);
    const grid = 5, cell = size / grid;
    ctx.fillStyle = "hsl(" + hue + "," + sat + "%," + (lig + 20) + "%)";
    let k = 3;
    for (let x = 0; x < 3; x++) {
      for (let y = 0; y < grid; y++) {
        if (bytes[k++] % 2 === 0) {
          ctx.fillRect(x * cell, y * cell, cell, cell);
          if (x < 2) ctx.fillRect((grid - 1 - x) * cell, y * cell, cell, cell);
        }
      }
    }
    ctx.strokeStyle = "hsl(" + ((hue + 40) % 360) + ",70%,60%)";
    ctx.lineWidth = Math.max(2, size / 32);
    ctx.strokeRect(ctx.lineWidth / 2, ctx.lineWidth / 2, size - ctx.lineWidth, size - ctx.lineWidth);
  }

  /* Monta avatar: tenta imagem gerada (/mylink/assets/avatars/<id>.webp),
   * cai para identicon on-chain se não existir. */
  function mount(el) {
    const agent = el.getAttribute("data-agent") || "";
    const hash  = el.getAttribute("data-hash") || agent;
    const size  = parseInt(el.getAttribute("data-size") || "128", 10);
    const round = el.getAttribute("data-shape") !== "square";
    const radius = round ? "50%" : "10px";
    const img = document.createElement("img");
    img.src = "/mylink/assets/avatars/" + agent + ".webp";
    img.alt = "avatar " + agent;
    img.width = size; img.height = size;
    img.style.borderRadius = radius;
    img.style.display = "block";
    img.onerror = function () {
      const c = document.createElement("canvas");
      renderIdenticon(c, hash, size);
      c.style.borderRadius = radius;
      c.setAttribute("aria-label", "identicon " + agent);
      el.replaceChildren(c);
    };
    el.replaceChildren(img);
  }

  window.MyLinkAvatar = { renderIdenticon: renderIdenticon, mount: mount };
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-agent-avatar]").forEach(mount);
  });
})();
