# Fase 8: fundação de engenharia

- Status: em andamento
- Planejada em: 2026-11-11 · Concluída em: -

## Objetivo
Daqui em diante o Pace Lab é construído como num time profissional: cada tarefa é uma issue no GitHub, cada mudança entra por pull request com testes e checagens automáticas (CI), a `main` só recebe código aprovado, as dependências são vigiadas, a segurança tem documento e checklist, e qualquer IA (Claude, Gemini) ou pessoa retoma o trabalho lendo o repositório e a issue aberta. O repositório fica limpo de dados pessoais e público.

## Fora do escopo
- Entrega automática no servidor (CD), contrato da API tipado (Pydantic, OpenAPI e tipos TypeScript gerados) e divisão do `services.py`: fase 9, junto com a refatoração para contas.
- Compilar o app Android no CI: depende de separar o plugin da Samsung (SDK que não pode ir ao repositório); fica como issue para a fase 9 ou 10.

## Decisões tomadas (11/11/2026)
- Fase própria antes da nuvem, com renumeração (nuvem 9, desktop 10, musculação 11, abrir para outras pessoas 12).
- Repositório público, com o histórico reescrito: o número do export do Strava sai de todos os commits e o e-mail de autor vira o `noreply` do GitHub (`45109700+almeidalucas78@users.noreply.github.com`).
- O usuário instala o GitHub CLI (`gh`) e faz `gh auth login`.

## Verificado antes de propor (11/11/2026)
- **Histórico do git (13 commits):** sem chaves, tokens reais, coordenadas, arquivos de treino, `.env` ou banco; o nome real da rede do Tailscale não aparece. Ficariam públicos: o número do export do Strava (provável ID de atleta; 3 arquivos e 2 commits), o e-mail do autor, fatos de saúde em `docs/dados.md` (FC máxima, datas e distâncias, VO2max) e o modelo do celular.
- **GitHub Free** (docs.github.com): repositório público tem Actions grátis nas máquinas padrão; privado tem US$ 12/mês e para sem cartão. Branch protegida só em repositório público no plano grátis.
- **Gemini CLI** (geminicli.com/docs/cli/gemini-md): lê `GEMINI.md` por padrão; aceita outros nomes em `context.fileName` no `.gemini/settings.json`, e um `GEMINI.md` pode importar outro arquivo com `@./AGENTS.md`.
- **Hoje o projeto não tem** lint, formatador, checagem de tipos no Python nem ESLint no painel; não tem CI.
- Versões das ferramentas (ruff, mypy, pre-commit, gitleaks, ações do GitHub) serão conferidas no PyPI, npm e GitHub na etapa em que entrarem.

## Decisões respondidas (11/11/2026)
1. **Licença:** nenhuma por enquanto (código visível, todos os direitos reservados); escolher depois. Uma licença aberta concedida não pode ser retirada de quem já recebeu o código.
2. **Organização das pastas (monorepo), agora:** `server/` (Python, hoje `treino/`, `tests/`, migrações), `web/` (painel), `android/` (hoje `web/android`), `desktop/` (fase 10). Junto, limpar a raiz (arquivos soltos, gerados e obsoletos).
3. **Mensagens de commit:** Conventional Commits com o tipo em inglês (`feat`, `fix`, `docs`, `chore`, `test`, `refactor`) e o resto em português, por exemplo `feat(web): tela de login`.
4. **Tipos no Python (mypy), gradual:** o mypy lê as anotações de tipo (`def f(x: int) -> str`) e acusa erros antes de rodar, como o TypeScript faz no painel. Começa exigindo só no `core/` e nos arquivos novos, e vai apertando; exigir tudo de uma vez travaria a fase. Escolhido pelo assistente porque o usuário não conhecia a ferramenta; dá para mudar a qualquer momento.

### Sobre licenças
- **Sem licença:** o código fica visível, mas pela lei ninguém pode copiar, modificar ou distribuir sem sua permissão. Você continua dono de tudo e pode escolher qualquer licença depois.
- **MIT:** qualquer pessoa pode usar, modificar e até vender, inclusive em produto fechado, só mantendo seu nome no aviso. Máxima liberdade para os outros; você não ganha proteção.
- **Apache 2.0:** parecida com a MIT, com proteção extra sobre patentes.
- **GPL 3.0:** quem distribuir uma versão modificada (instalador, APK) tem de abrir o código dela. Não cobre quem só hospeda e oferece pela internet.
- **AGPL 3.0:** como a GPL, mas cobre também quem hospeda: se alguém pegar o Pace Lab e oferecer como serviço, tem de abrir o código. Impede que alguém feche o seu projeto, mas afasta empresas.
- **Código disponível, uso não comercial** (ex.: PolyForm Noncommercial): visível e usável por pessoas, sem uso comercial. Não é "código aberto" na definição oficial.
- Como único autor, você pode no futuro usar duas licenças ao mesmo tempo (ex.: AGPL para todos e uma licença paga para quem quiser fechado).

## Mudanças no banco
Nenhuma.

## Etapas
1. [x] **Limpeza e publicação**: backup completo do repositório (`git bundle`) fora dele; número do export trocado por exemplo genérico nos arquivos atuais; `git filter-repo` para tirar o número de todos os commits e trocar o e-mail de autor pelo `noreply`; nova auditoria do histórico; push forçado (com o ok do usuário na hora); `git config user.email` do repositório com o `noreply`; o usuário liga no GitHub "manter e-mail privado" e "bloquear pushes que exponham o e-mail"; licença conforme a decisão 1; `SECURITY.md`; o usuário torna o repositório público.
2. [x] **Documentação para qualquer IA ou pessoa**: `AGENTS.md` com as regras do projeto (vindas do `CLAUDE.md`), `CLAUDE.md` e `GEMINI.md` importando o `AGENTS.md` (sem `.gemini/settings.json`: o `GEMINI.md` já importa); as regras por área continuam em `.claude/rules/` (o Claude Code carrega sozinho; o `AGENTS.md` aponta qual abrir em cada área, em vez de duplicar em `docs/convencoes/`); `docs/processo.md` com o fluxo (issue, branch, PR, revisão, fechamento de fase) que hoje só existe nas skills; `CONTRIBUTING.md` (montar o ambiente, comandos, checagens).
3. [x] **Organização das pastas** (decisão 2): `server/` (pacote `treino`, testes, `pyproject.toml`, `alembic.ini` com `%(here)s`), `android/` (Capacitor com `android.path`), `scripts/iniciar-treino.bat`; `config.ROOT` continua na raiz do repositório (`.env`, `data/`, `web/dist`); caches e builds apagados; testes, build do painel e `gradlew assembleDebug` (JDK 21) passando.
4. [x] **Qualidade local** (ADR 0016): `ruff` (lint e formatação) com configuração no `pyproject.toml`, `mypy` gradual (decisão 4), oxlint no painel (o ESLint com `typescript-eslint` não aceita o TypeScript 7), script `checagens` (travessão, arquivos proibidos, padrões de dado pessoal, segredos), `pre-commit` rodando a parte rápida antes de cada commit; corrigir o que aparecer.
5. [ ] **CI no GitHub Actions** (`.github/workflows/ci.yml`), em cada pull request e na `main`: Python (ruff, mypy, pytest), painel (ESLint, tipos, vitest, build), checagens do projeto, `gitleaks` em todo o histórico, `pip-audit` e `npm audit`. Tempo alvo: menos de 5 minutos.
6. [ ] **Dependências e segurança**: Dependabot (pip, npm, gradle, actions), `docs/seguranca.md` (o que protegemos, de quem e como; checklist do OWASP ASVS nível 1 para a fase 9), pasta `docs/runbooks/` (segredo vazado, restaurar backup, derrubar sessões).
7. [ ] **GitHub organizado** (com o `gh`): labels (área, tipo, prioridade), modelos de issue (tarefa, bug, decisão) e de pull request (checklist do `/fechar-fase`), milestones das fases 8 a 12, quadro no GitHub Projects, issues das etapas da fase 9, `main` protegida (só por PR com CI verde). A partir daqui, toda etapa vira branch e PR.
8. [ ] **Skills e versão**: `/planejar-fase` passa a criar a milestone e as issues; `/fechar-fase` passa a conferir o CI e a criar a tag e a Release no GitHub; primeira Release (`v0.7.0`, a da fase 7) criada a partir do CHANGELOG.

## Critério de pronto
- [ ] CI verde na `main`; um PR de teste com um teste quebrado é bloqueado; outro com um segredo falso (sintético) é pego pelo `gitleaks`.
- [ ] Auditoria final do histórico público sem o número do export e sem o e-mail antigo.
- [ ] Teste manual: no Gemini CLI, na pasta do projeto, `/memory show` mostra as regras do `AGENTS.md`; pedir a ele "qual a próxima tarefa?" e ele achar a issue aberta.
- [ ] Docs atualizadas (README com selo do CI, CONTRIBUTING, processo, segurança, CHANGELOG).

## Resultado (preenchido no fechamento)
