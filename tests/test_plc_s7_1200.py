"""Testes Automatizados para o Sistema de Controle de Caldeira Siemens S7-1200.

Testa a lógica fiel do bloco FB_Controle_Caldeira.scl, entradas analógicas S7,
botoeira industrial (NA/NF), intertravamentos de segurança e dinâmica termodinâmica.
"""

import sys
import os

# Garante importação do src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.simulador.boiler_physics import BoilerPhysics
from src.simulador.plc_s7_1200 import PLCS71200Caldeira


class TestPLCS71200:
    """Suíte de testes de automação e controle do CLP S7-1200."""

    def test_analog_scaling_limits_and_clamping(self):
        """Testa conversão analógica padrão Siemens 0..27648 -> 0..100% com clamping."""
        plc = PLCS71200Caldeira()

        # Faixa nominal
        plc.ai_nivel_raw = 0
        plc.ai_pressao_raw = 13824  # 50%
        plc.ai_temp_raw = 27648    # 100%
        plc.scan_cycle()

        assert plc.nivel_perc == 0.0
        assert abs(plc.pressao_perc - 50.0) < 0.1
        assert plc.temp_perc == 100.0

        # Subfaixa e sobrefaixa (clamping de segurança)
        plc.ai_nivel_raw = -500
        plc.ai_pressao_raw = 35000
        plc.scan_cycle()

        assert plc.nivel_perc == 0.0
        assert plc.pressao_perc == 100.0

    def test_start_and_stop_pushbuttons(self):
        """Testa botoeira: Liga %I0.0 (NA) e Desliga %I0.1 (NF - pulso 1 -> 0)."""
        plc = PLCS71200Caldeira()
        assert not plc.sistema_ligado

        # Pulso de partida no botão Liga (I0.0)
        plc.botao_liga = True
        events = plc.scan_cycle()
        assert plc.sistema_ligado is True
        assert plc.lamp_em_operacao is True
        assert any("PARTIDA" in e for e in events)

        # Manter botão pressionado não gera novo pulso
        events = plc.scan_cycle()
        assert plc.sistema_ligado is True

        # Soltar botão Liga
        plc.botao_liga = False
        plc.scan_cycle()
        assert plc.sistema_ligado is True

        # Pressionar botão Desliga (NF: contato abre, vai a False)
        plc.botao_desliga = False
        events = plc.scan_cycle()
        assert plc.sistema_ligado is False
        assert plc.lamp_em_operacao is False
        assert any("PARADA" in e for e in events)

    def test_emergency_stop_latches_and_cuts_burners(self):
        """Testa acionamento do botão de emergência %I0.3 (NF com retenção mecânica)."""
        plc = PLCS71200Caldeira()

        # Liga sistema com parâmetros normais
        plc.botao_liga = True
        plc.ai_nivel_raw = int(0.70 * 27648)  # 70% nível
        plc.ai_temp_raw = int(0.50 * 27648)   # 50% temp
        plc.scan_cycle()
        plc.botao_liga = False
        plc.scan_cycle()

        assert plc.sistema_ligado is True
        assert plc.qtd_queimadores_ativos > 0

        # Aciona emergência (contato NF abre -> False)
        plc.botao_emergencia = False
        events = plc.scan_cycle()

        assert plc.sistema_ligado is False
        assert plc.emergencia_ativa is True
        assert plc.stat_emergencia_latched is True
        assert plc.lamp_emergencia is True
        assert plc.qtd_queimadores_ativos == 0
        assert all(q is False for q in plc.queimadores)
        assert plc.valvula_alivio is True  # Válvula de alívio deve abrir
        assert any("EMERGÊNCIA" in e for e in events)

    def test_emergency_reset_requires_healthy_circuit(self):
        """Testa que o rearme só é aceito se o botão de emergência foi desfeito."""
        plc = PLCS71200Caldeira()
        plc.botao_emergencia = False  # Emergência acionada
        plc.scan_cycle()
        assert plc.stat_emergencia_latched is True

        # Tentativa de reset com emergência ainda pressionada deve FALHAR
        plc.botao_reset = False
        plc.scan_cycle()
        assert plc.stat_emergencia_latched is True

        # Destrava o cogumelo de emergência (contato volta a True)
        plc.botao_emergencia = True
        plc.botao_reset = True
        plc.scan_cycle()
        # Ainda travado pois precisa do pulso de reset após normalizar circuito
        assert plc.stat_emergencia_latched is True

        # Pulso de Reset (NF: True -> False)
        plc.botao_reset = False
        events = plc.scan_cycle()
        assert plc.stat_emergencia_latched is False
        assert plc.emergencia_ativa is False
        assert plc.valvula_alivio is False
        assert any("RESET" in e for e in events)

    def test_water_level_hysteresis(self):
        """Testa controle de água por histerese: Liga < 50%, Desliga >= 75%."""
        plc = PLCS71200Caldeira()

        # Nível inicial baixo (40%) -> Válvula Q0.0 deve LIGAR
        plc.ai_nivel_raw = int(0.40 * 27648)
        plc.scan_cycle()
        assert plc.valvula_agua is True

        # Nível sobe para 60% (dentro da histerese) -> Válvula deve CONTINUAR LIGADA
        plc.ai_nivel_raw = int(0.60 * 27648)
        plc.scan_cycle()
        assert plc.valvula_agua is True

        # Nível atinge 75% -> Válvula deve FECHAR
        plc.ai_nivel_raw = int(0.75 * 27648)
        plc.scan_cycle()
        assert plc.valvula_agua is False

        # Nível desce para 60% -> Válvula deve CONTINUAR FECHADA
        plc.ai_nivel_raw = int(0.60 * 27648)
        plc.scan_cycle()
        assert plc.valvula_agua is False

        # Nível cai abaixo de 50% -> Válvula deve ABRIR novamente
        plc.ai_nivel_raw = int(0.49 * 27648)
        plc.scan_cycle()
        assert plc.valvula_agua is True

    def test_burner_thermal_modulation_and_interlocks(self):
        """Testa modulação dos 6 queimadores por temperatura e intertravamento de nível."""
        plc = PLCS71200Caldeira()

        # Partida
        plc.botao_liga = True
        plc.ai_nivel_raw = int(0.70 * 27648)  # 70% de água (seguro)

        # Temp < 20% -> 6 queimadores
        plc.ai_temp_raw = int(0.15 * 27648)
        plc.scan_cycle()
        assert plc.qtd_queimadores_ativos == 6

        # Temp >= 20% e < 40% -> 5 queimadores
        plc.ai_temp_raw = int(0.25 * 27648)
        plc.scan_cycle()
        assert plc.qtd_queimadores_ativos == 5

        # Temp >= 40% e < 60% -> 4 queimadores
        plc.ai_temp_raw = int(0.45 * 27648)
        plc.scan_cycle()
        assert plc.qtd_queimadores_ativos == 4

        # Temp >= 60% e < 80% -> 3 queimadores
        plc.ai_temp_raw = int(0.65 * 27648)
        plc.scan_cycle()
        assert plc.qtd_queimadores_ativos == 3

        # Temp >= 80% -> 2 queimadores (manutenção térmica)
        plc.ai_temp_raw = int(0.85 * 27648)
        plc.scan_cycle()
        assert plc.qtd_queimadores_ativos == 2

        # INTERTRAVAMENTO: Se o nível cair abaixo de 50%, todos os queimadores cortam
        plc.ai_nivel_raw = int(0.45 * 27648)
        plc.scan_cycle()
        assert plc.qtd_queimadores_ativos == 0
        assert all(q is False for q in plc.queimadores)

    def test_steam_valve_and_relief_valve(self):
        """Testa abertura da linha de vapor Q0.1 e válvula de alívio Q0.2."""
        plc = PLCS71200Caldeira()
        plc.botao_liga = True
        plc.ai_nivel_raw = int(0.70 * 27648)

        # Temperatura ou pressão abaixo do limite -> Válvula de vapor fechada
        plc.ai_temp_raw = int(0.75 * 27648)    # < 80%
        plc.ai_pressao_raw = int(0.75 * 27648) # > 70%
        plc.scan_cycle()
        assert plc.valvula_vapor is False

        # Condição nominal atingida (Temp > 80% e Pressão > 70%) -> Válvula abre
        plc.ai_temp_raw = int(0.85 * 27648)
        plc.ai_pressao_raw = int(0.75 * 27648)
        plc.scan_cycle()
        assert plc.valvula_vapor is True
        assert plc.valvula_alivio is False

        # Sobrepressão crítica (>= 95%) -> Válvula de alívio de segurança abre
        plc.ai_pressao_raw = int(0.96 * 27648)
        events = plc.scan_cycle()
        assert plc.valvula_alivio is True
        assert any("SOBREPRESSÃO CRÍTICA" in e for e in events)


class TestBoilerPhysics:
    """Suíte de testes da modelagem termodinâmica e física da caldeira."""

    def test_water_feed_and_evaporation(self):
        """Testa enchimento de água com bomba ligada e evaporação com calor."""
        physics = BoilerPhysics()
        initial_water = physics.water_level

        # Bomba ligada (valvula_agua=True) por 2 segundos
        physics.update(dt=2.0, valvula_agua=True, valvula_vapor=False, valvula_alivio=False, qtd_queimadores=0)
        assert physics.water_level > initial_water

        # Evaporação em alta temperatura
        physics.temperature = 90.0
        water_before = physics.water_level
        physics.update(dt=2.0, valvula_agua=False, valvula_vapor=False, valvula_alivio=False, qtd_queimadores=6)
        assert physics.water_level < water_before

    def test_thermal_and_steam_generation(self):
        """Testa geração de calor pelos queimadores e produção de pressão de vapor."""
        physics = BoilerPhysics()
        physics.water_level = 60.0
        physics.temperature = 70.0
        initial_pressure = physics.pressure

        # 3 segundos com 6 queimadores a 70°C
        physics.update(dt=3.0, valvula_agua=False, valvula_vapor=False, valvula_alivio=False, qtd_queimadores=6)
        assert physics.temperature > 70.0
        assert physics.pressure > initial_pressure

    def test_emergency_relief_blowdown(self):
        """Testa dreno violento de vapor ao abrir válvula de alívio."""
        physics = BoilerPhysics()
        physics.pressure = 90.0
        physics.temperature = 95.0

        physics.update(dt=1.0, valvula_agua=False, valvula_vapor=False, valvula_alivio=True, qtd_queimadores=0)
        assert physics.pressure < 80.0
        assert physics.temperature < 95.0


def test_full_integrated_boiler_simulation():
    """Teste de Integração: Ciclo completo com física em tempo real e CLP."""
    physics = BoilerPhysics()
    plc = PLCS71200Caldeira()

    # 1. Partida
    plc.botao_liga = True
    plc.scan_cycle()
    plc.botao_liga = False

    # 2. Simulação de 15 segundos de aquecimento e controle
    dt = 0.5
    for _ in range(30):
        lvl, p, t = physics.get_raw_signals()
        plc.ai_nivel_raw, plc.ai_pressao_raw, plc.ai_temp_raw = lvl, p, t
        plc.scan_cycle()
        physics.update(dt, plc.valvula_agua, plc.valvula_vapor, plc.valvula_alivio, plc.qtd_queimadores_ativos)

    # Nível deve ter subido em direção à faixa nominal
    assert physics.water_level > 50.0
    # Queimadores devem estar atuando
    assert plc.qtd_queimadores_ativos > 0
    # Sistema permanece operando normalmente
    assert plc.sistema_ligado is True
    assert plc.emergencia_ativa is False
