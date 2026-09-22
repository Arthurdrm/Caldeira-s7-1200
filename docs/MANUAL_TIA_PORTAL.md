# Manual de Instalação e Execução no Siemens SIMATIC S7-1200 (TIA Portal)

Este manual descreve o passo a passo completo para carregar, compilar, simular e descarregar o programa de **Controle e Intertravamento de Caldeira** em qualquer CLP Siemens S7-1200 utilizando o **TIA Portal** (compatível com versões V13, V14, V15, V16, V17, V18 e V19).

---

## 1. Pré-Requisitos

1. **Software:**
   - Siemens TIA Portal (STEP 7 Basic ou Professional) V13 ou superior.
   - S7-PLCSIM (opcional, para teste em bancada virtual sem hardware físico).
2. **Hardware:**
   - Qualquer CPU S7-1200 (ex: CPU 1211C, 1212C, 1214C, 1215C).
   - Cabo de rede Ethernet padrão RJ45 conectado à porta PROFINET do CLP.

---

## 2. Passo a Passo no TIA Portal

### Passo 2.1: Criar um Novo Projeto
1. Abra o **TIA Portal**.
2. Clique em **"Create new project"**.
3. Defina o nome como `Controle_Caldeira_S7_1200` e clique em **Create**.
4. Mude para a visualização de projeto clicando em **"Project view"** no canto inferior esquerdo.

---

### Passo 2.2: Adicionar a CPU S7-1200
1. Na árvore do projeto à esquerda, dê um duplo clique em **"Add new device"**.
2. Selecione **Controllers** > **SIMATIC S7-1200** > **CPU**.
3. Escolha o modelo exato da sua CPU (exemplo: **CPU 1214C DC/DC/DC** - `6ES7 214-1AG40-0XB0` ou equivalente).
4. Verifique a versão do firmware e clique em **OK**.

---

### Passo 2.3: Importar a Tabela de Tags (Variáveis do CLP)
1. Na árvore da CPU, expanda a pasta **"PLC tags"**.
2. Abra a **"Default tag table"** (ou clique com o botão direito e selecione *Import*).
3. **Opção A (Importação Direta):**
   - Clique no ícone de **Import** no topo da tabela de tags.
   - Selecione o arquivo `tags/PLC_Tags_Caldeira.csv` ou `tags/PLC_Tags_Caldeira.xml` deste repositório.
   - Clique em **Import**.
4. **Opção B (Copiar e Colar):**
   - Abra o arquivo `tags/PLC_Tags_Caldeira.csv` no Excel ou bloco de notas.
   - Copie as linhas e cole diretamente na grade de tags do TIA Portal.

---

### Passo 2.4: Importar o Código Fonte SCL
1. Na árvore do projeto, localize a pasta **"External source files"** dentro da CPU.
2. Dê um duplo clique em **"Add new external file"**.
3. Navegue até a pasta do repositório `src/` e selecione:
   - `Caldeira_Controle_S7_1200.scl`
4. Clique em **Open**. O arquivo aparecerá na lista de fontes externas.
5. Clique com o **botão direito** sobre o arquivo `Caldeira_Controle_S7_1200.scl` importado.
6. Selecione a opção **"Generate blocks from source"**.
7. O TIA Portal irá compilar o código fonte e gerar automaticamente na pasta **"Program blocks"**:
   - `type_Parametros_Caldeira` (em PLC data types)
   - `type_Status_Caldeira` (em PLC data types)
   - `FB_Controle_Caldeira` [FB1]
   - `DB_Caldeira` [DB1]
   - `Main` [OB1]

> **Nota:** Se o seu projeto já possuir um bloco `Main [OB1]` vazio criado por padrão, o TIA Portal perguntará se deseja substituí-lo. Clique em **Yes to all**.

---

### Passo 2.5: Compilar o Projeto
1. Clique com o botão direito no nome da CPU ou na pasta **"Program blocks"**.
2. Selecione **Compile** > **Software (rebuild all)**.
3. Observe a janela de informações inferior (*Info > Compile*). O resultado deve indicar:
   `Compiling finished (errors: 0; warnings: 0)`.

---

## 3. Teste e Simulação com S7-PLCSIM

Caso não esteja conectado a uma caldeira real, você pode simular 100% da lógica no **S7-PLCSIM**:

1. No menu superior do TIA Portal, clique no botão **"Start simulation"** (ícone de computador com tela azul).
2. O S7-PLCSIM será iniciado e a CPU virtual entrará em modo `RUN`.
3. Na janela de download que abrir, clique em **Load**.
4. Crie uma **SIM table** no PLCSIM ou uma **Watch table** (Tabela de Observação) no TIA Portal com as variáveis:
   - `%I0.0` (`Botao_liga`)
   - `%I0.1` (`Botao_desliga`)
   - `%I0.2` (`Botao_reset`)
   - `%I0.3` (`Botao_emergencia`)
   - `%IW64` (`AI_Nivel`)
   - `%IW66` (`AI_Pressao`)
   - `%IW68` (`AI_Temperatura`)
   - `%Q0.0` (`Valvula_Agua`)
   - `%Q0.1` (`Valvula_Vapor`)
   - `%Q0.2` (`Valvula_Alivio`)
   - `%Q0.3` até `%Q1.0` (`Queimador_1` a `Queimador_6`)
5. **Roteiro de Teste no Simulador:**
   - **Condição Inicial:** Force `I0.3 = TRUE` (Botão de Emergência destravado, contato NF fechado) e `I0.1 = TRUE` (Botão Desliga em repouso).
   - **Reset de Inicialização:** Aplique um pulso rápido em `I0.2 = FALSE -> TRUE`.
   - **Partida:** Aplique um pulso em `I0.0 = TRUE` (Botão Liga) e depois volte para `FALSE`. O sistema passa para `Sistema_Ligado = TRUE`.
   - **Abastecimento de Água:** Com `IW64 = 5529` (aprox. 20%), a saída `%Q0.0` (`Valvula_Agua`) ligará imediatamente.
   - **Elevação de Nível:** Suba `IW64 = 22118` (80%), a `%Q0.0` desliga (atingiu histerese de 75%).
   - **Disparo dos Queimadores:**
     - Com `IW68 = 0` (0% Temp): Todos os 6 queimadores (`%Q0.3`..`%Q1.0`) acionam.
     - Suba `IW68 = 6912` (25% Temp): 5 queimadores acionados.
     - Suba `IW68 = 12441` (45% Temp): 4 queimadores acionados.
     - Suba `IW68 = 17971` (65% Temp): 3 queimadores acionados.
     - Suba `IW68 = 23500` (85% Temp): 2 queimadores acionados.
   - **Abertura de Vapor:**
     - Com Temp em 85% (`IW68 = 23500`) e Pressão em 75% (`IW66 = 20736`), a `%Q0.1` (`Valvula_Vapor`) abre!
     - Se baixar a pressão para 60% (`IW66 = 16588`), a `%Q0.1` fecha instantaneamente.
   - **Teste de Emergência:**
     - Force `I0.3 = FALSE` (botão de emergência acionado).
     - Imediatamente todos os queimadores desligam, válvula de vapor fecha e `%Q0.2` (`Valvula_Alivio`) abre.

---

## 4. Download para o CLP Real

1. Conecte o cabo de rede Ethernet entre o computador e a CPU S7-1200.
2. No menu do TIA Portal, selecione a CPU e clique em **"Download to device"** (ícone de seta para baixo).
3. Na janela de interface:
   - **Type of the PG/PC interface:** `PN/IE`
   - **PG/PC interface:** Sua placa de rede Ethernet (ex: Intel / Realtek).
   - **Connection to interface/subnet:** `Direct at slot 1 X1`.
4. Clique em **Start search**. Quando o CLP aparecer com seu endereço IP (padrão de fábrica `192.168.0.1`), selecione-o e clique em **Load**.
5. Na tela de pré-visualização de carga, confirme a ação e selecione **Start module after download** caso solicitado.
6. A CPU entrará no modo `RUN` (LED verde aceso fixo). O sistema está pronto e operando!
