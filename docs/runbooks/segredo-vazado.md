# Runbook: segredo vazado

Quando um token ou chave (`API_TOKEN`, chave do Gemini, token do GitHub) apareceu onde não devia: commit, issue, print, log.

1. **Trocar o segredo primeiro**, antes de limpar qualquer coisa. Apagar o commit não adianta: quem copiou já tem.
   - `API_TOKEN`: gerar outro com `.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"`, pôr no `.env`, reiniciar o serviço e reconectar o celular pelo QR code (página Conectar celular).
   - Chave do Gemini: apagar a chave no Google AI Studio e criar outra; atualizar `GEMINI_API_KEY` no `.env`.
   - Token do GitHub: revogar em github.com/settings/tokens, ou `gh auth logout` seguido de `gh auth login`.
2. **Ver se foi usado:** uso e cota no Google AI Studio; registros do serviço.
3. **Limpar onde apareceu:** editar ou apagar a issue ou o comentário. Se entrou num commit da `main`, reescrever o histórico só se o segredo não puder ser trocado (com backup `git bundle` antes; foi o que se fez na fase 8, etapa 1). O GitHub pode manter cópias em cache dos commits antigos; para apagá-las, pedir ao suporte do GitHub.
4. **Evitar de novo:** se o `scripts/checagens.py` ou o gitleaks não pegaram, acrescentar o padrão (em `data/checagens-locais.txt` se for privado).
5. Anotar o que aconteceu e o que mudou no CHANGELOG, numa seção "Segurança".
