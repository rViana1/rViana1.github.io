(() => {
  if (!/^https?:$/.test(new URL(location.href).protocol)) return;
  const main = document.querySelector('main');
  const nav = document.querySelector('#site-nav');
  const title = document.querySelector('title');
  const description = document.querySelector('meta[name="description"]');
  let controller;
  let serial = 0;
  let renderedUrl = location.href;
  history.scrollRestoration = 'manual';

  const savePosition = () => history.replaceState({ ...history.state, scrollX: window.scrollX, scrollY: window.scrollY }, '', location.href);
  window.addEventListener('scroll', () => {
    if (location.href === renderedUrl) savePosition();
  }, { passive: true });

  async function navigate(url, push, position) {
    if (controller) controller.abort();
    controller = new AbortController();
    const request = ++serial;
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok || !response.headers.get('content-type')?.includes('text/html') || new URL(response.url).origin !== location.origin) throw new Error('Invalid page');
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const nextMain = page.querySelector('main');
      const nextTitle = page.querySelector('title');
      const nextDescription = page.querySelector('meta[name="description"]');
      if (!nextMain || !nextTitle || !nextDescription) throw new Error('Invalid page');
      if (request !== serial) return;
      if (push) {
        savePosition();
        history.pushState({ scrollX: 0, scrollY: 0 }, '', url);
      }
      renderedUrl = location.href;
      main.innerHTML = nextMain.innerHTML;
      for (const language of ['en', 'pt']) {
        title.dataset[language] = nextTitle.dataset[language];
        description.dataset[language] = nextDescription.dataset[language];
      }
      const language = document.documentElement.dataset.lang || 'en';
      document.title = title.dataset[language];
      description.content = description.dataset[language];
      const active = page.querySelector('#site-nav a[aria-current="page"]');
      nav.querySelectorAll('a').forEach(link => {
        if (active && link.getAttribute('href') === active.getAttribute('href')) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      });
      const nextPhoto = page.querySelector('.brand-photo');
      let photo = document.querySelector('.brand-photo');
      let placeholder = document.querySelector('.brand-photo-placeholder');
      if (!photo && nextPhoto && placeholder) {
        photo = nextPhoto.cloneNode(true);
        placeholder.after(photo);
      }
      if (!placeholder && photo) {
        placeholder = document.createElement('span');
        placeholder.className = 'brand-photo-placeholder';
        placeholder.setAttribute('aria-hidden', 'true');
        photo.before(placeholder);
      }
      if (photo) photo.hidden = !nextPhoto;
      if (placeholder) placeholder.hidden = !!nextPhoto;
      const menu = document.querySelector('#menu-toggle');
      if (menu?.getAttribute('aria-expanded') === 'true') menu.click();
      window.scrollTo(position?.scrollX || 0, position?.scrollY || 0);
      if (push) main.focus({ preventScroll: true });
    } catch (error) {
      if (error.name !== 'AbortError' && request === serial) location.assign(url);
    }
  }

  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest('a[href]');
    if (!link || link.target || link.hasAttribute('download')) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.hash || !/^https?:$/.test(url.protocol)) return;
    event.preventDefault();
    navigate(url.href, true);
  });
  window.addEventListener('popstate', event => navigate(location.href, false, event.state));
})();
