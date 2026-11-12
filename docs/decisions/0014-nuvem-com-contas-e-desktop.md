# 0014. Nuvem com contas (Oracle, Postgres, login com Google) e Pace Lab Desktop em Electron

- Status: aceita
- Data: 2026-11-11

## Contexto
O usuário quer parar de depender do PC ligado e do `.bat`, e quer um dia mandar o Pace Lab para outras pessoas, cada uma com login e os próprios dados, sem gastar nada além de, no máximo, uma hospedagem. Verificado em 11/11/2026:
- A leitura do Samsung Health só existe no aparelho (SDK no Android; a API de nuvem da Samsung é só para parceiros, developer.samsung.com/health/server/partner-only). O app Android continua lendo e enviando.
- Oracle Always Free (docs.oracle.com, Always Free Resources): Ampere A1 com 2 OCPUs e 12 GB, 200 GB de disco; máquina ociosa por 7 dias pode ser recolhida.
- O Claude Agent SDK proíbe oferecer o login do claude.ai em produtos de terceiros sem aprovação (code.claude.com/docs/en/agent-sdk/overview); existe em TypeScript (`@anthropic-ai/claude-agent-sdk` 0.3.322, Node 18+, com o binário para Windows).
- Login com Google em app desktop: navegador do sistema, redirecionamento para `127.0.0.1` e PKCE; tela de login dentro da janela do app é recusada (`disallowed_useragent`) (developers.google.com/identity/protocols/oauth2/native-app). Com só os escopos básicos (`openid`, `email`, `profile`), o app em modo de teste pode ser usado por qualquer conta, com aviso de "em teste" (developers.google.com, OAuth app state overview; a confirmar no projeto real).
- Electron: instalador de cerca de 85 a 200 MB; Tauri de 3 a 15 MB; memória parecida no Windows (comparativos de 2026, amostras pequenas).

## Decisão
- **Servidor na Oracle (Always Free)** com API, Postgres e painel web; é a única fonte dos dados. Os programas nunca falam direto com o banco.
- **Postgres** no lugar do SQLite (já previsto no 0004), com os dados atuais migrados para a conta do usuário.
- **Contas de usuário** com login por **Google** e por e-mail e senha; todos os dados separados por usuário; tokens próprios do Pace Lab depois do login.
- **App Android** com login, enviando os treinos para o servidor.
- **Pace Lab Desktop em Electron** (fase 10): o mesmo painel React, login, e a IA para analisar e planejar (provedores configuráveis, IA local, Claude pela assinatura só na versão do próprio usuário). Electron porque a parte de trás também é JavaScript, o que permite o Agent SDK em TypeScript sem empacotar Python.
- Custo zero: nada pago além de, no futuro, talvez a hospedagem.

## Consequências
- Substitui a autenticação por `API_TOKEN` único do 0011 e o acesso do celular só pelo Tailscale do 0012 e 0013 (a API passa a ser pública com login). Atualiza o 0009 (hospedagem decidida; o MCP remoto fica para depois, com OAuth).
- Todo o `services.py`, as ferramentas da IA e as rotas passam a receber o usuário; testes provam que um usuário não vê dados de outro.
- Quem assina o Claude conecta pelo botão "Conectar ao Claude" do desktop (extensão do Claude Desktop, fase 10), não pelo login da assinatura dentro do Pace Lab.
- Entre a fase 9 (nuvem) e a 10 (desktop), o chat com o Claude pela assinatura fica indisponível (ele volta no desktop); o chat do painel web usa o Gemini.
- Dados de saúde são sensíveis pela LGPD: antes de outras pessoas usarem, termo de consentimento, política de privacidade, exportar e apagar conta (fase 12).
- Risco da Oracle recolher a máquina ociosa: monitorar; plano B pago mais barato é a Hetzner (cerca de € 5,49/mês em 11/2026).
