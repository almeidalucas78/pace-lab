# Segurança

O que o Pace Lab protege, de quem e como. Para relatar um problema, veja o [SECURITY.md](../SECURITY.md).

## O que protegemos

| Dado | Por que importa | Onde fica hoje |
|---|---|---|
| GPS dos treinos | Mostra onde a pessoa mora e a rotina dela | Banco local (`data/`) |
| Saúde (FC, VO2max, sensações) | Dado sensível pela LGPD | Banco local |
| Conversas com a IA | Podem ter qualquer coisa que a pessoa contou | Banco local |
| Segredos (`API_TOKEN`, chave do Gemini) | Dão acesso aos dados e à cota da pessoa | `.env` (fora do git) |
| Código e histórico | Repositório público: qualquer vazamento fica exposto | GitHub |

## De quem

- **Quem lê o repositório público:** não pode achar dado pessoal nem segredo (checagens, gitleaks e pre-commit).
- **Quem está na mesma rede:** hoje a API só escuta em `127.0.0.1` e o celular chega pelo Tailscale (rede privada).
- **Dependência comprometida:** Dependabot com espera de 7 dias, `pip-audit` e `npm audit` no CI, versões travadas no `package-lock.json`.
- **A partir da fase 9 (API pública com contas):** quem tenta entrar na conta de outro, ler dados de outro usuário ou derrubar o servidor.

## Como (hoje)

- Nada pessoal no git: `.gitignore`, `scripts/checagens.py` (com padrões privados em `data/checagens-locais.txt`), gitleaks em todo o histórico no CI.
- Token na API (`Authorization: Bearer`), comparado em tempo constante (`secrets.compare_digest`); painel servido pela própria API.
- A IA do chat não acessa arquivos nem comandos (`tools=[]`); as ferramentas devolvem fichas resumidas, nunca GPS.
- Mapa com tiles do OpenStreetMap: o navegador baixa as imagens da região, mas o traçado não sai do aparelho.
- Backups do banco fora do repositório (`D:\dados\strava\`).

## Checklist para a fase 9 (OWASP ASVS 5.0, nível 1)

O ASVS (asvs.owasp.org, versão 5.0.0 de 30/05/2025) é a lista de verificação de segurança de aplicações da OWASP; o nível 1 é o mínimo para qualquer app na internet. Itens que a fase 9 precisa cumprir, em linguagem nossa (conferir cada um contra o texto do ASVS ao implementar):

- [ ] **Senhas:** guardadas só com hash forte e lento (Argon2id ou bcrypt), mínimo de 8 caracteres, sem limite baixo de tamanho, checagem contra senhas vazadas comuns.
- [ ] **Login:** limite de tentativas por conta e por IP; mesma mensagem para "conta não existe" e "senha errada".
- [ ] **Google:** `state` e PKCE no OAuth; aceitar o `id_token` só com emissor, público e validade conferidos.
- [ ] **Sessões:** cookie `HttpOnly`, `Secure`, `SameSite`; token de acesso curto e de renovação com rotação, guardado só como hash; "sair" invalida no servidor (ADR 0015).
- [ ] **Separação de dados:** toda consulta filtrada pelo usuário logado; testes provando que um usuário não lê nem altera dados de outro.
- [ ] **Entrada:** validação de tudo que chega na API (Pydantic), limites de tamanho no envio de treinos e no chat.
- [ ] **Saída:** respostas sem dados internos; erros sem rastreamento de pilha em produção.
- [ ] **HTTPS em tudo**, com HSTS; cabeçalhos de segurança no painel (CSP, `X-Content-Type-Options`, `Referrer-Policy`).
- [ ] **CSRF:** `SameSite` no cookie e checagem de origem nas rotas que gravam.
- [ ] **Segredos no servidor:** só em variáveis de ambiente ou arquivo com permissão restrita, nunca dentro da imagem do contêiner.
- [ ] **Registros (logs):** login, falhas de login e mudanças de conta registrados, sem senhas, tokens nem GPS.
- [ ] **Backup** diário criptografado e teste de restauração.

## Runbooks

O que fazer quando algo dá errado, passo a passo:
- [Segredo vazado](runbooks/segredo-vazado.md)
- [Restaurar o banco a partir de um backup](runbooks/restaurar-backup.md)
- [Tirar o acesso de todos os aparelhos](runbooks/derrubar-sessoes.md)
