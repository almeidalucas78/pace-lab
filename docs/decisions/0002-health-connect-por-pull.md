# 0002. Treinos novos do Health Connect, com o PC puxando do celular

- Status: aceita
- Data: 2026-10-27

## Contexto
O usuário usa Galaxy Watch 7, Samsung Health e Health Connect. O app HC Webhook (github.com/mcnaveen/health-connect-webhook, docs conferidas em 27/10/2026) tem dois modos: webhook (o celular envia) e servidor HTTP local (porta padrão 8787, `GET /?start=&end=`, `GET /ping`, token Bearer opcional). No modo webhook o app só olha 48 h para trás, e o PC fica desligado da meia-noite às 8h.

## Decisão
- Enquanto o sistema roda no PC, o PC **puxa** do servidor local do app pela Wi-Fi, pedindo tudo desde a última leitura bem-sucedida menos uma margem de 48 h.
- Não usar o modo webhook enquanto o sistema roda no PC.
- Ao hospedar, o app passa a enviar webhook direto para a API.

## Consequências
- Celular fora da rede não perde dados: a janela não avança e a próxima rodada recupera.
- Segundo a documentação, a sessão de exercício não traz GPS, velocidade nem potência; parciais por km só saem com registros de distância curtos.
- O conversor foi escrito pela documentação; precisa ser ajustado a um JSON real (pendência no ROADMAP).
