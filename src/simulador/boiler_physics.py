"""Modelo Físico Termodinâmico de Planta Industrial para Caldeira a Vapor.
Simula nível de água, pressão interna e temperatura com base nas ações dos atuadores.
"""

class BoilerPhysics:
    def __init__(self):
        # Estados físicos reais (0.0 a 100.0%)
        self.water_level: float = 45.0      # Começa em 45% (abaixo de 50% para ver ligando a água)
        self.temperature: float = 24.0      # Temperatura ambiente inicial (24%)
        self.pressure: float = 8.0          # Pressão residual inicial (8%)

        # Flag para permitir controle físico automático ou injeção manual de falha
        self.auto_mode: bool = True

    def update(self, dt: float, valvula_agua: bool, valvula_vapor: bool, valvula_alivio: bool, qtd_queimadores: int):
        """Avança a física do processo em dt segundos."""
        if not self.auto_mode:
            return

        # 1. BALANÇO DE MASSA DE ÁGUA
        if valvula_agua:
            # Abastecimento via bomba de alimentação (+6.5%/s)
            self.water_level += 6.5 * dt
            # Água fria diminui ligeiramente a temperatura média da caldeira
            self.temperature = max(20.0, self.temperature - 1.2 * dt)

        # Consumo de água por evaporação/ebulição
        if self.temperature > 50.0 and qtd_queimadores > 0:
            taxa_evaporacao = (self.temperature / 100.0) * (qtd_queimadores / 6.0) * 1.6 * dt
            self.water_level -= taxa_evaporacao

        self.water_level = max(0.0, min(100.0, self.water_level))

        # 2. DINÂMICA TÉRMICA (QUEIMADORES)
        if qtd_queimadores > 0 and self.water_level > 5.0:
            # Taxa de aquecimento proporcional aos queimadores acesos
            taxa_calor = qtd_queimadores * 2.8 * dt
            self.temperature += taxa_calor
        else:
            # Perda de calor natural para o ambiente
            self.temperature = max(22.0, self.temperature - 0.7 * dt)

        self.temperature = max(0.0, min(110.0, self.temperature))

        # 3. GERAÇÃO DE PRESSÃO DE VAPOR
        if self.temperature > 65.0 and self.water_level > 5.0:
            # Geração de vapor superaquecido
            fator_temp = (self.temperature - 65.0) / 35.0
            self.pressure += fator_temp * 4.5 * dt
        else:
            # Condensação lenta
            self.pressure = max(0.0, self.pressure - 0.6 * dt)

        # 4. CONSUMO DE VAPOR PELO PROCESSO (VÁLVULA DE VAPOR Q0.1)
        if valvula_vapor:
            # Quando a válvula de processo abre, o vapor vai para os consumidores,
            # drenando pressão e tendendo a estabilizar entre 70% e 75%
            if self.pressure > 72.0:
                self.pressure -= 3.8 * dt

        # 5. DESPRESSURIZAÇÃO DE EMERGÊNCIA (VÁLVULA DE ALÍVIO Q0.2)
        if valvula_alivio:
            # Dreno violento de emergência para a atmosfera
            self.pressure = max(0.0, self.pressure - 16.0 * dt)
            self.temperature = max(35.0, self.temperature - 3.5 * dt)

        self.pressure = max(0.0, min(100.0, self.pressure))

    def get_raw_signals(self) -> tuple[int, int, int]:
        """Converte as grandezas físicas (0..100%) em palavras analógicas S7 (0..27648)."""
        raw_nivel = int((self.water_level / 100.0) * 27648)
        raw_pressao = int((self.pressure / 100.0) * 27648)
        raw_temp = int((self.temperature / 100.0) * 27648)

        raw_nivel = max(0, min(27648, raw_nivel))
        raw_pressao = max(0, min(27648, raw_pressao))
        raw_temp = max(0, min(27648, raw_temp))

        return raw_nivel, raw_pressao, raw_temp
