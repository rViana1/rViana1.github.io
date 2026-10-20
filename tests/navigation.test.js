const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const handlers = {};
const header = { photo: {} };
const main = { innerHTML: 'old', focus() {} };
const currentTitle = { dataset: { en: 'Old', pt: 'Antigo' } };
const currentDescription = { dataset: {}, content: '' };
const navLink = { removeAttribute() {}, setAttribute() {} };
const document = {
  documentElement: { dataset: { lang: 'en' } },
  title: 'Old',
  querySelector(selector) {
    return ({ 'main': main, '.site-header': header, 'title': currentTitle,
      'meta[name="description"]': currentDescription, '#site-nav': { querySelectorAll: () => [navLink] },
      '.brand-photo': null, '.brand-photo-placeholder': null, '#menu-toggle': null })[selector];
  },
  addEventListener(name, callback) { handlers[name] = callback; }
};
const nextMain = { innerHTML: 'new' };
const parsed = { querySelector(selector) { return ({
  main: nextMain, title: { dataset: { en: 'New', pt: 'Novo' } },
  'meta[name="description"]': { dataset: { en: 'New description', pt: 'Nova descrição' } },
  '#site-nav a[aria-current="page"]': null, '.brand-photo': null,
  '.brand-photo-placeholder': null
})[selector]; } };
const history = { state: null, pushState(state, title, url) { this.url = url; }, replaceState() {} };
const window = { addEventListener(name, fn) { handlers[name] = fn; }, scrollTo() {}, scrollX: 0, scrollY: 0 };
const location = { href: 'https://example.test/old/', origin: 'https://example.test', assign() {} };
const context = { document, history, window, location, URL, DOMParser: class { parseFromString() { return parsed; } },
  fetch: async () => ({ ok: true, url: 'https://example.test/new/', headers: { get: () => 'text/html' }, text: async () => '<html></html>' }),
  AbortController, console };
const file = 'assets/js/navigation.js';
assert.ok(fs.existsSync(file), 'A navegação contínua ainda não está implementada');
vm.runInNewContext(fs.readFileSync(file, 'utf8'), context);
const link = { href: 'https://example.test/new/', target: '', hasAttribute: () => false, getAttribute: () => '/new/' };
let prevented = false;
handlers.click({ button: 0, target: { closest: () => link }, preventDefault() { prevented = true; } });
setTimeout(() => {
  assert.equal(prevented, true);
  assert.equal(main.innerHTML, 'new');
  assert.equal(document.querySelector('.site-header'), header);
  assert.equal(document.title, 'New');
  assert.equal(history.url, 'https://example.test/new/');
}, 20);
