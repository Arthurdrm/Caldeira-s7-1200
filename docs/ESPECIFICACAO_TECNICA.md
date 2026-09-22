# Especificação Técnica do Sistema de Controle da Caldeira

Este documento formaliza as regras de processo, automação e segurança implementadas no CLP **Siemens SIMATIC S7-1200** para o controle e intertravamento da Caldeira Industrial, com base nas especificações de engenharia de automação.

---

## 1. Mapeamento de Hardware e I/O (Slide 5)

### Entradas Digitais (DI)
| Tag | Endereço | Tipo de Contato | Função de Campo |
| :--- | :--- | :--- | :--- |
| `Botao_liga` | `%I0.0` | NA (Normalmente Aberto) | Botão de impulso de partida do sistema |
| `Botao_desliga` | `%I0.1` | NF (Normalmente Fechado) | Botão de impulso para parada natural |
| `Botao_reset` | `%I0.2` | NF (Normalmente Fechado) | Botão de impulso para reconhecimento de falha |
| `Botao_emergencia` | `%I0.3` | NF (Retenção Mecânica) | Botão cogumelo de parada crítica imediata |

### Entradas Analógicas (AI)
| Tag | Endereço | Faixa de Sinal | Faixa de Engenharia | Função de Processo |
| :--- | :--- | :--- | :--- | :--- |
| `AI_Nivel` | `%IW64` | 4 a 20 mA (0 a 27648) | 0.0 a 100.0 % | Transmissor de nível do reservatório da caldeira |
| `AI_Pressao` | `%IW66` | 4 a 20 mA (0 a 27648) | 0.0 a 100.0 % | Transmissor de pressão interna do vaso/tubulão |
| `AI_Temperatura` | `%IW68` | 4 a 20 mA (0 a 27648) | 0.0 a 100.0 % | Termoelemento interno do trocador de calor |

### Saídas Digitais (DQ)
| Tag | Endereço | Descrição do Atuador |
| :--- | :--- | :--- |
| `Valvula_Agua` | `%Q0.0` | Válvula Solenoide/Esfera ON/OFF de alimentação de água |
| `Valvula_Vapor` | `%Q0.1` | Válvula de Controle Principal de Vapor para a fábrica |
| `Valvula_Alivio` | `%Q0.2` | Válvula de Alívio Rápido de Emergência (Blowdown) |
| `Queimador_1` | `%Q0.3` | Contator/Comando Queimador 1 |
| `Queimador_2` | `%Q0.4` | Contator/Comando Queimador 2 |
| `Queimador_3` | `%Q0.5` | Contator/Comando Queimador 3 |
| `Queimador_4` | `%Q0.6` | Contator/Comando Queimador 4 |
| `Queimador_5` | `%Q0.7` | Contator/Comando Queimador 5 |
| `Queimador_6` | `%Q1.0` | Contator/Comando Queimador 6 |
| `Lamp_Sistema_Lig` | `%Q1.1` | Lâmpada Piloto Verde - Sistema em Operação |
| `Lamp_Alarme_Emerg`| `%Q1.2` | Lâmpada Piloto Vermelha - Alarme de Emergência Ativo |

---

## 2. Descrição das Etapas de Processo

### Etapa 1: Controle de Abastecimento de Água (Slide 1)
- O sistema assume imediatamente o monitoramento contínuo do nível do reservatório ao detectar o pulso de partida no botão Liga (`%I0.0`).
- **Intertravamento de Nível Mínimo:** Se o nível for inferior a **50.0%**, a válvula ON/OFF de água (`%Q0.0`) abre automaticamente para abastecimento.
- **Histerese de Parada:** Ao atingir o patamar seguro superior (**75.0%**), a válvula é fechada, evitando chaveamento cíclico excessivo da solenoide.
- **Proteção Contra Choque Térmico (Slide 4):** Mesmo com o sistema desligado intencionalmente, o monitoramento e reposição de água continuam ativos para garantir que os tubos e o corpo de aço da fornalha nunca sequem sob alta temperatura residual.

---

### Etapa 2: Estagiamento e Otimização Térmica dos Queimadores (Slide 2)
- **Permissão de Ignição:** Os queimadores somente recebem permissão para operar se:
  1. `Sistema_Ligado = TRUE`
  2. `Emergencia_Ativa = FALSE`
  3. `Nivel_Agua >= 50.0%` (Intertravamento mandatório contra queima sem água)
- **Rampa de Modulação Térmica:**
  | Faixa de Temperatura (%) | Quantidade de Queimadores Ativos | Queimadores Ligados |
  | :--- | :--- | :--- |
  | $\ge 80.0\%$ | 2 Queimadores | Q1, Q2 |
  | $60.0\% \le T < 80.0\%$ | 3 Queimadores | Q1, Q2, Q3 |
  | $40.0\% \le T < 60.0\%$ | 4 Queimadores | Q1, Q2, Q3, Q4 |
  | $20.0\% \le T < 40.0\%$ | 5 Queimadores | Q1, Q2, Q3, Q4, Q5 |
  | $< 20.0\%$ (Frio / Partida) | 6 Queimadores | Q1, Q2, Q3, Q4, Q5, Q6 |

---

### Etapa 3: Linha de Vapor e Intertravamento Industrial (Slide 3)
- **Condição de Abertura:** A válvula principal de vapor (`%Q0.1`) só abre se ambos os seguintes parâmetros de segurança forem simultaneamente satisfeitos:
  - $\text{Temperatura} > 80.0\%$
  - $\text{Pressão Interna} > 70.0\%$
- **Intertravamento:** Caso a temperatura caia para $\le 80.0\%$ OU a pressão caia para $\le 70.0\%$, a válvula fecha imediatamente, prevenindo passagem de vapor úmido (arraste de condensado) para a linha de produção fabril e preservando o rendimento.

---

### Etapas 4 e 5: Filosofia de Segurança e Parada (Slide 4)

#### Parada Normal de Desligamento:
- Acionada pelo botão `Botao_desliga` (`%I0.1`).
- Desliga instantaneamente todos os queimadores.
- A linha de vapor é encerrada acompanhando a rampa natural de resfriamento.
- O abastecimento e nível de água permanecem monitorados e atuantes.

#### Parada Crítica de Emergência:
- Acionada ao abrir a trava mecânica do botão cogumelo `Botao_emergencia` (`%I0.3`).
- **Ações Imediatas:**
  - Corta imediatamente o selo do sistema (`Sistema_Ligado := FALSE`).
  - Desliga todos os 6 queimadores em 1 ciclo de scan do CLP.
  - Corta a alimentação da válvula de vapor principal (`%Q0.1 := FALSE`).
  - Força a abertura instantânea da válvula de alívio (`%Q0.2 := TRUE`).
  - Acende sinalizador de emergência (`%Q1.2 := TRUE`).
- **Sequência Obrigatória de Normalização (Dois Passos):**
  1. Destravar fisicamente o botão cogumelo de emergência (`%I0.3` retorna ao estado elétrico fechado = 24V).
  2. Aplicar um pulso no botão `Botao_reset` (`%I0.2`).
  3. Somente após essa confirmação o alarme é liberado e a válvula de alívio se fecha.
