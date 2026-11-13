---
paths:
  - "web/**"
---

# Painel web (React)

- O painel fala só com a API (`/api/...`), via `web/src/api/cliente.ts`. Nada de importar dados de outro jeito.
- Tipos das respostas em `web/src/api/tipos.ts`, escritos à mão a partir dos dicts de `server/treino/services.py`: ao mudar uma resposta no Python, atualize o tipo e o teste de fumaça (`web/src/paginas/paginas.test.tsx`).
- Consultas em `web/src/api/consultas.ts` (TanStack Query). Chaves começam pelo recurso (`treinos`, `planos`, `carga`, `conversas`) para invalidar em grupo; o chat invalida `planos` e `treinos` depois de ferramentas que gravam.
- Textos da tela em português do Brasil, sem travessão. Formatação de números, ritmo e datas só por `web/src/util/formato.ts`.
- Datas chegam da API já no fuso local (`2026-10-20T07:52-03:00`); não converter com `new Date()` para exibir.
- Cores só pelas variáveis CSS de `estilo.css` (tema claro e escuro).
- Mapa: tiles do OpenStreetMap com atribuição visível, sem pré-carregar áreas nem uso offline (ADR 0011).
- Dados guardados no aparelho (IndexedDB, `web/src/api/persistencia.ts`, opções em `opcoesPersistencia`): ao mudar o formato de uma resposta, suba `VERSAO_DADOS` para descartar o cache antigo. `gcTime` fica `Infinity`: qualquer tempo acima de ~24,8 dias estoura o `setTimeout` e descarta os dados restaurados na hora. Nunca guardar `/api` nem tiles no service worker (`vite.config.ts`).
- Layout de celular abaixo de 720 px: barra inferior, `.so-celular` / `.so-desktop` para versões alternativas, áreas de toque de 40 px. Testar as duas versões no teste de fumaça.
- Páginas novas entram com `lazy()` em `App.tsx`, para o arquivo inicial continuar pequeno.
- `useEffect` sempre com chaves no corpo: nunca devolver valor que não seja função de limpeza (o jsdom esconde isso; no Chrome `scrollIntoView` devolve Promise e derrubou o chat).
- Antes de dizer que está pronto: `npm run lint` (oxlint, sem avisos), `npm run build` (inclui checagem de tipos) e `npm test` na pasta `web`, além do `pytest`. Exceção a uma regra do oxlint só com `// oxlint-disable-next-line regra` e um comentário com o motivo.
- Bibliotecas novas: conferir versão e `peerDependencies` no npm antes de instalar.
