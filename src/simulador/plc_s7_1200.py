"""Emulador do Ciclo de Varredura (Scan Cycle) do CLP Siemens S7-1200.
Implementa a lógica fiel do bloco FB_Controle_Caldeira.scl.
"""

from dataclasses import dataclass
from typing import List, Tuple

class PLCS71200Caldeira:
    def __init__(self):
        # 1. ENTRADAS DIGITAIS (%I0.0 a %I0.3)
        self.botao_liga: bool = False        # %I0.0 (NA) - Pulso de partida
        self.botao_desliga: bool = True      # %I0.1 (NF) - Parada normal (True em repouso)
        self.botao_reset: bool = True        # %I0.2 (NF) - Reconhecimento de falha (True em repouso)
        self.botao_emergencia: bool = True   # %I0.3 (NF com trava) - Parada imediata (True quando seguro)

        # 2. ENTRADAS ANALÓGICAS BRUTAS 0..27648 (%IW64, %IW66, %IW68)
        self.ai_nivel_raw: int = 0           # %IW64
        self.ai_pressao_raw: int = 0         # %IW66
        self.ai_temp_raw: int = 0            # %IW68

        # 3. PARÂMETROS DE PROCESSO (Ajustáveis no DB_Caldeira)
        self.nivel_liga_agua: float = 50.0       # % Nível mínimo para ligar válvula de água
        self.nivel_desliga_agua: float = 75.0    # % Nível superior para fechar válvula
        self.temp_min_vapor: float = 80.0        # % Temp mínima para abrir linha de vapor
        self.pressao_min_vapor: float = 70.0     # % Pressão mínima para liberar vapor
        self.pressao_max_seguranca: float = 95.0 # % Pressão de sobrepressão crítica

        # 4. SAÍDAS DIGITAIS (%Q0.0 a %Q1.2)
        self.valvula_agua: bool = False          # %Q0.0
        self.valvula_vapor: bool = False         # %Q0.1
        self.valvula_alivio: bool = False        # %Q0.2
        self.queimadores: List[bool] = [False] * 6 # %Q0.3 a %Q1.0
        self.lamp_em_operacao: bool = False      # %Q1.1
        self.lamp_emergencia: bool = False       # %Q1.2

        # 5. VARIÁVEIS DE PROCESSO ESCALONADAS (0 a 100%)
        self.nivel_perc: float = 0.0
        self.pressao_perc: float = 0.0
        self.temp_perc: float = 0.0
        self.sistema_ligado: bool = False
        self.emergencia_ativa: bool = False
        self.qtd_queimadores_ativos: int = 0

        # 6. MEMÓRIA INTERNA (STAT do S7)
        self.stat_sistema_ligado: bool = False
        self.stat_emergencia_latched: bool = False
        self.stat_valvula_agua: bool = False
        self.stat_liga_prev: bool = False
        self.stat_reset_prev: bool = True
        self.stat_desliga_prev: bool = True

    def scan_cycle(self) -> List[str]:
        """Executa 1 ciclo de scan do CLP Siemens idêntico ao OB1 / FB_Controle_Caldeira."""
        events: List[str] = []

        # 1. ESCALONAMENTO S7 (0..27648 -> 0..100%)
        r_nivel = (float(self.ai_nivel_raw) / 27648.0) * 100.0
        r_nivel = max(0.0, min(100.0, r_nivel))
        self.nivel_perc = r_nivel

        r_pressao = (float(self.ai_pressao_raw) / 27648.0) * 100.0
        r_pressao = max(0.0, min(100.0, r_pressao))
        self.pressao_perc = r_pressao

        r_temp = (float(self.ai_temp_raw) / 27648.0) * 100.0
        r_temp = max(0.0, min(100.0, r_temp))
        self.temp_perc = r_temp

        # 2. DETECÇÃO DE BORDAS
        pulso_liga = self.botao_liga and not self.stat_liga_prev
        self.stat_liga_prev = self.botao_liga

        # Botão NF: quando pressionado vai de 1 para 0 (borda de descida do contato elétrico)
        pulso_reset = (not self.botao_reset) and self.stat_reset_prev
        self.stat_reset_prev = self.botao_reset

        pulso_desliga = (not self.botao_desliga) and self.stat_desliga_prev
        self.stat_desliga_prev = self.botao_desliga

        # 3. ETAPAS 4 E 5: CIRCUITO DE SEGURANÇA E EMERGÊNCIA
        if not self.botao_emergencia:
            if not self.stat_emergencia_latched:
                events.append("🚨 [EMERGÊNCIA] Botão de Emergência I0.3 acionado! Travando sistema.")
            self.stat_emergencia_latched = True
            self.stat_sistema_ligado = False
        elif self.stat_emergencia_latched and self.botao_emergencia and pulso_reset:
            events.append("🟢 [RESET] Botão I0.2 acionado. Emergência desarmada com sucesso.")
            self.stat_emergencia_latched = False

        # 4. PARTIDA E PARADA NORMAL
        if self.stat_emergencia_latched:
            self.stat_sistema_ligado = False
        elif pulso_desliga or (not self.botao_desliga):
            if self.stat_sistema_ligado:
                events.append("⏹️ [PARADA] Botão Desliga I0.1 acionado. Sistema em repouso.")
            self.stat_sistema_ligado = False
        elif pulso_liga and (not self.stat_emergencia_latched) and self.botao_desliga:
            if not self.stat_sistema_ligado:
                events.append("▶️ [PARTIDA] Botão Liga I0.0 acionado. Caldeira em operação!")
            self.stat_sistema_ligado = True

        # 5. ETAPA 1: CONTROLE DE ABASTECIMENTO DE ÁGUA (HISTERESE)
        if r_nivel < self.nivel_liga_agua:
            if not self.stat_valvula_agua:
                events.append(f"💧 [ÁGUA] Nível baixo ({r_nivel:.1f}% < {self.nivel_liga_agua:.1f}%). Abrindo Válvula Q0.0.")
            self.stat_valvula_agua = True
        elif r_nivel >= self.nivel_desliga_agua:
            if self.stat_valvula_agua:
                events.append(f"💧 [ÁGUA] Nível nominal atingido ({r_nivel:.1f}% >= {self.nivel_desliga_agua:.1f}%). Fechando Válvula Q0.0.")
            self.stat_valvula_agua = False
        self.valvula_agua = self.stat_valvula_agua

        # 6. ETAPA 2: OTIMIZAÇÃO TÉRMICA DOS QUEIMADORES
        condicao_ok = self.stat_sistema_ligado and (not self.stat_emergencia_latched) and (r_nivel >= self.nivel_liga_agua)

        prev_qtd = self.qtd_queimadores_ativos
        if not condicao_ok:
            self.queimadores = [False] * 6
            self.qtd_queimadores_ativos = 0
            if prev_qtd > 0:
                motivo = "Intertravamento de nível baixo (<50%)" if r_nivel < self.nivel_liga_agua else "Sistema desligado/emergência"
                events.append(f"🔥 [QUEIMADORES] Todos desligados. Motivo: {motivo}.")
        else:
            if r_temp >= 80.0:
                self.queimadores = [True, True, False, False, False, False]
                self.qtd_queimadores_ativos = 2
            elif r_temp >= 60.0:
                self.queimadores = [True, True, True, False, False, False]
                self.qtd_queimadores_ativos = 3
            elif r_temp >= 40.0:
                self.queimadores = [True, True, True, True, False, False]
                self.qtd_queimadores_ativos = 4
            elif r_temp >= 20.0:
                self.queimadores = [True, True, True, True, True, False]
                self.qtd_queimadores_ativos = 5
            else:
                self.queimadores = [True, True, True, True, True, True]
                self.qtd_queimadores_ativos = 6

            if prev_qtd != self.qtd_queimadores_ativos:
                events.append(f"🔥 [QUEIMADORES] Modulação térmica ajustada: {self.qtd_queimadores_ativos} ativos (Temp: {r_temp:.1f}%).")

        # 7. ETAPA 3: LINHA DE VAPOR (LIBERAÇÃO E INTERTRAVAMENTO)
        cond_vapor = (self.stat_sistema_ligado 
                      and (not self.stat_emergencia_latched) 
                      and (r_temp > self.temp_min_vapor) 
                      and (r_pressao > self.pressao_min_vapor))
        if cond_vapor:
            if not self.valvula_vapor:
                events.append(f"💨 [VAPOR] Condições nominais atingidas (Temp>{self.temp_min_vapor}%, Pressão>{self.pressao_min_vapor}%). Válvula de Vapor Q0.1 ABERTA!")
            self.valvula_vapor = True
        else:
            if self.valvula_vapor:
                events.append("💨 [VAPOR] Condições abaixo do limite. Válvula de Vapor Q0.1 FECHADA.")
            self.valvula_vapor = False

        # 8. VALVULA DE ALÍVIO DE EMERGÊNCIA
        cond_alivio = self.stat_emergencia_latched or (r_pressao >= self.pressao_max_seguranca)
        if cond_alivio:
            if not self.valvula_alivio:
                motivo = "SOBREPRESSÃO CRÍTICA (>=95%)" if r_pressao >= self.pressao_max_seguranca else "PARADA DE EMERGÊNCIA"
                events.append(f"⚠️ [ALÍVIO] Válvula de Alívio Q0.2 ABERTA! Motivo: {motivo}.")
            self.valvula_alivio = True
        else:
            if self.valvula_alivio:
                events.append("⚠️ [ALÍVIO] Pressão normalizada. Válvula de Alívio Q0.2 Fechada.")
            self.valvula_alivio = False

        # 9. SINALIZAÇÕES
        self.sistema_ligado = self.stat_sistema_ligado
        self.emergencia_ativa = self.stat_emergencia_latched
        self.lamp_em_operacao = self.stat_sistema_ligado and (not self.stat_emergencia_latched)
        self.lamp_emergencia = self.stat_emergencia_latched

        return events
