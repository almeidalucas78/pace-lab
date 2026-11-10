# Fase 6: painel no celular

- Status: concluída
- Planejada em: 2026-11-02 · Concluída em: 2026-11-10

## Objetivo
Com o PC ligado e o `treino servico` aberto, o usuário abre o Pace Lab no celular de qualquer lugar (casa ou rua), pelo Tailscale, e instala como app na tela inicial. As telas funcionam bem no celular: navegação por barra inferior, listas em cartões, plano dia a dia e o chat em tela cheia. Conectar o celular é ler um QR code no painel do PC, sem digitar o token.

## Fora do escopo
- Acesso com o PC desligado (hospedagem, fase 7).
- Notificações push no celular.
- Atualização em tempo real (push do servidor): os dados atualizam ao abrir o app, ao voltar para ele e ao puxar a tela.
- Mudar a sincronização com o Health Connect (continua o PC puxando pela Wi-Fi, ADR 0002).

## Verificado antes de propor (02/11/2026)
- **Tailscale, plano Personal:** grátis, até 6 usuários e aparelhos ilimitados (tailscale.com/pricing). A página de preços não diz explicitamente se certificados HTTPS e `serve` estão no plano grátis; confirmamos na hora de ativar.
- **`tailscale serve`** (tailscale.com/kb/1242): repassa uma porta local para o tailnet em `https://<nome-do-pc>.<tailnet>.ts.net`, só dentro do tailnet (não é público; público seria o Funnel). Com `--bg` fica ativo e volta sozinho depois de reiniciar o PC; desfaz com `tailscale serve reset`. O serviço continua escutando só em 127.0.0.1: o Tailscale é que repassa.
- **HTTPS no Tailscale** (tailscale.com/kb/1153): exige MagicDNS e ativar "HTTPS Certificates" no painel. **O nome da máquina e do tailnet vão para um registro público de certificados** (Certificate Transparency); a recomendação deles é não usar nomes com informação sensível. Dá para renomear a máquina antes.
- **Instalar como app (PWA) no Chrome** (web.dev/articles/install-criteria): precisa de HTTPS e de um manifest com nome, ícones de 192 e 512 px, `start_url` e `display: standalone`. Por isso o Tailscale com HTTPS é necessário.
- **Bibliotecas:** `vite-plugin-pwa` 2.0.0 (aceita Vite 8), `workbox-window` 7.4.1, `qrcode` 1.5.4, `@vite-pwa/assets-generator` 2.0.0 (gera os ícones PNG a partir do SVG), `@tanstack/react-query-persist-client` e `@tanstack/query-async-storage-persister` 5.107.1 (pedem `@tanstack/react-query` 5.107.1 ou mais novo: atualizar junto), `idb-keyval` 6.3.0 (IndexedDB).

## Decisões necessárias

1. **Acesso pelo Tailscale com HTTPS (`tailscale serve`).** Confirmado pelo usuário em 09/11/2026. Recomendação: sim, e antes de ativar o HTTPS renomear o PC no Tailscale para algo neutro (ex.: `pacelab`), já que o nome fica público no registro de certificados. O nome do tailnet também aparece; o Tailscale deixa trocar por um nome aleatório.
2. **Token no celular por QR code.** Aceito em 09/11/2026. Recomendação: o painel do PC ganha "Conectar celular", que mostra um QR com o endereço do Tailscale e o token no fragmento da URL (`#token=...`, parte que o navegador não envia ao servidor). O celular lê, salva o token e limpa a URL. O endereço do Tailscale fica no `.env` (`PAINEL_URL_CELULAR`).
3. **Sem conexão:** decidido pelo usuário em 09/11/2026 (mudou a recomendação): **o celular guarda os dados** que já foram vistos (cache persistente do TanStack Query no IndexedDB). Sem o PC, o app mostra os dados guardados com o aviso "PC fora do ar, dados de <data e hora>"; o chat e as alterações precisam do PC. Ao sair (botão Sair), o cache é apagado.
4. **Navegação no celular:** aceito em 09/11/2026. Recomendação: barra inferior com Visão geral, Treinos, Plano e Chat; no celular o chat vira uma tela própria (no PC continua lateral). Tabelas viram cartões; o plano vira lista por dia.
5. **Nome e ícone do app:** aceito em 09/11/2026 (pode mudar depois). Recomendação: "Pace Lab", com o ícone atual (o gráfico subindo).

Todas respondidas em 09/11/2026; viram o ADR 0012 (celular e PWA) no início da implementação.

## Mudanças no banco
Nenhuma.

## Etapas
1. [x] **Pacote menor**: cada página carrega sob demanda (mapa e gráficos só quando abertos); meta: arquivo inicial abaixo de 500 kB.
2. [x] **Layout de celular**: barra inferior, rota `/chat` (tela cheia no celular; no PC o botão continua abrindo a lateral), lista de treinos em cartões, plano em lista por dia, gráficos e mapa com altura de celular, áreas de toque maiores.
3. [x] **PWA e dados guardados**: `vite-plugin-pwa` com manifest em português, ícones gerados do SVG, service worker para as telas (nunca `/api`); cache dos dados no IndexedDB com validade de 30 dias; aviso "PC fora do ar, dados de <hora>" e "atualizado há X min"; atualizar ao voltar para o app e ao puxar a tela; Sair apaga o cache; aviso de versão nova do painel.
4. [x] **Conectar celular**: `PAINEL_URL_CELULAR` no `.env`; `GET /api/painel/config`; página no PC com o QR (biblioteca `qrcode`); o painel lê `#token=` ao abrir, salva e limpa a URL.
5. [x] **Tailscale**: guia passo a passo em `docs/celular.md` (instalar no PC e no Android, renomear o PC, ativar MagicDNS e HTTPS, `tailscale serve --bg 8000`, conferir); `treino servico` mostra o endereço do celular quando configurado.
6. [x] **Docs**: ADR 0012, README, ARCHITECTURE, CHANGELOG, regra do painel.

## Critério de pronto
- [x] `pytest`, `npm run build` e `npm test` passando; testes novos: leitura do `#token=` (salva e limpa a URL), rota `/api/painel/config`, telas renderizando no modo celular.
- [x] Arquivo inicial do painel abaixo de 500 kB.
- [x] Teste manual no celular (usuário): com o Tailscale ligado nos dois aparelhos, ler o QR no PC, abrir o Pace Lab, instalar na tela inicial, navegar por Visão geral, a corrida de 20/10 (mapa e gráficos), Plano e Chat (uma pergunta); fechar o `treino servico` e ver as telas já visitadas com o aviso de PC fora do ar e a hora dos dados.
- [x] Docs atualizadas.

## Resultado (preenchido no fechamento)

**Entrou:** Tailscale com `tailscale serve --bg 8000` (`https://pacelab.<rede>.ts.net`); PWA instalável (`vite-plugin-pwa`, ícones gerados do SVG, aviso de versão nova); página Conectar celular com QR code (`#token=`) e `PAINEL_URL_CELULAR`; layout de celular (barra inferior, chat em tela cheia em `/chat`, treinos em cartões, plano dia a dia); dados guardados no aparelho (IndexedDB, 30 dias) com aviso "PC fora do ar" e hora dos dados; páginas sob demanda (arquivo inicial de 1.042 kB para 302 kB); guia `docs/celular.md`; ADR 0012. Testes: 43 no backend, 26 no front.

**Mudou em relação ao plano:**
- Guardar dados no celular: o plano recomendava não guardar; o usuário escolheu guardar (ADR 0012).
- Botão Atualizar no lugar de "puxar a tela": o gesto costuma não funcionar com o app instalado.
- Proteção contra tela preta (`ErroTela`): qualquer erro de desenho mostra a mensagem e um botão para recarregar, em vez de sumir com o painel.
- Mapas de código-fonte no build (`build.sourcemap`), para o console do navegador mostrar nomes reais.
- `treino servico` mostra o endereço do celular.

**Defeitos achados no teste do usuário e corrigidos (com teste que falhava antes):**
- Chat derrubava o painel ao enviar, no PC e no celular: o `useEffect` devolvia o resultado de `scrollIntoView`, que no Chrome é uma Promise; o React tentava chamá-la como limpeza (`destroy is not a function`). Só aparecia no navegador real, não no jsdom.
- Chat ficava vazio entre a resposta e a nova busca da conversa: agora pergunta e resposta aparecem na hora.
- Dados guardados não voltavam com o PC fora do ar: `gcTime` de 30 dias passava do limite do `setTimeout` (~24,8 dias) e descartava os dados restaurados na hora (agora `Infinity`); e o padrão do TanStack não guardava consultas cuja última busca falhou (agora guarda toda consulta com dados).
- Instalação interrompida do pacote (`pip install` com o `treino.exe` aberto) deixou o comando `treino` sem o módulo; reinstalado. Regra: reinstalar só com o serviço fechado.

**Teste manual (09 e 10/11/2026, usuário, Galaxy S23 pelo Tailscale):** QR code, app instalado, navegação, chat e "PC fora do ar" com os dados guardados, tudo funcionando.

**Pendente:** nada desta fase.
