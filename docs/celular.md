# Pace Lab no celular

Abre o painel no celular de qualquer lugar, com o PC ligado e o `treino servico` aberto, pelo Tailscale (ADR 0009 e 0012). Nada fica aberto na internet: só os seus aparelhos logados na sua conta Tailscale chegam ao PC.

Passos conferidos na documentação oficial do Tailscale em 09/11/2026.

## 1. Instalar o Tailscale (uma vez)

**PC (Windows):**
1. Baixe em https://tailscale.com/download/windows e instale.
2. O ícone aparece na bandeja, perto do relógio (se não, clique na setinha `^`).
3. Botão direito no ícone, **Log in**, e entre com a sua conta Google.

**Celular (Android):**
1. Instale o **Tailscale** pela Play Store.
2. **Get Started**, **Sign in with Google** com a **mesma conta** do PC.
3. Aceite criar a configuração de VPN. Só o tráfego para os seus aparelhos passa pelo Tailscale.

## 2. Configurar a rede (uma vez)

No painel do Tailscale (https://console.tailscale.com/admin/machines), com os dois aparelhos aparecendo:

1. **Nome do PC (opcional):** menu `...` na linha do PC, **Edit machine name**, ex.: `pacelab`. O nome vai para o endereço e para um registro público de certificados: use um nome neutro.
2. **Nome da rede (recomendado):** página **DNS**, **Rename tailnet**, escolha um nome aleatório. Também fica público. Depois de usado no HTTPS, não dá para sortear outro.
3. **HTTPS:** página **DNS**: confira que o **MagicDNS** está ligado e, em **HTTPS Certificates**, clique em **Enable HTTPS**.

## 3. Ligar o painel ao Tailscale (uma vez)

No PowerShell do PC:

```powershell
tailscale serve --bg 8000
```

O comando mostra o endereço, no formato `https://pacelab.nome-da-rede.ts.net`. Com `--bg` ele fica ativo e volta sozinho depois de reiniciar o PC. O `treino servico` continua escutando só em 127.0.0.1: o Tailscale é que faz a ponte.

Para desligar: `tailscale serve reset`.

Coloque o endereço no `.env` e reabra o Treino:

```
PAINEL_URL_CELULAR=https://pacelab.nome-da-rede.ts.net
```

## 4. Conectar o celular

1. No PC, abra o painel e vá em **Conectar celular**, depois **Mostrar QR code**.
2. No celular, com o Tailscale ligado, aponte a câmera para o QR e abra o link. O painel já entra conectado (o token vai no link e é apagado da barra de endereço).
3. No Chrome do celular: menu ⋮, **Instalar app** (ou **Adicionar à tela inicial**).

O QR code contém o token de acesso: não compartilhe nem tire foto dele. Se ele vazar, troque o `API_TOKEN` no `.env` e conecte de novo.

## Como funciona no dia a dia

- **PC ligado:** o app mostra na hora os dados guardados e busca os novos em seguida. Busca de novo ao voltar para o app e no botão **Atualizar**.
- **PC desligado ou Tailscale desligado:** o app abre e mostra os dados já vistos neste aparelho, com o aviso "PC fora do ar" e a hora dos dados. Chat e alterações precisam do PC.
- **Treinos novos:** chegam ao PC a cada 30 min (`SYNC_INTERVALO_MIN`) e aparecem no celular na próxima atualização.
- **Dados no celular:** ficam guardados por até 30 dias. **Sair** apaga tudo do aparelho.
- **Versão nova do painel:** depois de um `npm run build` no PC, o app avisa "Há uma versão nova" na próxima vez que abrir.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "PC fora do ar" com o PC ligado | Confira se o Tailscale está ligado no celular e se a janela do Treino está aberta no PC. |
| O link não abre | Rode `tailscale serve --bg 8000` de novo no PC e confira o endereço no `.env`. |
| Não aparece "Instalar app" | Só aparece em HTTPS (endereço `https://...ts.net`), não pelo IP. Use o Chrome. |
| Pede o token de novo | O `API_TOKEN` do `.env` mudou: conecte de novo pelo QR code. |
