(() => {
  const root = document.documentElement;
  const languageButtons = document.querySelectorAll('[data-set-lang]');
  const themeButton = document.querySelector('#theme-toggle');
  const menuButton = document.querySelector('#menu-toggle');
  const navigation = document.querySelector('#site-nav');
  const title = document.querySelector('title');
  const description = document.querySelector('meta[name="description"]');
  // Storage can be blocked by browser privacy settings; controls still work.
  const read = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const save = (key, value) => { try { localStorage.setItem(key, value); } catch {} };
  const setLanguage = language => {
    root.dataset.lang = language;
    root.lang = language;
    document.title = title.dataset[language];
    description.content = description.dataset[language];
    languageButtons.forEach(button => button.setAttribute('aria-pressed', button.dataset.setLang === language));
  };
  const storedLanguage = read('rv-language');
  setLanguage(['en', 'pt'].includes(storedLanguage) ? storedLanguage : (navigator.language || '').toLowerCase().startsWith('pt') ? 'pt' : 'en');
  languageButtons.forEach(button => button.addEventListener('click', () => {
    setLanguage(button.dataset.setLang);
    save('rv-language', root.dataset.lang);
  }));

  const setTheme = theme => {
    root.dataset.theme = theme;
    themeButton.setAttribute('aria-pressed', theme === 'light');
  };
  setTheme(read('rv-theme') === 'light' ? 'light' : 'dark');
  themeButton.addEventListener('click', () => {
    setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark');
    save('rv-theme', root.dataset.theme);
  });

  let menuOpen = false;
  const setMenu = (open, restoreFocus = false) => {
    menuOpen = open;
    menuButton.setAttribute('aria-expanded', open);
    navigation.hidden = !open;
    if (!open && restoreFocus) menuButton.focus();
  };
  setMenu(false);
  menuButton.addEventListener('click', () => setMenu(!menuOpen, menuOpen));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menuOpen) setMenu(false, true);
  });
  navigation.addEventListener('click', event => {
    if (menuOpen && event.target.closest('a')) setMenu(false, true);
  });
})();
