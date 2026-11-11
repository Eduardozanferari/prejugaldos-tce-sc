// Tocador da edição: toca o resumo e as notícias em sequência. A Media Session API mostra
// título e controles na tela bloqueada e mantém a reprodução com o celular travado.
(function () {
  const faixas = window.FAIXAS || [];
  const audio = document.getElementById('audio');
  if (!audio || !faixas.length) return;
  const botao = document.getElementById('tocar');
  const titulo = document.getElementById('faixa-titulo');
  const sub = document.getElementById('faixa-sub');
  let atual = -1;

  function carregar(i) {
    if (i < 0 || i >= faixas.length) return false;
    atual = i;
    const f = faixas[i];
    audio.src = f.src;
    titulo.textContent = f.titulo;
    sub.textContent = f.sub + ' · ' + (i + 1) + ' de ' + faixas.length;
    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: f.titulo, artist: f.sub, album: 'Briefing de Notícias',
        artwork: [{ src: '/static/icone.svg', sizes: '512x512', type: 'image/svg+xml' }]
      });
    }
    return true;
  }
  function tocar(i) { if (carregar(i)) audio.play().catch(() => {}); }

  botao.addEventListener('click', () => {
    if (atual === -1) return tocar(0);
    audio.paused ? audio.play() : audio.pause();
  });
  document.getElementById('anterior').addEventListener('click', () => tocar(Math.max(0, atual - 1)));
  document.getElementById('proxima').addEventListener('click', () => tocar(atual + 1));
  audio.addEventListener('ended', () => tocar(atual + 1));
  audio.addEventListener('play', () => { botao.textContent = 'Pausar'; });
  audio.addEventListener('pause', () => { botao.textContent = 'Continuar'; });
  document.querySelectorAll('.ouvir').forEach(b => b.addEventListener('click', () => {
    const i = faixas.findIndex(f => f.src === b.dataset.src);
    if (i >= 0) { tocar(i); document.getElementById('tocador').scrollIntoView({ behavior: 'smooth' }); }
  }));
  if ('mediaSession' in navigator) {
    const ms = navigator.mediaSession;
    ms.setActionHandler('play', () => audio.play());
    ms.setActionHandler('pause', () => audio.pause());
    ms.setActionHandler('previoustrack', () => tocar(Math.max(0, atual - 1)));
    ms.setActionHandler('nexttrack', () => tocar(atual + 1));
    try { ms.setActionHandler('seekbackward', d => { audio.currentTime = Math.max(0, audio.currentTime - (d.seekOffset || 15)); }); } catch (e) {}
    try { ms.setActionHandler('seekforward', d => { audio.currentTime = audio.currentTime + (d.seekOffset || 15); }); } catch (e) {}
  }
})();
