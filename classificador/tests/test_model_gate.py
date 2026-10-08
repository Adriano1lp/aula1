"""Testes do model gate: as três regras, sem treinar nada."""

import model_gate

PRODUCAO = {"f1_macro": 0.82, "f1_por_classe": {"positiva": 0.87, "negativa": 0.81, "neutra": 0.78}}


def candidato(macro, positiva=0.87, negativa=0.81, neutra=0.78):
    return {
        "f1_macro": macro,
        "f1_por_classe": {"positiva": positiva, "negativa": negativa, "neutra": neutra},
    }


def test_aprova_candidato_igual_ou_melhor():
    assert model_gate.avaliar(candidato(0.83), PRODUCAO) == []


def test_reprova_f1_macro_abaixo_do_minimo():
    assert any("F1 macro" in m for m in model_gate.avaliar(candidato(0.75), PRODUCAO))


def test_piso_por_classe_nao_se_esconde_na_media():
    """Média boa, mas uma classe ruim: o gate precisa barrar."""
    motivos = model_gate.avaliar(candidato(0.83, positiva=0.95, negativa=0.95, neutra=0.60), PRODUCAO)
    assert any("classe 'neutra'" in m for m in motivos)


def test_reprova_piora_em_relacao_a_producao():
    assert any("piora" in m for m in model_gate.avaliar(candidato(0.797), {**PRODUCAO, "f1_macro": 0.83}))
