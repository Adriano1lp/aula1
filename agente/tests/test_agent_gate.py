"""Testes do agent gate: a regra do enunciado, sem LLM e sem rede."""

import yaml

import agent_gate

LIMITES = yaml.safe_load((agent_gate.PASTA / "limites.yaml").read_text())


def categoria(rot, rec, res):
    return {"roteamento": rot, "recuperacao": rec, "resposta": res}


def test_categoria_piora_mesmo_com_media_melhor():
    """O caso fraude_vendedor do enunciado: a média sobe, mas uma categoria regride."""
    baseline = {"fraude_vendedor": categoria(1.0, 1.0, 1.0), "entrega": categoria(0.33, 0.33, 0.33)}
    candidato = {"fraude_vendedor": categoria(0.33, 0.33, 0.33), "entrega": categoria(1.0, 1.0, 1.0)}

    assert agent_gate.media(candidato, "roteamento") == agent_gate.media(baseline, "roteamento")
    motivos = agent_gate.avaliar(candidato, baseline, LIMITES)
    assert any("fraude_vendedor/roteamento: regrediu" in m for m in motivos)


def test_dois_casos_a_menos_e_ruido():
    """Cair 2 de 6 casos (≈33 p.p.) é ruído do LLM: dentro da tolerância e acima do piso."""
    baseline = {"entrega": categoria(0.83, 0.83, 0.83)}
    candidato = {"entrega": categoria(0.5, 0.5, 0.5)}
    assert agent_gate.avaliar(candidato, baseline, LIMITES) == []


def test_tres_casos_a_menos_e_regressao():
    baseline = {"entrega": categoria(0.83, 0.83, 0.83)}
    candidato = {"entrega": categoria(0.33, 0.33, 0.33)}
    motivos = agent_gate.avaliar(candidato, baseline, LIMITES)
    assert any("regrediu" in m for m in motivos)
    assert any("abaixo do piso" in m for m in motivos)


def test_sem_baseline_so_vale_o_piso():
    assert agent_gate.avaliar({"entrega": categoria(0.83, 0.83, 0.83)}, {}, LIMITES) == []
    assert agent_gate.avaliar({"entrega": categoria(0.17, 1.0, 1.0)}, {}, LIMITES)


def test_taxas_por_categoria_agrega_os_casos():
    def caso(cat, rot):
        return {
            "vars": {"categoria": cat},
            "namedScores": {"roteamento": rot, "recuperacao": 1, "resposta": 1},
        }

    resultado = {"results": {"results": [caso("a", 1), caso("a", 0), caso("b", 1)]}}
    taxas = agent_gate.taxas_por_categoria(resultado)
    assert taxas["a"]["roteamento"] == 0.5
    assert taxas["b"]["roteamento"] == 1.0


def test_erro_de_execucao_conta_como_reprovado():
    """Timeout ou limite do provedor não pode virar aprovação silenciosa."""
    resultado = {"results": {"results": [{"vars": {"categoria": "a"}, "namedScores": None}]}}
    assert agent_gate.taxas_por_categoria(resultado)["a"] == categoria(0, 0, 0)
