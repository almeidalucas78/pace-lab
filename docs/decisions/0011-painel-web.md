# 0011. Painel web: estrutura, autenticação, chat, gráficos e mapa

- Status: aceita; a autenticação por `API_TOKEN` único foi substituída por contas com login (0014)
- Data: 2026-10-28

## Contexto
A fase 5 cria o painel desktop (ADR 0004: React + TypeScript + Vite) que fala só com a API (ADR 0005). Versões verificadas no npm em 28/10/2026: React 19.3, Vite 8.3, TypeScript 7.0, React Router 8.5, TanStack Query 5.105, Recharts 3.10, Leaflet 1.9.4, React Leaflet 5.0. Política de tiles do OpenStreetMap conferida em operations.osmfoundation.org/policies/tiles.

## Decisão
- **Estrutura:** o front fica em `web/`, no mesmo repositório, com dependências próprias (`package.json`). Não importa nada do Python.
- **Rotas:** a API passa para `/api/...`; o painel fica na raiz (`/`, `/treinos/356`, `/plano`). Em uso normal, `treino servico` serve o painel compilado (`web/dist`) e a API no mesmo endereço. No desenvolvimento, o Vite (`npm run dev`) repassa `/api` para o backend.
- **Autenticação:** na primeira vez o painel pede o `API_TOKEN` e guarda no navegador.
- **Chat:** painel lateral em todas as páginas, com histórico e escolha de provedor; a mensagem leva o contexto da página (treino ou plano que está aberto). Resposta inteira, sem streaming, com indicador de "pensando".
- **Gráficos:** Recharts. **Mapa:** Leaflet com tiles do OpenStreetMap (HTTPS, atribuição visível, URL configurável, nada de download para uso offline).
- **Páginas:** Visão geral, Treinos (lista e detalhe), Plano e o chat lateral.

## Consequências
- O traçado do GPS não sai do PC, mas o navegador baixa do OpenStreetMap as imagens da região exibida (o servidor deles vê qual área foi aberta). Usuário de acordo.
- As respostas da API são dicts sem esquema no OpenAPI; os tipos TypeScript são escritos à mão em `web/src/api/tipos.ts` e precisam acompanhar mudanças em `services.py`.
- Sem build (`web/dist`), `treino servico` serve só a API e avisa.
