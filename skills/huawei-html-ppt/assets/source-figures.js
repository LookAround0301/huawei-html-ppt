/* Local, byte-preserving image zoom for technical-project reports. */
(() => {
  const images = [...document.querySelectorAll('.technical-project .source-figure img, .project-report .source-figure img')];
  if (!images.length) return;
  const dialog = document.createElement('dialog');
  dialog.className = 'source-lightbox';
  dialog.setAttribute('aria-label', '查看原图');
  const close = document.createElement('button');
  close.type = 'button';
  close.textContent = '关闭 · Esc';
  const scroll = document.createElement('div');
  scroll.className = 'image-scroll';
  const large = document.createElement('img');
  large.tabIndex = 0;
  large.title = '点击切换原始尺寸';
  dialog.append(close, scroll);
  document.body.append(dialog);
  let opener;
  const toggle = () => dialog.classList.toggle('expanded');
  large.addEventListener('click', toggle);
  large.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); toggle(); }
  });
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => opener?.focus({preventScroll: true}));
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('keydown', event => event.stopPropagation());
  for (const image of images) {
    image.dataset.zoom = 'true';
    image.tabIndex = 0;
    image.title = '点击放大原图';
    image.setAttribute('aria-haspopup', 'dialog');
    const open = () => {
      opener = image;
      large.src = image.src;
      large.alt = image.alt;
      scroll.append(large);
      dialog.classList.remove('expanded');
      if (!dialog.open) dialog.showModal();
    };
    image.addEventListener('click', open);
    image.addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); open(); }
    });
  }
})();
