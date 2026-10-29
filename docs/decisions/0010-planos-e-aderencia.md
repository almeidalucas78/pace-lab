# 0010. Planos de treino e aderência

- Status: aceita
- Data: 2026-10-28

## Contexto
Os planos nascem da conversa com a IA (ADR 0008); o sistema precisa guardá-los e medir se foram cumpridos, sem regras fixas de periodização no código.

## Decisão
- **Alteração:** ajustes pontuais (mover, mudar metas, cancelar) editam a sessão no lugar; reescritas grandes criam um plano novo, e o anterior fica `substituido` com `replaced_by` apontando para o novo. Só um plano ativo por vez. (O usuário aceitou, deixando aberto mudar no futuro.)
- **Casamento planejado x feito:** mesmo esporte no mesmo dia (fuso local); sem isso, um treino do dia anterior ou seguinte ainda não casado conta como `feita_outro_dia`. Duplicatas nunca entram. Treino sem sessão correspondente é `extra`.
- **Metas:** todas opcionais por sessão: distância, duração, faixa de ritmo, zona de FC e percepção de esforço. A IA usa as que fazem sentido. Descanso é uma sessão sem metas.
- **Musculação:** entra no plano só como feita ou não.
- **Confirmação:** a IA mostra o plano e só chama `salvar_plano` depois que o usuário confirma.
- **Cálculo na hora:** o casamento não é gravado; é refeito a cada consulta, para incluir treinos que chegam depois.

## Consequências
- Treinos que chegam atrasados (celular ou novo export) entram na aderência sozinhos.
- Histórico de planos preservado; planos são dados que nenhum export recupera.
- Casar no dia vizinho pode trocar sessões em semanas muito cheias; revisar se acontecer.
