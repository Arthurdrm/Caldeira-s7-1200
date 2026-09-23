#!/usr/bin/env python3
"""Script de Demonstração e Validação dos Testes do S7-1200.

Gera um relatório visual completo no terminal para apresentação à equipe.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.simulador.boiler_physics import BoilerPhysics
from src.simulador.plc_s7_1200 import PLCS71200Caldeira

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header():
    print(f"\n{CYAN}{BOLD}{'=' * 74}")
    print("  SIEMENS SIMATIC S7-1200 — RELATÓRIO DE TESTES & VALIDAÇÃO TÉCNICA")
    print("  Sistema de Controle de Caldeira Industrial com Física Termodinâmica")
    print(f"{'=' * 74}{RESET}\n")


def print_step(num: int, title: str, desc: str, passed: bool, details: list[str] = None):
    status = f"{GREEN}[APROVADO]{RESET}" if passed else f"{RED}[FALHOU]{RESET}"
    print(f"{BOLD}{CYAN}Teste {num:02d}:{RESET} {BOLD}{title:<48}{RESET} {status}")
    print(f"  {YELLOW}↳ Detalhe:{RESET} {desc}")
    if details:
        for d in details:
            print(f"     {d}")
    print()


def main():
    print_header()
    time.sleep(0.1)
    passed_count = 0
    total_tests = 9

    # 1. Escalonamento Analógico
    plc = PLCS71200Caldeira()
    plc.ai_nivel_raw = 13824
    plc.ai_pressao_raw = 20736
    plc.ai_temp_raw = 27648
    plc.scan_cycle()
    ok1 = (abs(plc.nivel_perc - 50.0) < 0.1 and abs(plc.pressao_perc - 75.0) < 0.1 and plc.temp_perc == 100.0)
    if ok1: passed_count += 1
    print_step(
        1, "Escalonamento Analógico S7 (0..27648)",
        "Valida conversão das palavras %IW64, %IW66, %IW68 para engenharia (0..100%).",
        ok1, [f"Nível: {plc.nivel_perc:.1f}% | Pressão: {plc.pressao_perc:.1f}% | Temp: {plc.temp_perc:.1f}%"]
    )

    # 2. Botoeira Industrial
    plc = PLCS71200Caldeira()
    plc.botao_liga = True
    ev1 = plc.scan_cycle()
    plc.botao_liga = False
    plc.scan_cycle()
    ok_partida = plc.sistema_ligado
    plc.botao_desliga = False  # NF
    ev2 = plc.scan_cycle()
    ok2 = ok_partida and (not plc.sistema_ligado)
    if ok2: passed_count += 1
    print_step(
        2, "Botoeira Industrial (Partida/Parada)",
        "Borda de subida em %I0.0 (NA) e borda de descida em %I0.1 (NF).",
        ok2, ["Pulso de Partida: Sistema LIGADO", "Pulso de Parada: Sistema DESLIGADO"]
    )

    # 3. Intertravamento de Emergência
    plc = PLCS71200Caldeira()
    plc.botao_liga = True
    plc.ai_nivel_raw = int(0.7 * 27648)
    plc.scan_cycle()
    plc.botao_liga = False
    plc.botao_emergencia = False  # Botão NF pressionado
    plc.scan_cycle()
    ok3 = (not plc.sistema_ligado) and plc.stat_emergencia_latched and plc.valvula_alivio and (plc.qtd_queimadores_ativos == 0)
    if ok3: passed_count += 1
    print_step(
        3, "Circuito de Emergência (%I0.3)",
        "Parada imediata: corta todos os queimadores e abre Válvula de Alívio %Q0.2.",
        ok3, ["Status: Emergência TRAVADA", "Queimadores: 0 ativos", "Válvula Alívio: ABERTA"]
    )

    # 4. Rearme Seguro
    plc.botao_emergencia = True # destrava mecânica
    plc.botao_reset = False     # pulso de reset
    plc.scan_cycle()
    ok4 = (not plc.stat_emergencia_latched) and (not plc.valvula_alivio)
    if ok4: passed_count += 1
    print_step(
        4, "Procedimento de Rearme (%I0.2)",
        "Exige circuito seguro reestabelecido antes de aceitar pulso de Reset.",
        ok4, ["Status após Reset: Normalizado, pronto para nova partida"]
    )

    # 5. Controle de Nível (Histerese)
    plc = PLCS71200Caldeira()
    plc.ai_nivel_raw = int(0.40 * 27648)
    plc.scan_cycle()
    v1 = plc.valvula_agua  # True
    plc.ai_nivel_raw = int(0.60 * 27648)
    plc.scan_cycle()
    v2 = plc.valvula_agua  # True (mantém)
    plc.ai_nivel_raw = int(0.76 * 27648)
    plc.scan_cycle()
    v3 = plc.valvula_agua  # False (desliga)
    ok5 = v1 and v2 and (not v3)
    if ok5: passed_count += 1
    print_step(
        5, "Controle de Água por Histerese (%Q0.0)",
        "Liga com nível < 50%, sustenta na faixa intermediária e desliga em >= 75%.",
        ok5, ["40% -> Válvula ABERTA", "60% (subindo) -> MANTÉM ABERTA", "76% -> Válvula FECHADA"]
    )

    # 6. Modulação Térmica
    plc = PLCS71200Caldeira()
    plc.botao_liga = True
    plc.ai_nivel_raw = int(0.70 * 27648)
    plc.ai_temp_raw = int(0.15 * 27648)
    plc.scan_cycle()
    q_frio = plc.qtd_queimadores_ativos  # 6
    plc.ai_temp_raw = int(0.85 * 27648)
    plc.scan_cycle()
    q_quente = plc.qtd_queimadores_ativos  # 2
    ok6 = (q_frio == 6) and (q_quente == 2)
    if ok6: passed_count += 1
    print_step(
        6, "Modulação dos 6 Queimadores (%Q0.3 a %Q1.0)",
        "Graduação automática de queima (6 queimadores na partida fria -> 2 em cruzeiro).",
        ok6, [f"Frio (15%) -> {q_frio} Queimadores", f"Cruzeiro (85%) -> {q_quente} Queimadores"]
    )

    # 7. Válvula de Vapor e Alívio de Sobrepressão
    plc = PLCS71200Caldeira()
    plc.botao_liga = True
    plc.ai_nivel_raw = int(0.70 * 27648)
    plc.ai_temp_raw = int(0.85 * 27648)
    plc.ai_pressao_raw = int(0.75 * 27648)
    plc.scan_cycle()
    v_vapor_ok = plc.valvula_vapor
    plc.ai_pressao_raw = int(0.96 * 27648)
    plc.scan_cycle()
    v_alivio_ok = plc.valvula_alivio
    ok7 = v_vapor_ok and v_alivio_ok
    if ok7: passed_count += 1
    print_step(
        7, "Válvulas de Vapor (%Q0.1) & Alívio (%Q0.2)",
        "Liberação de vapor aos consumidores e proteção contra sobrepressão crítica (>=95%).",
        ok7, ["Temp>80% + Pressão>70% -> Vapor LIBERADO", "Pressão >= 95% -> Válvula de Alívio DISPARADA"]
    )

    # 8. Física Termodinâmica
    physics = BoilerPhysics()
    physics.water_level = 50.0
    physics.temperature = 80.0
    p_init = physics.pressure
    physics.update(dt=2.0, valvula_agua=False, valvula_vapor=False, valvula_alivio=False, qtd_queimadores=6)
    ok8 = (physics.temperature > 80.0) and (physics.pressure > p_init)
    if ok8: passed_count += 1
    print_step(
        8, "Modelo Físico Termodinâmico",
        "Equações de balanço térmico, geração de pressão de vapor e consumo de massa.",
        ok8, [f"Temperatura: 80.0°C -> {physics.temperature:.1f}°C", f"Pressão: {p_init:.1f}% -> {physics.pressure:.1f}%"]
    )

    # 9. Integração Tempo Real
    physics = BoilerPhysics()
    plc = PLCS71200Caldeira()
    plc.botao_liga = True
    plc.scan_cycle()
    plc.botao_liga = False
    for _ in range(20):
        lvl, p, t = physics.get_raw_signals()
        plc.ai_nivel_raw, plc.ai_pressao_raw, plc.ai_temp_raw = lvl, p, t
        plc.scan_cycle()
        physics.update(0.5, plc.valvula_agua, plc.valvula_vapor, plc.valvula_alivio, plc.qtd_queimadores_ativos)
    ok9 = plc.sistema_ligado and (physics.water_level > 50.0)
    if ok9: passed_count += 1
    print_step(
        9, "Simulação Integrada em Ciclo Fechado",
        "Execução síncrona com CLP e planta física em malha fechada durante 10 segundos.",
        ok9, [f"Nível final: {physics.water_level:.1f}%", f"Temp final: {physics.temperature:.1f}°C", f"Pressão final: {physics.pressure:.1f}%"]
    )

    # Sumário Final
    print(f"{CYAN}{BOLD}{'=' * 74}")
    if passed_count == total_tests:
        print(f"  {GREEN}{BOLD}RESULTADO: {passed_count}/{total_tests} TESTES APROVADOS (100% SUCESSO) — SISTEMA HOMOLOGADO{RESET}")
    else:
        print(f"  {RED}{BOLD}RESULTADO: {passed_count}/{total_tests} TESTES APROVADOS{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 74}{RESET}\n")


if __name__ == "__main__":
    main()
