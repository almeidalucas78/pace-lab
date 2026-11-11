# Fase 7: Pace Lab como app Android com os treinos do Samsung Health (com GPS)

- Status: concluída
- Planejada em: 2026-11-10 · Concluída em: 2026-11-11

## Objetivo
O usuário tem **um app só** no celular além do Tailscale: o Pace Lab. Ao abrir o app (ou voltar para ele), os treinos novos do Samsung Health, **com percurso de GPS**, FC, velocidade e cadência ao longo do treino, são lidos e enviados ao PC pelo Tailscale, entram no banco sem duplicar o histórico do Strava e aparecem no painel (com mapa e parciais) e no chat. O painel continua o mesmo da fase 6, agora dentro do app. Quando sair versão nova do app, ele avisa e baixa sozinho.

## Fora do escopo
- Leitura com o app fechado (segundo plano): exige código nativo próprio em Kotlin (ver decisão 2). Fica para uma fase seguinte.
- Play Store: instalação direta do arquivo do app.
- Musculação detalhada do Hevy e hospedagem (fase 8).

## Verificado antes de propor (10/11/2026)
- **PC:** Java 21 (Temurin) instalado; Node 24. Sem Android SDK nem Android Studio.
- **Capacitor 8.6.0** (estável; o 9 está em beta). Requisitos (capacitorjs.com/docs/getting-started/environment-setup): Node 22+, **Android Studio 2025.2.1 ou mais novo**, Android SDK API 24+ (36 é o atual); o Android Studio traz o JDK certo.
- **Painel dentro do app:** a documentação do Capacitor diz que `server.url` (carregar o painel do PC) "não é para produção". Então o painel vai embutido no app (origem `https://localhost`) e fala com a API pelo endereço do Tailscale, o que exige liberar essa origem no backend (CORS).
- **Plugins do Health Connect para Capacitor 8:**
  - `@capgo/capacitor-health` 8.12.1 (MPL-2.0, atualizado em 09/11/2026): `requestAuthorization`, `queryWorkouts` (exercícios), `readSamples` (FC e outros), `queryAggregated`; distância, calorias, FC; histórico além de 30 dias com `requestHistoryAccess` (só em Health Connect novo). Exige política de privacidade (HTML no app ou URL). **Não menciona percurso nem segundo plano.**
  - `@flomentumsolutions/capacitor-health-extended` 0.9.5 (MIT): lê percurso e FC junto com o treino, mas a versão atual pede **Capacitor 9 beta**.
  - `@capawesome-team/capacitor-health`: não está no npm público.
- **Segundo plano:** o Background Runner do Capacitor só expõe algumas APIs próprias (fetch, armazenamento, notificações, localização) e não chama outros plugins (capacitorjs.com/docs/apis/background-runner). Ler o Health Connect com o app fechado precisa de código nativo (WorkManager) e da permissão `READ_HEALTH_DATA_IN_BACKGROUND` (developer.android.com, read-data).
- **Health Connect:** por padrão lê até 30 dias antes da primeira permissão; percurso de outro app só com o app aberto e autorização do usuário.
- **Samsung Health → Health Connect** (developer.samsung.com, FAQ do Health Connect): exercícios, FC, distância, calorias e velocidade são sincronizados; liga-se em Samsung Health > Configurações > Health Connect. Dados do relógio chegam quando ele sincroniza com o celular (ou ao abrir o Samsung Health).

- **GPS pelo Health Connect provavelmente não existe para o Samsung Health:** não há documento oficial, mas um desenvolvedor no fórum da Samsung afirma que o percurso do Samsung Health não é acessível pelo Health Connect, e um relato no `react-native-health-connect` (issue #127) diz que o percurso vem vazio para treinos do Samsung Health. Outros apps (Mi Fitness, Garmin, Strava) gravam percurso lá.
- **Teste do usuário (10/11/2026):** no app do Health Connect, a corrida de 03/11 (18:18 a 19:47, origem Samsung Health) aparece só com horário e duração, sem mapa; em outros apps (ex.: Mi Fitness) a tela mostra o percurso quando ele existe. Conclusão: o Samsung Health não envia o percurso ao Health Connect (sem documento oficial, mas três evidências na mesma direção). Fonte escolhida: Samsung Health Data SDK.
- **Teste com o DataViewer (11/11/2026):** com o modo desenvolvedor ligado, o SDK leu a corrida de 03/11 completa: `route` com 5.326 pontos, `log` com 10.904 registros, distância 17.027 m, duração 5.355 s, FC média 187 e máxima 206, cadência média 170, calorias, altitude e `vo2Max`. GPS confirmado pelo SDK.
- **Escolha do usuário (11/11/2026):** mapa logo depois da corrida pesa mais; segue o Samsung Health Data SDK. Baixou o SDK 1.1.0 (`samsung-health-data-sdk-1.1.0.zip`): `libs/samsung-health-data-api-1.1.0.aar` (tem `ExerciseSession`, `ExerciseLog` e `ExerciseLocation`; `minSdkVersion` 29), documentação apenas com links para o site, e `tool/DataViewer_1.1.0.apk` (ferramenta da Samsung para ver os dados no celular). O `.aar` fica fora do git (licença da Samsung não verificada para redistribuição); o caminho dele vai no README.
- **Export do Samsung Health** ("Baixar dados pessoais"): traz por treino um `location_data.json` (GPS) e um `live_data.json` (FC, velocidade), formato não documentado oficialmente (projeto gpxmaker, fórum da Samsung). Opção futura para importar histórico com GPS de uma vez.
- **Samsung Health Data SDK** (developer.samsung.com/health/data): o `ExerciseSession` tem `route` (lista de `ExerciseLocation`: horário, latitude, longitude, altitude, precisão) e `log` (`ExerciseLog`: horário, FC, cadência, potência, velocidade), além de distância, calorias e FC média/máxima. É o mesmo nível de detalhe dos TCX do Strava.
  - **Modo desenvolvedor** (developer.samsung.com/health/data/guide/developer-mode.html): permite **ler** dados no próprio celular **sem pedir parceria**. Ativa-se em Samsung Health > Configurações > Sobre o Samsung Health, tocando 10 vezes na versão, e ligando "Developer Mode for Data Read". A Samsung diz que o modo é para teste e depuração; parceria só é exigida para gravar dados ou publicar o app.
  - Requisitos: Android 10+, Samsung Health 6.30.2+, Java 17+. O SDK (arquivo `.aar`) é baixado no site da Samsung com conta Samsung; não está no Maven.
  - Não há plugin pronto para Capacitor; os de React Native (`@obitrain/react-native-samsung-health`, `rn-samsung-health-data-api`) não cobrem treino com percurso. O acesso será por um plugin próprio em **Kotlin**, em qualquer framework.

## Decisões necessárias

1. **Fonte dos treinos:** o usuário exige GPS (10/11/2026). Recomendação: ler direto do **Samsung Health Data SDK em modo desenvolvedor**, por um plugin próprio em Kotlin (treino, percurso, FC, velocidade, cadência). O Health Connect deixa de ser necessário. Ponto de atenção: a Samsung descreve o modo desenvolvedor como recurso de teste; para uso pessoal no próprio celular funciona, mas a Samsung pode mudá-lo. Se um dia parar, o plano B é o Health Connect sem GPS.
1a. **App para outras pessoas no futuro** (usuário, 10/11/2026): quer um app "redondo", usável por um amigo ou publicado na Play Store, sem passos fora do app. O modo desenvolvedor não serve para isso (a Samsung pede para não orientar usuários a ligá-lo); para outras pessoas é preciso **parceria aprovada pela Samsung** (código de acesso) ou o **Health Connect** (oficial na Play Store, mas sem GPS do Samsung Health). Por isso: a leitura fica atrás de uma "fonte de treinos" com formato próprio; agora só a fonte Samsung em modo desenvolvedor; com parceria, basta configurar o código de acesso; a fonte Health Connect entra quando o app for para outras pessoas. A rota do backend não depende da fonte.
1b. **Framework:** Capacitor (reaproveita todo o painel React de `web/`), não React Native (exigiria reescrever o painel, gráficos e mapa, e o Kotlin para o Samsung SDK seria necessário do mesmo jeito).
2. **Quando sincroniza:** recomendação: ao abrir o app, ao voltar para ele e num botão "Sincronizar". Leitura com o app fechado fica para depois (código nativo em Kotlin). Na prática: terminou o treino, abriu o Pace Lab, o treino entra.
3. **Conectar o app ao PC:** recomendação: a página Conectar celular ganha um segundo QR que abre o app instalado (link `pacelab://conectar`) com o endereço do Tailscale e o token. Sem digitar nada.
4. **HC Webhook e a busca pelo PC (ADR 0002 e 0006):** recomendação: o celular passa a **enviar** para o PC (`POST /api/saude/treinos`); o código que buscava no HC Webhook e o agendador do serviço são removidos ao fim da fase, quando o app estiver funcionando. A notificação do Windows de treino novo continua, disparada pelo envio do app.
5. **App pelo navegador (fase 6):** recomendação: o app Android substitui o app instalado pelo navegador no celular (o mesmo painel). O painel no navegador do PC continua igual.
6. **Instalação e atualização:** o usuário quer que o app detecte e baixe versões novas sozinho (10/11/2026). Recomendação: primeira instalação pelo cabo USB; depois, ao abrir, o app consulta a versão no PC (`/api/app/versao`), baixa o APK novo pelo Tailscale e abre o instalador do Android (o usuário só toca em "Instalar"; instalar sem toque nenhum não é possível fora da Play Store, a confirmar). Atualizações só do painel poderiam até ser aplicadas sem reinstalar; verificar na implementação.

Respostas de 10/11/2026: Capacitor, atualização pelo app e conta Samsung aceitos; fonte Samsung Health Data SDK em modo desenvolvedor aceita, com a leitura atrás de uma "fonte de treinos" para trocar por parceria Samsung ou Health Connect quando o app for para outras pessoas; 2 a 5 aceitas antes; 6 mudou (atualização pelo próprio app). Viram o ADR 0013; 0002 e 0012 ficam marcadas como substituídas (no que mudou).

## Mudanças no banco
Nenhuma. Os treinos do app entram como `source="samsung_health"` (a fonte `health_connect` fica reservada para o futuro), com o id do treino na fonte; o último envio fica em `sync_state` (tabela existente).

## O que o usuário instala ou configura
- **PC:** Android Studio (alguns GB; traz o SDK e o JDK).
- **Celular:** depuração USB ligada (Opções do desenvolvedor) e o modo desenvolvedor do Samsung Health (leitura de dados) ligado.
- **Conta Samsung** para baixar o SDK no site da Samsung.

## Etapas
1. [x] **Base do app**: Capacitor 8 no `web/` (`npx cap add android`), nome, ícone e id do app; o painel embutido abre no celular; instalação pelo cabo. Sem saúde ainda.
2. [x] **App fala com o PC**: endereço da API configurável no cliente (no app: endereço do Tailscale; no navegador: o próprio site); CORS no backend só para a origem do app; QR com link `pacelab://conectar`; testes.
3. [x] **Backend recebe treinos**: `POST /api/saude/treinos` com formato próprio e simples (sessão, FC, distância, calorias, velocidade); conversor puro em `ingest/`, reaproveitando a gravação idempotente e a deduplicação com o Strava; `sync_state`; notificação do Windows; testes sintéticos.
4. [x] **App lê o Samsung Health**: "fonte de treinos" com formato próprio (no app e na rota do backend) e a primeira fonte: plugin próprio em Kotlin com o Samsung Health Data SDK (permissões, treinos com percurso e log), leitura desde a última marca guardada no aparelho, envio em lotes, ao abrir, ao voltar e no botão; situação da última sincronização na tela; testes do lado web com o plugin simulado.
4b. [x] **Atualização do app**: versão publicada pelo PC, aviso de versão nova, download do APK e instalador do Android. Feito em 11/11/2026: `treino publicar-app`, `/api/app/versao` e `/api/app/apk`, versionCode automático (minutos desde 01/01/2026), plugin `AtualizacaoPlugin.kt` (PackageInstaller). Testado pelo usuário: atualizou; o Play Protect avisou e bloqueou, com opção de instalar mesmo assim (pendência no ROADMAP).
5. [x] **Validação com dados reais**: primeira sincronização (treinos de 27/10 em diante), conferência com o usuário, ajustes no conversor; anotar em `docs/dados.md` o que o Samsung Health realmente grava. Feito em 11/11/2026: 40 treinos; esteira e musculação vinham com GPS (0, 0), corrigido no conversor (distância pela velocidade) e reprocessado com `treino reprocessar-app`.
6. [x] **Limpeza e docs**: remover o cliente do HC Webhook e o agendador (decisão 4); ADR 0013; ARCHITECTURE, README, `docs/celular.md`, CHANGELOG, regras.

## Critério de pronto
- [x] `pytest`, `npm run build` e `npm test` passando; testes novos: conversor do formato do app, rota `/api/saude/treinos` (idempotente, duplicata com o Strava, sessão apagada), CORS só para a origem do app, link `pacelab://conectar`, sincronização no app com o plugin simulado. No fechamento: 49 no backend, 40 no painel.
- [x] Teste manual (usuário): app instalado pelo cabo, modo desenvolvedor ligado, QR lido, permissões dadas; treinos de 27/10 em diante no painel com mapa e parciais, sem duplicar com o Strava; musculação de 11/11 entrou ao abrir o Pace Lab; chat respondeu sobre a corrida de 03/11 (e revelou o erro de parciais, corrigido); versão nova oferecida e instalada pelo app.
- [x] Docs atualizadas.

## Resultado (preenchido no fechamento)
**Entrou:** app Android Pace Lab (Capacitor 8, painel embutido) com plugin próprio em Kotlin que lê o Samsung Health Data SDK em modo desenvolvedor: treinos com percurso de GPS, FC, velocidade e cadência, enviados ao PC (`POST /api/saude/treinos`) ao abrir, ao voltar e no botão Sincronizar; conexão por QR (`pacelab://conectar`); CORS só para a origem do app; notificação do Windows a cada treino novo; atualização do app pelo próprio app (`treino publicar-app`, `/api/app/versao`, `/api/app/apk`, PackageInstaller); `treino reprocessar-app`.

**Mudou em relação ao plano:**
- Fonte: o plano começou pelo Health Connect; o teste do usuário mostrou que o Samsung Health não manda o percurso para lá, então a fonte virou o Samsung Health Data SDK (ADR 0013). A leitura fica atrás de uma "fonte de treinos" para trocar por parceria Samsung ou Health Connect.
- Dados reais pediram dois ajustes no conversor: esteira e musculação chegam com GPS (0, 0) (distância pela velocidade) e GPS, FC e velocidade chegam em registros com horários desencontrados (pontos próximos juntados e parciais por janela de 3 s). Antes, a corrida de 03/11 mostrava km a 1:16/km. Ver `docs/dados.md`.
- Removidos o HC Webhook e o agendador (ADR 0002 e 0006 substituídas por 0013); `treino servico` e `treino api` agora são o mesmo serviço.

**Pendente:** aviso do Play Protect na atualização (ROADMAP); leitura com o app fechado; sessão "OTHER" que o Samsung grava junto com a musculação; natação na piscina mapeada como "other"; peso do Hevy (fase 8).
