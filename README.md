# Ricardo Viana — portfolio / portefólio

Jekyll portfolio in English and Portuguese. Both languages share each page; the
language and theme controls save preferences locally. No analytics or form backend
is included. Contacts use email, LinkedIn and GitHub links.

## Local setup / preparação

Use Ruby 3.3+ (see `.ruby-version`), Python 3.9+ and Node.js for the existing UI
checks. On Apple Silicon with Homebrew Ruby, first run
`export PATH="/opt/homebrew/opt/ruby/bin:$PATH"`. From the repository root:

```sh
ruby --version
gem install bundler -v 2.6.9
bundle check || bundle install
```

Keep `Gemfile.lock` committed; do not update gems as part of a content edit.

## Preview and validate / pré-visualizar e validar

```sh
bundle exec jekyll serve --livereload
```

Open <http://localhost:4000>. Stop the preview with Ctrl+C. Before publishing:

```sh
bundle exec python -m unittest discover -s tests -v
JEKYLL_ENV=production bundle exec jekyll build --safe --strict_front_matter --destination _site-test
python tools/check_source.py .
python tools/check_site.py _site-test
```

The generated checker requires HTML pages, existing internal targets/fragments,
one `h1` per page, image alt text and positive dimensions, and no inherited private
identity or unrendered Liquid. It does not request external websites. For a build
under a subpath, use `--baseurl /portfolio` on both Jekyll and the generated checker.
`_site-test` is disposable output and is ignored by Git.

## Edit content / editar conteúdo

```sh
${EDITOR:-vi} admin/_data/profile.yml admin/_data/contacts.yml
${EDITOR:-vi} admin/_data/nav.yml admin/_data/skills.yml admin/_data/languages.yml
${EDITOR:-vi} admin/_data/ui.yml admin/_data/tags.yml
${EDITOR:-vi} admin/_experience/medana-ai.md admin/_projects/codelp.md
${EDITOR:-vi} admin/_education/computer-engineering.md admin/_hobbies/roller-hockey.md
```

Keep every translated field's `en` and `pt` values. Collection entries use bilingual
`title`, `subtitle`, `summary` and `highlights`, followed by English Markdown,
`<!--pt-->`, then Portuguese Markdown. Reuse an entry in the same collection when
adding content; its filename becomes the detail-page slug. Keep optional dates
accurate and use only approved public contact details. Images live in `images/`;
provide alt text and the actual width/height whenever adding an image.

## GitHub Pages

In repository Settings → Pages, choose **Deploy from a branch**, branch **main**,
folder **/ (root)**. The site uses the locked `github-pages` bundle and safe Jekyll
build; no deployment workflow is required. Publishing or changing that setting is
a separate action from local editing and validation.
