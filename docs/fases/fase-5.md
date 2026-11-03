# Fase 5: painel web desktop

- Status: concluída
- Planejada em: 2026-10-28 · Concluída em: 2026-11-02

## Objetivo
O usuário abre `http://127.0.0.1:8000` no navegador (com `treino servico` rodando) e vê os treinos em gráficos: forma, fitness e fadiga; volume por semana; cada treino com mapa, parciais e gráficos de FC e ritmo; o plano ativo com a situação de cada sessão. Em qualquer página ele abre o chat com o treinador ao lado, sem sair do que está vendo.

## Fora do escopo
- Layout de celular e PWA (fase 6). O painel já nasce com CSS que não quebra em tela menor, mas sem otimizar.
- Respostas do chat aparecendo aos poucos (streaming); a resposta chega inteira, com indicador de "pensando".
- Editar plano ou treino por formulário: alterações continuam pelo chat.
- Hospedagem, login de verdade, vários usuários (fase 7).

## Verificado antes de propor (28/10/2026)
- Node 24.18 e npm 12 instalados no PC.
- Versões atuais no npm e compatíveis entre si: React 19.3, Vite 8.3 (`create-vite` 9.3), TypeScript 7.0, `@vitejs/plugin-react` 6.1 (pede Vite 8), React Router 8.5 (pede React 19.2.7+), TanStack Query 5.105, Recharts 3.10 (aceita React 19), Leaflet 1.9.4 + React Leaflet 5.0 (pede React 19).
- Mapa com tiles do OpenStreetMap (operations.osmfoundation.org/policies/tiles): permitido para uso leve com atribuição visível, HTTPS, Referer enviado e sem download para uso offline. URL dos tiles configurável.

## Decisões necessárias

1. **API com prefixo `/api`?** Recomendação: sim. O painel fica na raiz (`/`, `/treinos/356`, `/plano`) e a API em `/api/...`, no mesmo processo e endereço. Hoje só os testes e a CLI usam as rotas; nada de fora quebra.
2. **Como o painel se autentica?** Recomendação: na primeira vez, uma tela pede o `API_TOKEN` do `.env`, que fica salvo no navegador. Funciona igual quando o acesso vier pelo Tailscale (fase 6).
3. **Chat:** recomendação: painel lateral que abre em qualquer página, com histórico de conversas e escolha de Claude ou Gemini. Quando aberto na página de um treino ou do plano, a mensagem leva junto "estou vendo o treino #356" para a IA saber do que se trata.
4. **Gráficos e mapa:** recomendação: Recharts para os gráficos (simples, declarativo, bom para algumas centenas de pontos) e Leaflet com tiles do OpenStreetMap para o mapa. Observação de privacidade: o traçado do GPS nunca sai do PC, mas o navegador baixa do OpenStreetMap as imagens da região exibida, então o servidor deles vê qual área foi aberta.
5. **Páginas:** recomendação: Visão geral, Treinos (lista e detalhe), Plano, e o chat lateral. Algo a acrescentar ou tirar?

Respondidas em 28/10/2026: todas as recomendações aceitas, com o front em `web/` no mesmo repositório. Registrado no [ADR 0011](../decisions/0011-painel-web.md).

## Mudanças no banco
Nenhuma.

## Etapas
1. [x] **Backend para o painel**: rotas atuais passam para `/api` (um `APIRouter`); rotas que faltam: `GET /api/perfil` (FC máxima e zonas), `GET /api/carga/atual`; servir `web/dist` na raiz com retorno do `index.html` para as rotas do painel; testes em `tests/test_api.py`. CLI e testes atualizados.
2. [x] **Base do front** em `web/`: projeto Vite + React + TypeScript; proxy do Vite para a API no desenvolvimento; cliente da API com o token; tipos TypeScript das respostas; layout com menu; rotas; tela do token; tema claro e escuro seguindo o sistema. `node_modules` e `web/dist` no `.gitignore`.
3. [x] **Visão geral**: forma, fitness e fadiga de hoje com a variação em 7 dias; gráfico de 90 dias (carga diária em barras, fitness e fadiga em linhas, forma em área); volume das últimas 12 semanas; cartão do último treino; semana atual do plano com cores por status.
4. [x] **Treinos**: lista com filtro de esporte e paginação; detalhe com resumo, mapa do percurso, gráficos de FC, ritmo e altitude ao longo da distância, tabela de parciais, tempo por zona, qualidade da FC e sensações registradas.
5. [x] **Plano**: plano ativo em semanas (cada sessão com metas, status e o treino casado, com link), resumo da aderência, histórico de planos.
6. [x] **Chat lateral**: lista de conversas, mensagens, escolha de provedor ao começar, ferramentas consultadas em cada resposta, indicador de "pensando", contexto da página atual; atualiza os dados da tela quando a IA salva ou altera um plano.
7. [x] **Integração e docs**: `treino servico` serve o painel já compilado; `npm run build` documentado; `iniciar-treino.bat` avisa se falta o build; ADR 0011; README, ARCHITECTURE e CLAUDE.md (mapa do código e regra para `web/`).

## Critério de pronto
- [x] `pytest` passando, com testes novos das rotas `/api` e do retorno do `index.html`.
- [x] `npm run build` sem erros de TypeScript.
- [x] Testes do front com Vitest para formatadores (ritmo, duração, datas) e para o cliente da API (token e erro 401).
- [x] Teste manual: com `treino servico` aberto, entrar em `http://127.0.0.1:8000`, informar o token, ver a visão geral com os dados reais, abrir a corrida de 20/10/2026 com mapa, parciais e gráficos, ver o plano de teste com as cores de cada sessão e, na página da corrida, perguntar no chat "o que você achou desse treino?" e receber uma resposta sobre ela.
- [x] Docs atualizadas.

## Resultado (preenchido no fechamento)

**Entrou:** painel em `web/` (React 19, Vite 8, TypeScript 7, React Router 8, TanStack Query, Recharts, Leaflet) com Visão geral, Treinos (lista e detalhe com mapa, gráficos de FC, ritmo e altitude, parciais, zonas e sensações), Plano (semanas com status, aderência e histórico) e chat lateral com contexto da página; API em `/api` e painel compilado servido na raiz pelo mesmo processo; ADR 0011; regra `.claude/rules/web.md`. Testes: 41 no backend, 14 no front (formatadores, cliente da API e renderização das 4 páginas com respostas no formato real).

**Mudou em relação ao plano:**
- O chat manda o contexto da página num campo próprio (`contexto`), que vai para a IA mas não é gravado na conversa; assim o histórico e o título ficam limpos.
- O detalhe do treino na API passou a trazer as sensações (antes só a ficha da IA trazia).
- Teste de fumaça das páginas em jsdom no lugar de só testar formatadores e cliente: pega erros de renderização sem abrir navegador.
- `treino servico` confere a porta antes de subir e explica quem a ocupa (apareceu um `treino api` antigo, sem janela, preso na porta 8000 no teste do usuário); `iniciar-treino.bat` abre o navegador sozinho.
- `.gitignore`: `activities*` virou `/activities*` (o padrão antigo pegaria arquivos do front).

**Teste manual:** em 28/10/2026, com o banco real, conferi as rotas servidas, a corrida de 20/10 (600 pontos, 594 com GPS), a aderência (33%) e o chat com contexto (o Claude consultou o treino #4 e comentou o salto suspeito da FC no último km). Em 02/11/2026 o usuário navegou pelas telas e confirmou que está tudo certo.

**Pendente:** pacote do front com cerca de 1 MB (308 kB comprimido) por causa de gráficos e mapa; dividir na fase 6, junto com o celular.
