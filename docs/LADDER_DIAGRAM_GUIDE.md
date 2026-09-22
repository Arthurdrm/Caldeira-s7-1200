# Guia de Implementação em Linguagem Ladder (LAD) - S7-1200

Para os engenheiros e técnicos que desejam visualizar, editar ou criar o programa diretamente na linguagem de contatos **LAD (Ladder)** no TIA Portal, este documento detalha o arranjo exato de cada uma das redes (**Networks**) no bloco `Main [OB1]` ou em um bloco de funções `FB`.

---

## Tabela de Correspondência de I/Os e Variáveis

| Identificador | Endereço CLP | Tipo | Descrição Elétrica |
| :--- | :--- | :--- | :--- |
| `Botao_liga` | `%I0.0` | BOOL | Contato NA (Normalmente Aberto) |
| `Botao_desliga` | `%I0.1` | BOOL | Contato NF (Normalmente Fechado - 24V em repouso) |
| `Botao_reset` | `%I0.2` | BOOL | Contato NF (Normalmente Fechado - 24V em repouso) |
| `Botao_emergencia` | `%I0.3` | BOOL | Contato NF com Retenção mecânica |
| `AI_Nivel` | `%IW64` | INT | Entrada Analógica 4-20mA (0..27648) |
| `AI_Pressao` | `%IW66` | INT | Entrada Analógica 4-20mA (0..27648) |
| `AI_Temperatura` | `%IW68` | INT | Entrada Analógica 4-20mA (0..27648) |
| `Valvula_Agua` | `%Q0.0` | BOOL | Bobina Válvula de Abastecimento |
| `Valvula_Vapor` | `%Q0.1` | BOOL | Bobina Válvula Principal de Vapor |
| `Valvula_Alivio` | `%Q0.2` | BOOL | Bobina Válvula de Alívio Emergência |
| `Queimador_1`..`6` | `%Q0.3`..`%Q1.0` | BOOL | Bobinas de Acionamento dos Queimadores |
| `Lamp_Sistema_Lig` | `%Q1.1` | BOOL | Bobina Piloto Sistema Ligado |
| `Lamp_Alarme_Emerg`| `%Q1.2` | BOOL | Bobina Piloto Alarme Emergência |

---

## Rede 1: Escalonamento das Entradas Analógicas (4-20mA)

Utiliza os blocos nativos da Siemens **NORM_X** e **SCALE_X** para converter a faixa bruta de 0..27648 em percentual de engenharia 0.0..100.0%.

```
[ NORM_X ]
   MIN: 0
   VALUE: %IW64 ("AI_Nivel")
   MAX: 27648
   OUT: #temp_norm_nivel (Real)
        |
        +---> [ SCALE_X ]
                 MIN: 0.0
                 VALUE: #temp_norm_nivel
                 MAX: 100.0
                 OUT: "DB_Caldeira".Status.Nivel_Perc

[ NORM_X ]
   MIN: 0
   VALUE: %IW66 ("AI_Pressao")
   MAX: 27648
   OUT: #temp_norm_pressao (Real)
        |
        +---> [ SCALE_X ]
                 MIN: 0.0
                 VALUE: #temp_norm_pressao
                 MAX: 100.0
                 OUT: "DB_Caldeira".Status.Pressao_Perc

[ NORM_X ]
   MIN: 0
   VALUE: %IW68 ("AI_Temperatura")
   MAX: 27648
   OUT: #temp_norm_temp (Real)
        |
        +---> [ SCALE_X ]
                 MIN: 0.0
                 VALUE: #temp_norm_temp
                 MAX: 100.0
                 OUT: "DB_Caldeira".Status.Temp_Perc
```

---

## Rede 2: Circuito de Segurança e Emergência (Slide 4)

- Se a trava de emergência abrir (`%I0.3` = FALSE / contato NF aberto), seta o latch de emergência.
- Para resetar: Botão de emergência físico destravado (`%I0.3` = TRUE) **E** pulso no botão Reset (`%I0.2`).

```
Ramo 1: Disparo da Emergência
--| / |---------------------------------------------------( S )--
  "Botao_emergencia"                                     "DB_Caldeira".Status.Emergencia_Ativa

Ramo 2: Reset da Emergência
--|   |-----------| P_TRIG |------------------------------( R )--
  "Botao_emergencia"   "Botao_reset"                     "DB_Caldeira".Status.Emergencia_Ativa
```

---

## Rede 3: Liga / Desliga do Sistema (Slide 1 e 4)

Comando de partida pelo botão Liga (`%I0.0`), retenção (selo de operação), desliga intencional pelo botão Desliga (`%I0.1`), e desarme instantâneo se a emergência for acionada.

```
--+--|   |--+--|   |----------| / |-----------------------(   )--
  |  "Botao_liga"  |  "Botao_desliga"   "DB_Caldeira".Status.      "DB_Caldeira".Status.
  +--|   |--+                           Emergencia_Ativa           Sistema_Ligado
   "DB_Caldeira".
   Status.Sistema_Ligado
```

---

## Rede 4: Etapa 1 - Controle de Abastecimento de Água (Slide 1 e 4)

- Se `Nivel_Perc < 50.0%`: Seta acionamento da válvula de água (`%Q0.0`).
- Se `Nivel_Perc >= 75.0%`: Reseta acionamento da válvula de água.
- **Nota Crucial:** Não depende do botão Liga estar acionado, mantendo monitoramento e reposição mesmo com o sistema desligado para evitar choque térmico.

```
Ramo 1: Ligar válvula se Nível < 50%
--[ CMP < ]-----------------------------------------------( S )--
  "DB_Caldeira".Status.Nivel_Perc                        %Q0.0 ("Valvula_Agua")
  50.0

Ramo 2: Desligar válvula se Nível >= 75%
--[ CMP >= ]----------------------------------------------( R )--
  "DB_Caldeira".Status.Nivel_Perc                        %Q0.0 ("Valvula_Agua")
  75.0
```

---

## Rede 5: Condição Geral de Permissão dos Queimadores

Garante que os queimadores só podem ser ativados se o sistema estiver ligado, sem emergência e com nível de água seguro ($\ge 50\%$).

```
--|   |----------| / |------------------[ CMP >= ]--------(   )--
  "DB_Caldeira".   "DB_Caldeira".Status.  "DB_Caldeira".Status.    #Permissao_Queimadores
  Status.          Emergencia_Ativa       Nivel_Perc
  Sistema_Ligado                          50.0
```

---

## Rede 6: Etapa 2 - Otimização Térmica dos Queimadores (Slide 2)

### Queimadores 1 e 2 (Ativos em qualquer faixa onde haja permissão):
```
--|   |---------------------------------------------------(   )-- %Q0.3 ("Queimador_1")
  #Permissao_Queimadores

--|   |---------------------------------------------------(   )-- %Q0.4 ("Queimador_2")
  #Permissao_Queimadores
```

### Queimador 3 (Ativo se Temperatura < 80%):
```
--|   |----------[ CMP < ]--------------------------------(   )-- %Q0.5 ("Queimador_3")
  #Permissao_       "DB_Caldeira".Status.Temp_Perc
  Queimadores       80.0
```

### Queimador 4 (Ativo se Temperatura < 60%):
```
--|   |----------[ CMP < ]--------------------------------(   )-- %Q0.6 ("Queimador_4")
  #Permissao_       "DB_Caldeira".Status.Temp_Perc
  Queimadores       60.0
```

### Queimador 5 (Ativo se Temperatura < 40%):
```
--|   |----------[ CMP < ]--------------------------------(   )-- %Q0.7 ("Queimador_5")
  #Permissao_       "DB_Caldeira".Status.Temp_Perc
  Queimadores       40.0
```

### Queimador 6 (Ativo se Temperatura < 20% - Partida a frio):
```
--|   |----------[ CMP < ]--------------------------------(   )-- %Q1.0 ("Queimador_6")
  #Permissao_       "DB_Caldeira".Status.Temp_Perc
  Queimadores       20.0
```

---

## Rede 7: Etapa 3 - Linha de Vapor e Intertravamento (Slide 3)

A válvula de vapor só abre se:
1. `Sistema_Ligado` = TRUE
2. `Emergencia_Ativa` = FALSE
3. `Temperatura` > 80.0%
4. `Pressao` > 70.0%

Se qualquer dessas condições cessar, a bobina `%Q0.1` desliga imediatamente.

```
--|   |----------| / |----------[ CMP > ]--------[ CMP > ]--------(   )--
  "DB_Caldeira".   "DB_Caldeira". "DB_Caldeira".   "DB_Caldeira".    %Q0.1 ("Valvula_Vapor")
  Status.          Status.        Status.          Status.
  Sistema_Ligado   Emergencia_    Temp_Perc        Pressao_Perc
                   Ativa          80.0             70.0
```

---

## Rede 8: Válvula de Alívio de Emergência (Slide 4)

Aciona instantaneamente em parada crítica de emergência ou por proteção de sobrepressão ($\ge 95\%$).

```
--+--|   |------------------------------------------------+---(   )--
  |  "DB_Caldeira".Status.Emergencia_Ativa                |    %Q0.2 ("Valvula_Alivio")
  +--[ CMP >= ]-------------------------------------------+
     "DB_Caldeira".Status.Pressao_Perc
     95.0
```

---

## Rede 9: Sinalizações do Painel

```
--|   |----------| / |------------------------------------(   )--
  "DB_Caldeira".   "DB_Caldeira".Status.                         %Q1.1 ("Lamp_Sistema_Lig")
  Status.          Emergencia_Ativa
  Sistema_Ligado

--|   |---------------------------------------------------(   )--
  "DB_Caldeira".Status.Emergencia_Ativa                         %Q1.2 ("Lamp_Alarme_Emerg")
```
