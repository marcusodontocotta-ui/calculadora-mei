"""
Equipe de Validacao - QA, Performance e Logica
Testa o app da Calculadora MEI de forma criteriosa
"""
import asyncio
import httpx
import json
import time
import sys
import io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_URL = "http://localhost:8081"
resultados = []

class QAAgent:
    """Agente de Quality Assurance - Testes funcionais"""
    
    def __init__(self):
        self.name = "QA Agent"
        self.tests_passed = 0
        self.tests_failed = 0
        self.issues = []
    
    def assert_test(self, name, condition, detail=""):
        if condition:
            self.tests_passed += 1
            print(f"    [PASS] {name}")
        else:
            self.tests_failed += 1
            self.issues.append({"test": name, "detail": detail})
            print(f"    [FAIL] {name} - {detail}")
    
    async def run_tests(self, client):
        print("\n  [QA AGENT] Iniciando testes funcionais...")
        
        # Teste 1: Health check
        r = await client.get(f"{API_URL}/api/health")
        self.assert_test("Health check", r.status_code == 200)
        data = r.json()
        self.assert_test("Health retorna status", data.get("status") == "healthy")
        self.assert_test("Health retorna versao", "version" in data)
        self.assert_test("Health retorna teto", data.get("teto_anual") == 81000)
        
        # Teste 2: Pagina principal
        r = await client.get(f"{API_URL}/")
        self.assert_test("Pagina principal carrega", r.status_code == 200)
        self.assert_test("HTML contem titulo", "Calculadora MEI" in r.text)
        self.assert_test("HTML contem formulario", "formDAS" in r.text)
        self.assert_test("HTML contem scripts", "app.js" in r.text)
        
        # Teste 3: Calculo DAS - Servico
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 5000, "tipo_atividade": "servico"
        })
        self.assert_test("Calculo DAS servico retorna 200", r.status_code == 200)
        data = r.json()
        self.assert_test("Calculo retorna sucesso", data.get("sucesso") == True)
        resultado = data.get("resultado", {})
        self.assert_test("DAS servico = R$ 150", resultado.get("componentes", {}).get("total") == 150.0)
        self.assert_test("INSS = R$ 75", resultado.get("componentes", {}).get("inss") == 75.0)
        self.assert_test("ISS = R$ 75", resultado.get("componentes", {}).get("iss") == 75.0)
        self.assert_test("Dentro do teto", resultado.get("dentro_do_teto") == True)
        self.assert_test("Pode emitir NF-e", resultado.get("pode_emitir_nfe") == True)
        
        # Teste 4: Calculo DAS - Comercio
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 4000, "tipo_atividade": "comercio"
        })
        data = r.json()
        resultado = data.get("resultado", {})
        self.assert_test("DAS comercio = R$ 150", resultado.get("componentes", {}).get("total") == 150.0)
        self.assert_test("ICMS = R$ 75", resultado.get("componentes", {}).get("icms") == 75.0)
        self.assert_test("ISS comercio = 0", resultado.get("componentes", {}).get("iss") == 0.0)
        
        # Teste 5: Calculo DAS - Misto
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 6000, "tipo_atividade": "misto"
        })
        data = r.json()
        resultado = data.get("resultado", {})
        self.assert_test("DAS misto = R$ 225", resultado.get("componentes", {}).get("total") == 225.0)
        
        # Teste 6: Fora do teto
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 7000, "tipo_atividade": "servico"
        })
        data = r.json()
        resultado = data.get("resultado", {})
        self.assert_test("Faturamento alto = fora do teto", resultado.get("dentro_do_teto") == False)
        self.assert_test("Nao pode emitir NF-e", resultado.get("pode_emitir_nfe") == False)
        
        # Teste 7: Valores invalidos
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 13, "ano": 2025, "faturamento": 5000, "tipo_atividade": "servico"
        })
        self.assert_test("Mes invalido retorna erro", r.status_code == 422)
        
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": -100, "tipo_atividade": "servico"
        })
        self.assert_test("Faturamento negativo retorna erro", r.status_code == 422)
        
        # Teste 8: Tipo invalido (deve usar default)
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 5000, "tipo_atividade": "invalido"
        })
        self.assert_test("Tipo invalido usa default", r.status_code == 200)
        
        # Teste 9: Alertas
        r = await client.get(f"{API_URL}/api/alertas?mes=8&ano=2025")
        self.assert_test("Alertas retornam 200", r.status_code == 200)
        data = r.json()
        self.assert_test("Alerta tem nivel", "nivel" in data.get("alerta", {}))
        self.assert_test("Alerta tem mensagem", "mensagem" in data.get("alerta", {}))
        
        # Teste 10: Tabela DAS
        r = await client.get(f"{API_URL}/api/tabela-das")
        self.assert_test("Tabela DAS retorna 200", r.status_code == 200)
        data = r.json()
        self.assert_test("Tabela tem comercio", "comercio" in data.get("tabela", {}))
        self.assert_test("Tabela tem servico", "servico" in data.get("tabela", {}))
        self.assert_test("Tabela tem misto", "misto" in data.get("tabela", {}))
        
        # Teste 11: Dashboard
        r = await client.get(f"{API_URL}/api/dashboard")
        self.assert_test("Dashboard retorna 200", r.status_code == 200)
        data = r.json()
        self.assert_test("Dashboard tem resumo", "resumo" in data)
        self.assert_test("Dashboard tem alerta", "alerta" in data)
        self.assert_test("Dashboard tem simulacoes", "simulacoes" in data)
        
        # Teste 12: Simulacao
        r = await client.post(f"{API_URL}/api/simular", json={
            "cenarios": [
                {"nome": "Teste", "faturamento_mensal": 5000, "custos_fixos": 1000, "custos_variaveis_pct": 20}
            ]
        })
        self.assert_test("Simulacao retorna 200", r.status_code == 200)
        data = r.json()
        self.assert_test("Simulacao retorna resultados", len(data.get("resultados", [])) > 0)
        resultado = data.get("resultados", [{}])[0]
        self.assert_test("Resultado tem lucro liquido", "lucro_liquido" in resultado)
        self.assert_test("Resultado tem margem", "margem" in resultado)
        
        return {
            "agent": self.name,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "issues": self.issues
        }


class PerformanceAgent:
    """Agente de Performance - Testes de eficiencia"""
    
    def __init__(self):
        self.name = "Performance Agent"
        self.metrics = []
        self.issues = []
    
    async def run_tests(self, client):
        print("\n  [PERFORMANCE AGENT] Iniciando testes de performance...")
        
        # Teste 1: Tempo de resposta do health check
        start = time.time()
        r = await client.get(f"{API_URL}/api/health")
        elapsed = time.time() - start
        self.metrics.append({"test": "Health check", "time_ms": round(elapsed * 1000, 2)})
        status = "PASS" if elapsed < 0.5 else "FAIL"
        print(f"    [{status}] Health check: {elapsed*1000:.0f}ms (limite: 500ms)")
        if elapsed >= 0.5:
            self.issues.append("Health check lento")
        
        # Teste 2: Tempo de calculo DAS
        start = time.time()
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 5000, "tipo_atividade": "servico"
        })
        elapsed = time.time() - start
        self.metrics.append({"test": "Calculo DAS", "time_ms": round(elapsed * 1000, 2)})
        status = "PASS" if elapsed < 0.3 else "FAIL"
        print(f"    [{status}] Calculo DAS: {elapsed*1000:.0f}ms (limite: 300ms)")
        if elapsed >= 0.3:
            self.issues.append("Calculo DAS lento")
        
        # Teste 3: Tempo de simulacao
        start = time.time()
        r = await client.post(f"{API_URL}/api/simular", json={
            "cenarios": [
                {"nome": "Teste", "faturamento_mensal": 5000, "custos_fixos": 1000, "custos_variaveis_pct": 20}
            ]
        })
        elapsed = time.time() - start
        self.metrics.append({"test": "Simulacao", "time_ms": round(elapsed * 1000, 2)})
        status = "PASS" if elapsed < 0.5 else "FAIL"
        print(f"    [{status}] Simulacao: {elapsed*1000:.0f}ms (limite: 500ms)")
        if elapsed >= 0.5:
            self.issues.append("Simulacao lenta")
        
        # Teste 4: Carga - 10 requests simultaneos
        print("    Testando carga (10 requests)...")
        start = time.time()
        tasks = [client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 5000, "tipo_atividade": "servico"
        }) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        success = sum(1 for r in results if not isinstance(r, Exception))
        self.metrics.append({"test": "Carga 10 req", "time_ms": round(elapsed * 1000, 2), "success": success})
        status = "PASS" if success == 10 and elapsed < 2 else "FAIL"
        print(f"    [{status}] Carga: {success}/10 em {elapsed*1000:.0f}ms")
        if success < 10:
            self.issues.append(f"Apenas {success}/10 requests tiveram sucesso")
        
        # Teste 5: Tamanho da pagina
        r = await client.get(f"{API_URL}/")
        size_kb = len(r.content) / 1024
        self.metrics.append({"test": "Tamanho pagina", "size_kb": round(size_kb, 2)})
        status = "PASS" if size_kb < 100 else "FAIL"
        print(f"    [{status}] Tamanho pagina: {size_kb:.1f}KB (limite: 100KB)")
        if size_kb >= 100:
            self.issues.append("Pagina muito pesada")
        
        # Teste 6: CSS
        r = await client.get(f"{API_URL}/static/style.css")
        css_kb = len(r.content) / 1024
        self.metrics.append({"test": "Tamanho CSS", "size_kb": round(css_kb, 2)})
        status = "PASS" if css_kb < 50 else "FAIL"
        print(f"    [{status}] CSS: {css_kb:.1f}KB (limite: 50KB)")
        if css_kb >= 50:
            self.issues.append("CSS muito pesado")
        
        # Teste 7: JS
        r = await client.get(f"{API_URL}/static/app.js")
        js_kb = len(r.content) / 1024
        self.metrics.append({"test": "Tamanho JS", "size_kb": round(js_kb, 2)})
        status = "PASS" if js_kb < 30 else "FAIL"
        print(f"    [{status}] JS: {js_kb:.1f}KB (limite: 30KB)")
        if js_kb >= 30:
            self.issues.append("JS muito pesado")
        
        return {
            "agent": self.name,
            "metrics": self.metrics,
            "issues": self.issues
        }


class LogicAgent:
    """Agente de Logica - Validacao de regras de negocio"""
    
    def __init__(self):
        self.name = "Logic Agent"
        self.tests_passed = 0
        self.tests_failed = 0
        self.issues = []
    
    def assert_test(self, name, condition, detail=""):
        if condition:
            self.tests_passed += 1
            print(f"    [PASS] {name}")
        else:
            self.tests_failed += 1
            self.issues.append({"test": name, "detail": detail})
            print(f"    [FAIL] {name} - {detail}")
    
    async def run_tests(self, client):
        print("\n  [LOGIC AGENT] Iniciando validacao de regras de negocio...")
        
        # Regra 1: DAS servico deve ser INSS + ISS
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 5000, "tipo_atividade": "servico"
        })
        data = r.json()["resultado"]
        self.assert_test(
            "DAS servico = INSS + ISS",
            data["componentes"]["total"] == data["componentes"]["inss"] + data["componentes"]["iss"],
            f"Total={data['componentes']['total']} vs INSS+ISS={data['componentes']['inss']+data['componentes']['iss']}"
        )
        
        # Regra 2: DAS comercio deve ser INSS + ICMS
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 5000, "tipo_atividade": "comercio"
        })
        data = r.json()["resultado"]
        self.assert_test(
            "DAS comercio = INSS + ICMS",
            data["componentes"]["total"] == data["componentes"]["inss"] + data["componentes"]["icms"],
            f"Total={data['componentes']['total']} vs INSS+ICMS={data['componentes']['inss']+data['componentes']['icms']}"
        )
        
        # Regra 3: DAS misto deve ser INSS + ICMS + ISS
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 5000, "tipo_atividade": "misto"
        })
        data = r.json()["resultado"]
        self.assert_test(
            "DAS misto = INSS + ICMS + ISS",
            data["componentes"]["total"] == data["componentes"]["inss"] + data["componentes"]["icms"] + data["componentes"]["iss"],
            f"Total={data['componentes']['total']} vs Soma={data['componentes']['inss']+data['componentes']['icms']+data['componentes']['iss']}"
        )
        
        # Regra 4: Teto anual = R$ 81.000
        self.assert_test(
            "Teto anual = R$ 81.000",
            data["teto_anual"] == 81000,
            f"Teto={data['teto_anual']}"
        )
        
        # Regra 5: Faturamento dentro do teto (ate 6.750/mes)
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 6750, "tipo_atividade": "servico"
        })
        data = r.json()["resultado"]
        self.assert_test(
            "R$ 6.750/mes = dentro do teto",
            data["dentro_do_teto"] == True,
            f"Faturamento=6750, Dentro={data['dentro_do_teto']}"
        )
        
        # Regra 6: Faturamento acima do teto (6.751/mes)
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 6751, "tipo_atividade": "servico"
        })
        data = r.json()["resultado"]
        self.assert_test(
            "R$ 6.751/mes = fora do teto",
            data["dentro_do_teto"] == False,
            f"Faturamento=6751, Dentro={data['dentro_do_teto']}"
        )
        
        # Regra 7: NF-e so pode se dentro do teto E dentro do limite mensal
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 6750, "tipo_atividade": "servico"
        })
        data = r.json()["resultado"]
        self.assert_test(
            "NF-e: dentro do teto + dentro do limite mensal = pode",
            data["pode_emitir_nfe"] == True
        )
        
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 7000, "tipo_atividade": "servico"
        })
        data = r.json()["resultado"]
        self.assert_test(
            "NF-e: fora do teto = nao pode",
            data["pode_emitir_nfe"] == False
        )
        
        # Regra 8: INSS sempre R$ 75
        for tipo in ["servico", "comercio", "misto"]:
            r = await client.post(f"{API_URL}/api/calcular-das", json={
                "mes": 8, "ano": 2025, "faturamento": 5000, "tipo_atividade": tipo
            })
            data = r.json()["resultado"]
            self.assert_test(
                f"INSS {tipo} = R$ 75",
                data["componentes"]["inss"] == 75.0,
                f"INSS={data['componentes']['inss']}"
            )
        
        # Regra 9: Vencimento sempre dia 20
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 5000, "tipo_atividade": "servico"
        })
        data = r.json()["resultado"]
        self.assert_test(
            "Vencimento = dia 20",
            "20/" in data["data_vencimento"],
            f"Vencimento={data['data_vencimento']}"
        )
        
        # Regra 10: Simulacao - lucro liquido = faturamento - custos - DAS
        r = await client.post(f"{API_URL}/api/simular", json={
            "cenarios": [{"nome": "Teste", "faturamento_mensal": 5000, "custos_fixos": 1000, "custos_variaveis_pct": 20}]
        })
        data = r.json()["resultados"][0]
        # Faturamento anual = 60.000, Custos fixos = 12.000, Custos variaveis = 12.000
        # DAS anual = 150 * 12 = 1.800
        # Lucro bruto = 60.000 - 12.000 - 12.000 = 36.000
        # Lucro liquido = 36.000 - 1.800 = 34.200
        expected_lucro = 5000 * 12 - 1000 * 12 - (5000 * 12 * 20 / 100) - (150 * 12)
        self.assert_test(
            f"Simulacao lucro liquido correto",
            abs(data["lucro_liquido"] - expected_lucro) < 1,
            f"Esperado={expected_lucro}, Obtido={data['lucro_liquido']}"
        )
        
        # Regra 11: Margem = lucro / faturamento * 100
        expected_margem = (data["lucro_liquido"] / data["faturamento_anual"]) * 100
        self.assert_test(
            "Margem calculada corretamente",
            abs(data["margem"] - round(expected_margem, 1)) < 0.2,
            f"Esperado={expected_margem:.1f}%, Obtido={data['margem']}%"
        )
        
        # Regra 12: Faturamento 0 = DAS continua R$ 150 (valor fixo)
        r = await client.post(f"{API_URL}/api/calcular-das", json={
            "mes": 8, "ano": 2025, "faturamento": 0, "tipo_atividade": "servico"
        })
        data = r.json()["resultado"]
        self.assert_test(
            "Faturamento 0 = DAS continua R$ 150",
            data["componentes"]["total"] == 150.0,
            f"DAS={data['componentes']['total']}"
        )
        
        return {
            "agent": self.name,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "issues": self.issues
        }


async def main():
    print("=" * 70)
    print("  EQUIPE DE VALIDACAO - CALCULADORA MEI")
    print("=" * 70)
    print(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  Alvo: {API_URL}")
    
    async with httpx.AsyncClient() as client:
        # Verificar se API esta rodando
        try:
            r = await client.get(f"{API_URL}/api/health", timeout=5)
            print(f"  Status: ONLINE")
        except Exception as e:
            print(f"  Status: OFFLINE ({e})")
            print("  Execute: python main.py")
            return
        
        # Executar agentes
        qa = QAAgent()
        perf = PerformanceAgent()
        logic = LogicAgent()
        
        qa_result = await qa.run_tests(client)
        perf_result = await perf.run_tests(client)
        logic_result = await logic.run_tests(client)
        
        # Relatorio final
        print()
        print("=" * 70)
        print("  RELATORIO FINAL DE VALIDACAO")
        print("=" * 70)
        
        total_passed = qa_result["tests_passed"] + logic_result["tests_passed"]
        total_failed = qa_result["tests_failed"] + logic_result["tests_failed"]
        total_tests = total_passed + total_failed
        
        print(f"\n  TESTES FUNCIONAIS (QA):")
        print(f"    Aprovados: {qa_result['tests_passed']}")
        print(f"    Reprovados: {qa_result['tests_failed']}")
        
        print(f"\n  TESTES DE LOGICA:")
        print(f"    Aprovados: {logic_result['tests_passed']}")
        print(f"    Reprovados: {logic_result['tests_failed']}")
        
        print(f"\n  PERFORMANCE:")
        for m in perf_result["metrics"]:
            if "time_ms" in m:
                print(f"    {m['test']}: {m['time_ms']}ms")
            elif "size_kb" in m:
                print(f"    {m['test']}: {m['size_kb']}KB")
        
        print(f"\n  RESUMO GERAL:")
        print(f"    Total de testes: {total_tests}")
        print(f"    Aprovados: {total_passed} ({total_passed/total_tests*100:.1f}%)")
        print(f"    Reprovados: {total_failed} ({total_failed/total_tests*100:.1f}%)")
        
        all_issues = qa_result["issues"] + perf_result["issues"] + logic_result["issues"]
        if all_issues:
            print(f"\n  PROBLEMAS ENCONTRADOS ({len(all_issues)}):")
            for issue in all_issues:
                if isinstance(issue, dict):
                    print(f"    - {issue['test']}: {issue['detail']}")
                else:
                    print(f"    - {issue}")
        else:
            print(f"\n  NENHUM PROBLEMA ENCONTRADO!")
        
        # Veredicto
        print()
        if total_failed == 0 and len(perf_result["issues"]) == 0:
            print("  [APROVADO] App pronto para producao!")
        elif total_failed <= 2:
            print("  [APROVADO COM RESSALVAS] Corrigir problemas menores")
        else:
            print("  [REPROVADO] Corrigir problemas antes de publicar")
        
        print()
        print("=" * 70)
        
        # Salvar relatorio
        report = {
            "timestamp": datetime.now().isoformat(),
            "api_url": API_URL,
            "qa": qa_result,
            "performance": perf_result,
            "logic": logic_result,
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "pass_rate": f"{total_passed/total_tests*100:.1f}%"
            }
        }
        
        with open("reports/validation_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print("  Relatorio salvo em: reports/validation_report.json")


if __name__ == "__main__":
    import os
    os.makedirs("reports", exist_ok=True)
    asyncio.run(main())
