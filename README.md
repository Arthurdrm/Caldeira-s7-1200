# Sistema de Controle e Intertravamento de Caldeira Industrial (Siemens S7-1200)

[![PLC](https://img.shields.io/badge/PLC-Siemens%20SIMATIC%20S7--1200-00646E.svg)](https://www.siemens.com)
[![TIA Portal](https://img.shields.io/badge/TIA%20Portal-V13%20a%20V19-EB780A.svg)](https://support.industry.siemens.com)
[![Language](https://img.shields.io/badge/Language-SCL%20%7C%20LAD-007ACC.svg)](https://en.wikipedia.org/wiki/Structured_text)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Projeto completo de automação, modulação térmica e segurança crítica para Caldeira Industrial em CLP **Siemens SIMATIC S7-1200**, desenvolvido segundo as normas IEC 61131-3 e especificações industriais rigorosas.

---

## 📂 Estrutura do Repositório

```text
caldeira-s7-1200/
├── src/
│   ├── Caldeira_Controle_S7_1200.scl   # Arquivo SCL unificado (Pronto para importar no TIA Portal)
│   ├── FB_Controle_Caldeira.scl         # Bloco de Função (Lógica principal modular)
│   ├── DB_Caldeira.scl                  # Bloco de Dados de Instância e parâmetros
│   └── OB1_Main.scl                     # Ciclo principal OB1 com mapeamento de hardware
├── tags/
│   ├── PLC_Tags_Caldeira.csv            # Tabela de Tags para importação no TIA Portal (CSV)
│   └── PLC_Tags_Caldeira.xml            # Tabela de Tags formato nativo Siemens XML
├── docs/
│   ├── MANUAL_TIA_PORTAL.md             # Passo a passo completo para TIA Portal e S7-PLCSIM
│   ├── LADDER_DIAGRAM_GUIDE.md          # Guia de implementação e redes em Linguagem Ladder (LAD)
│   └── ESPECIFICACAO_TECNICA.md         # Memorial descritivo detalhado das 5 Etapas do processo
└── README.md                            # Apresentação do projeto
```

---

## ⚡ Guia Rápido de Instalação (TIA Portal)

1. No TIA Portal, crie um projeto com sua CPU S7-1200 (ex: CPU 1214C DC/DC/DC).
2. Em **PLC tags**, importe o arquivo [`tags/PLC_Tags_Caldeira.csv`](tags/PLC_Tags_Caldeira.csv).
3. Na pasta **External source files**, adicione o arquivo [`src/Caldeira_Controle_S7_1200.scl`](src/Caldeira_Controle_S7_1200.scl).
4. Clique com o botão direito nele e selecione **"Generate blocks from source"**.
5. Compile o projeto e faça o download para a CPU real ou para o simulador **S7-PLCSIM**!

Consulte o [Manual Detalhado do TIA Portal](docs/MANUAL_TIA_PORTAL.md) para o tutorial passo a passo.

---

## ⚙️ Mapeamento de Entradas e Saídas (I/O)

### Entradas Digitais e Analógicas
| Endereço | Tag | Descrição Elétrica | Função |
| :--- | :--- | :--- | :--- |
| `%I0.0` | `Botao_liga` | Digital NA | Partida do sistema |
| `%I0.1` | `Botao_desliga` | Digital NF | Parada natural com resfriamento |
| `%I0.2` | `Botao_reset` | Digital NF | Pulso de reconhecimento de falhas |
| `%I0.3` | `Botao_emergencia` | Digital NF (Retenção) | Parada imediata e alívio de pressão |
| `%IW64` | `AI_Nivel` | Analógica 4-20mA (0..27648) | Leitura de nível do reservatório da caldeira |
| `%IW66` | `AI_Pressao` | Analógica 4-20mA (0..27648) | Leitura de pressão interna do cilindro |
| `%IW68` | `AI_Temperatura` | Analógica 4-20mA (0..27648) | Leitura termométrica do trocador de calor |

### Saídas Digitais
| Endereço | Tag | Descrição |
| :--- | :--- | :--- |
| `%Q0.0` | `Valvula_Agua` | Válvula ON/OFF de abastecimento de água contínuo |
| `%Q0.1` | `Valvula_Vapor` | Válvula principal de fornecimento de vapor para a fábrica |
| `%Q0.2` | `Valvula_Alivio` | Válvula de alívio rápido de emergência e sobrepressão |
| `%Q0.3` a `%Q1.0` | `Queimador_1` a `Queimador_6` | Estágios de aquecimento dos 6 queimadores |
| `%Q1.1` | `Lamp_Sistema_Lig` | Lâmpada de indicação de sistema ligado |
| `%Q1.2` | `Lamp_Alarme_Emerg` | Lâmpada piloto de emergência ativa |

---

## 🎯 Lógica do Processo (As 5 Etapas)

### Etapa 1: Água (Abastecimento Contínuo)
- Monitoramento contínuo do nível no reservatório.
- Se $\text{Nível} < 50\% \rightarrow$ Válvula abre automaticamente (`%Q0.0 = TRUE`).
- Desliga ao alcançar o nível superior de segurança ($75\%$).
- O monitoramento e abastecimento permanecem ativos mesmo no desligamento do sistema para evitar choque térmico na estrutura de aço.

### Etapa 2: Queimadores (Otimização Térmica)
- Com nível $\ge 50\%$ e sistema em operação, os queimadores modulam conforme a temperatura:
  - $\ge 80\% \rightarrow$ **2 Queimadores** (`Q1`, `Q2`)
  - $60\% \le T < 80\% \rightarrow$ **3 Queimadores** (`Q1` a `Q3`)
  - $40\% \le T < 60\% \rightarrow$ **4 Queimadores** (`Q1` a `Q4`)
  - $20\% \le T < 40\% \rightarrow$ **5 Queimadores** (`Q1` a `Q5`)
  - $< 20\% \rightarrow$ **6 Queimadores** (`Q1` a `Q6`)

### Etapa 3: Linha de Vapor (Intertravamento de Segurança)
- Abertura liberada apenas quando:
  $$\text{Temperatura} > 80\% \quad \text{E} \quad \text{Pressão} > 70\%$$
- Se qualquer uma das variáveis cair abaixo do setpoint, a válvula fecha imediatamente para evitar envio de vapor fora de especificação.

### Etapa 4: Procedimento de Desligamento
- Acionado por `Botao_desliga` (`%I0.1`).
- Desliga imediatamente todos os queimadores.
- Válvula de vapor acompanha rampa de resfriamento.

### Etapa 5: Parada Crítica (Emergência)
- Acionado por trava cogumelo `Botao_emergencia` (`%I0.3`).
- Corta instantaneamente todos os atuadores e **força a abertura da válvula de alívio** (`%Q0.2`).
- **Procedimento de Normalização:**
  1. Destravar fisicamente o botão cogumelo.
  2. Aplicar um pulso no botão `Botao_reset` (`%I0.2`).

---

## 📖 Documentação Adicional
- [Manual Passo a Passo do TIA Portal](docs/MANUAL_TIA_PORTAL.md)
- [Diagrama e Redes em Linguagem Ladder (LAD)](docs/LADDER_DIAGRAM_GUIDE.md)
- [Especificação Técnica Completa](docs/ESPECIFICACAO_TECNICA.md)
