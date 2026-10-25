(() => {
  const deck = document.querySelector('.deck');
  const slides = [...deck.querySelectorAll(':scope > .slide')];
  if (!slides.length) return;
  const toolbar = document.createElement('nav');
  toolbar.className = 'viewer-toolbar';
  toolbar.setAttribute('aria-label', '幻灯片浏览');
  toolbar.innerHTML = '<button class="viewer-icon" data-action="prev" aria-label="上一页" title="上一页（←）">‹</button><select aria-label="选择页码"></select><button class="viewer-icon" data-action="next" aria-label="下一页" title="下一页（→）">›</button><button data-action="fit" aria-pressed="true" title="切换适应窗口和原始尺寸">适应窗口</button><span class="viewer-scale" aria-live="polite"></span><button class="viewer-icon" data-action="full" aria-label="全屏" title="全屏">⛶</button>';
  document.body.prepend(toolbar);
  const select = toolbar.querySelector('select');
  const scaleLabel = toolbar.querySelector('.viewer-scale');
  const frames = slides.map((slide, index) => {
    const frame = document.createElement('div');
    frame.className = 'slide-viewport';
    slide.before(frame); frame.append(slide);
    const option = document.createElement('option');
    option.value = index; option.textContent = `${index + 1} / ${slides.length}`;
    select.append(option);
    return frame;
  });
  let current = 0, fit = true, scheduled = false;
  function syncControls() {
    select.value = current;
    toolbar.querySelector('[data-action="prev"]').disabled = current === 0;
    toolbar.querySelector('[data-action="next"]').disabled = current === slides.length - 1;
  }
  function go(index) {
    current = Math.max(0, Math.min(slides.length - 1, index));
    const top = frames[current].getBoundingClientRect().top + scrollY - toolbar.offsetHeight - 12;
    window.scrollTo({ top, behavior: 'instant' });
    syncControls();
  }
  function resize() {
    const top = toolbar.offsetHeight + 12;
    const scale = fit ? Math.max(.1, Math.min(1, (document.documentElement.clientWidth - 24) / 1280, (innerHeight - top - 20) / 720)) : 1;
    deck.style.paddingTop = `${top}px`;
    // Leave enough trailing space for the last page to align under the toolbar.
    deck.style.paddingBottom = `${Math.max(20, innerHeight - top - 720 * scale)}px`;
    document.documentElement.style.scrollPaddingTop = `${top}px`;
    for (const [index, frame] of frames.entries()) {
      frame.style.width = `${1280 * scale}px`;
      frame.style.height = `${720 * scale}px`;
      slides[index].style.transform = `scale(${scale})`;
    }
    scaleLabel.textContent = `${Math.round(scale * 100)}%`;
    toolbar.querySelector('[data-action="fit"]').textContent = fit ? '适应窗口' : '原始尺寸';
    toolbar.querySelector('[data-action="fit"]').setAttribute('aria-pressed', String(fit));
    document.body.classList.toggle('viewer-actual', !fit);
    go(current);
  }
  toolbar.addEventListener('click', async event => {
    const action = event.target.closest('button')?.dataset.action;
    if (action === 'prev') go(current - 1);
    if (action === 'next') go(current + 1);
    if (action === 'fit') { fit = !fit; resize(); }
    if (action === 'full') {
      try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); } catch { /* Window fitting remains available when fullscreen is restricted. */ }
    }
  });
  select.addEventListener('change', () => go(Number(select.value)));
  addEventListener('keydown', event => {
    if (event.target.closest('input, select, textarea, button') || event.ctrlKey || event.metaKey || event.altKey) return;
    if (['ArrowLeft', 'PageUp', 'ArrowRight', 'PageDown', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      go(event.key === 'Home' ? 0 : event.key === 'End' ? slides.length - 1 : current + (['ArrowLeft', 'PageUp'].includes(event.key) ? -1 : 1));
    }
  });
  addEventListener('scroll', () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      let distance = Infinity;
      frames.forEach((frame, index) => {
        const next = Math.abs(frame.getBoundingClientRect().top - toolbar.offsetHeight - 12);
        if (next < distance) { distance = next; current = index; }
      });
      syncControls();
    });
  }, { passive: true });
  addEventListener('resize', resize);
  addEventListener('fullscreenchange', resize);
  resize();
})();
