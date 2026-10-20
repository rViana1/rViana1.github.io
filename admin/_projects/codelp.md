---
title:
  en: Codelp
  pt: Codelp
subtitle:
  en: Repository understanding tool · In development
  pt: Ferramenta de compreensão de repositórios · Em desenvolvimento
summary:
  en: A software project that turns Python repositories into navigable knowledge, with persistent history, incremental analysis and traceable retrieval.
  pt: Projeto de software que transforma repositórios Python em conhecimento navegável, com histórico persistente, análise incremental e pesquisa rastreável.
order: 1
project_order: 2
status: active
tags: [personal]
tech: [Python, AST, FastAPI, Pydantic, Typer, MCP, React, TypeScript, Vinext, Vite, Tailwind CSS, JSON]
highlights:
  - en: Parses Python code into symbols, indexes and semantic chunks.
    pt: Analisa código Python para obter símbolos, índices e segmentos semânticos.
  - en: Preserves project knowledge and identity across changes and analysis runs.
    pt: Preserva o conhecimento e a identidade do projeto entre alterações e execuções de análise.
  - en: Exposes knowledge through a CLI, MCP, REST API and visual workspace.
    pt: Disponibiliza o conhecimento através de uma interface de linha de comandos, MCP, API REST e espaço de trabalho visual.
links:
  - label:
      en: Source code on GitHub
      pt: Código-fonte no GitHub
    url: https://github.com/rViana1/codelp
---
## How it works

Codelp is an actively developed software project for understanding repositories. Its current parser supports Python: it discovers files, extracts imports and symbols with Python AST, builds deterministic indexes and divides code into chunks associated with their source locations.

The project persists knowledge with stable identities and history, detects changes and supports selective incremental analysis. A knowledge graph helps explore dependencies, duplicates, similarity and evolution. Retrieval produces context with traceable sources, using optional embeddings or a deterministic lexical fallback.

The same runtime is available through a command-line interface, MCP, a REST API and a visual browser workspace. Static analysis and structural exploration work without an LLM. Support for other programming languages and a hosted multi-user service are future possibilities, rather than current capabilities.

<!--pt-->

## Como funciona

O Codelp é um projeto de software em desenvolvimento ativo para compreender repositórios. O analisador atual suporta Python: descobre ficheiros, extrai importações e símbolos com Python AST, constrói índices determinísticos e divide o código em segmentos associados à sua localização na origem.

O projeto guarda conhecimento com identidades estáveis e histórico, deteta alterações e permite análise incremental seletiva. Um grafo de conhecimento permite explorar dependências, duplicados, semelhanças e evolução. A pesquisa produz contexto com fontes rastreáveis, recorrendo a embeddings opcionais ou a uma alternativa de pesquisa lexical determinística.

O mesmo motor está disponível através de uma interface de linha de comandos, MCP, uma API REST e um espaço de trabalho visual no navegador. A análise estática e a exploração estrutural funcionam sem um LLM. O suporte de outras linguagens de programação e um serviço alojado para vários utilizadores são possibilidades futuras, ainda não disponíveis.
