# 0017. Contas e login: tokens opacos, Argon2id, cadastro fechado por lista e Google sem biblioteca de OAuth

- Status: aceita
- Data: 2026-11-18

## Contexto
A fase 9 (etapa 2, issue #6) cria as contas de usuário previstas no ADR 0014, com as sessões do ADR 0015. Verificado em 18/11/2026:
- argon2-cffi 25.1.0: `PasswordHasher` usa Argon2id com o perfil "RFC 9106 de pouca memória" (cerca de 64 MB), com `verify` e `check_needs_rehash` (argon2-cffi.readthedocs.io).
- Google (developers.google.com/identity/openid-connect/openid-connect): fluxo de código no servidor; `state` e `nonce`; `sub` é a chave estável do usuário (o e-mail pode mudar); o documento de descoberta anuncia PKCE S256. O `google-auth` (já instalado com o `google-genai`) confere assinatura, emissor, público e validade do `id_token` com `verify_oauth2_token`.
- Authlib: a versão mais nova saiu em 17/11/2026, um dia antes; não adotamos versões com menos de duas semanas.
- OWASP ASVS 5.0 nível 1 (V6): senha de no mínimo 8 caracteres (15 recomendado), checagem contra pelo menos as 3.000 senhas mais comuns, troca de senha pedindo a atual, controles contra força bruta documentados e que não permitam travar a conta de outra pessoa. Checagem contra senhas vazadas e mensagens genéricas para "conta não existe" ficam para os níveis 2 e 3.

## Decisão
- **Tokens opacos** (aleatórios, prefixos `pla_` e `plr_`), guardados no banco só como hash SHA-256, sem JWT: "sair" vale na hora e não entra biblioteca de tokens. Acesso de 15 minutos, renovação de 30 dias trocada a cada uso; token de renovação já trocado usado de novo derruba a família inteira de sessões.
- **Senhas com Argon2id** (argon2-cffi), mínimo de 8 caracteres e máximo de 128, recusando as senhas mais comuns de uma lista embutida (SecLists, licença MIT; cerca de 10 mil com 8 caracteres ou mais).
- **Cadastro fechado até a fase 12:** só cria conta (por senha ou pelo Google) quem está em `CADASTRO_EMAILS` no `.env`; o comando `treino criar-usuario` cria direto no PC ou no servidor. Abrir o cadastro na fase 12 é tirar essa checagem.
- **Google sem biblioteca de OAuth:** `httpx` para trocar o código e `google-auth` para conferir o `id_token`; `state` (guardado no banco como hash, uso único, 10 minutos), cookie de vínculo com o navegador, `nonce` e PKCE S256. Conta Google com e-mail confirmado igual ao de uma conta existente é ligada a ela.
- **Limite de tentativas** em memória, contando só falhas em janela de 15 minutos: 5 por e-mail e IP, 20 por IP; a resposta é esperar (429), sem bloquear a conta para todos.
- **CSRF:** cookies `SameSite=Strict` e, em chamadas que gravam com cookie, origem igual à do próprio site (ou `https://localhost`, o app).
- **Transição:** o `API_TOKEN` continua aceito até o painel (etapa 7) e o app (etapa 8) passarem a usar o login.

## Consequências
- Cada chamada à API consulta a tabela de sessões (uma busca por índice); aceitável para poucos usuários.
- O limite de tentativas zera quando o servidor reinicia e não vale entre vários processos; se um dia houver mais de um, ele vai para o banco.
- Dois pedidos de renovação simultâneos com o mesmo token (duas abas) derrubam a sessão; o painel precisa centralizar a renovação (etapa 7).
- Atrás do Tailscale Funnel, o IP do cliente precisa vir dos cabeçalhos do proxy para o limite por IP funcionar (a configurar no servidor).
