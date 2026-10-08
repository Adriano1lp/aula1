"""Testes do resumo do juiz: agregação por categoria e o modo informativo."""

import juiz_resumo


def caso(categoria, nota):
    return {"vars": {"categoria": categoria}, "namedScores": {"fidelidade": nota}}


def test_fidelidade_por_categoria():
    resultado = {"results": {"results": [caso("a", 1), caso("a", 0), caso("b", 1)]}}
    assert juiz_resumo.fidelidade_por_categoria(resultado) == {"a": 0.5, "b": 1.0}


def test_erro_do_juiz_conta_como_reprovado():
    resultado = {"results": {"results": [{"vars": {"categoria": "a"}, "namedScores": None}]}}
    assert juiz_resumo.fidelidade_por_categoria(resultado) == {"a": 0.0}


def test_avaliar_aponta_categorias_abaixo_do_piso():
    motivos = juiz_resumo.avaliar({"a": 0.5, "b": 1.0}, 0.66)
    assert len(motivos) == 1 and motivos[0].startswith("a:")
