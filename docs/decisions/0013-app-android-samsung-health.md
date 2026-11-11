# 0013. Pace Lab como app Android lendo o Samsung Health (com GPS)

- Status: aceita
- Data: 2026-11-11
- Substitui: 0002 (treinos novos pelo HC Webhook, com o PC puxando), 0006 (agendador no serviço) e, no celular, 0012 (app instalado pelo navegador)

## Contexto
O usuário quer treinos entrando sozinhos, com GPS, e um app só no celular. Verificado em 10 e 11/11/2026:
- O Health Connect não traz o percurso dos treinos do Samsung Health (teste no app do Health Connect: só horário e duração; relato no fórum da Samsung; issue #127 do `react-native-health-connect`).
- O Samsung Health Data SDK 1.1.0 entrega treino, percurso (`ExerciseLocation`) e registro ao longo do treino (`ExerciseLog`). Em modo desenvolvedor lê os dados no próprio celular sem parceria (developer.samsung.com/health/data/guide/developer-mode.html). Teste com o DataViewer leu a corrida de 03/11 com 5.326 pontos de GPS.
- Capacitor 8 empacota o painel React existente num app Android; `server.url` não é para produção, então o painel vai embutido e fala com a API pelo endereço do Tailscale.

## Decisão
- O Pace Lab vira app Android com **Capacitor 8**, reaproveitando `web/`. O acesso ao Samsung Health é um **plugin próprio em Kotlin** sobre o Samsung Health Data SDK, em modo desenvolvedor.
- A leitura fica atrás de uma **"fonte de treinos"** com formato próprio (no app e na API), para trocar por parceria Samsung ou acrescentar o Health Connect quando o app for para outras pessoas.
- O **celular envia** os treinos para `POST /api/saude/treinos` pelo Tailscale: ao abrir o app, ao voltar para ele e no botão Sincronizar. Leitura com o app fechado fica para depois.
- Conexão por QR com link `pacelab://conectar` (endereço e token). Atualização: o app consulta a versão no PC, baixa o APK novo e abre o instalador do Android.
- O cliente do HC Webhook e o agendador do serviço saem quando o app estiver funcionando. O painel no navegador do PC continua.
- O SDK da Samsung (`.aar`) não vai para o git; fica com o usuário.

## Consequências
- Mapa, parciais e zonas para treinos novos logo depois de abrir o app.
- Dependência do modo desenvolvedor do Samsung Health, que a Samsung descreve como recurso de teste e pode mudar; plano B: Health Connect sem GPS, ou o export do Samsung Health ("Baixar dados pessoais").
- Para outras pessoas: parceria com a Samsung (código de acesso) ou Health Connect; ver "Direção futura" no ROADMAP.
- Primeira instalação pelo cabo USB (depuração USB); o id do app (`app.pacelab`) fica fixo, porque é ele que a Samsung e a Play Store usam.
