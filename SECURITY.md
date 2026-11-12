# Segurança

O Pace Lab guarda dados de saúde e de localização (GPS das corridas). Problemas de segurança são levados a sério.

## Como relatar uma vulnerabilidade

**Não abra uma issue pública.** Use a aba **Security** deste repositório, em **Report a vulnerability** (relato privado do GitHub). Inclua:

- o que é o problema e onde está (arquivo, rota, versão ou commit);
- como reproduzir;
- o impacto que você imagina.

Resposta inicial em até 7 dias. Este é um projeto pessoal, mantido por uma pessoa, sem programa de recompensa.

## Versões cobertas

Só a versão mais recente da `main`.

## O que está no escopo

- A API (`treino/api/`), a autenticação e a separação de dados entre usuários (a partir da fase 9).
- O app Android e o painel web.
- Vazamento de dados pessoais ou de segredos no repositório.

Dados reais de usuários nunca estão no repositório nem nos testes; se encontrar algo que pareça dado real (coordenadas, tokens, e-mails), relate pelo canal acima.
