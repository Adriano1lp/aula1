"""Testes unitários (etapa 2 do pipeline): baratos, determinísticos, rodam em segundos."""

from texto import limpar, so_emojis


def test_remove_acentos_e_caixa():
    assert limpar("Péssimo PRODUTO") == "pessimo produto"


def test_remove_url():
    assert limpar("veja https://loja.exemplo/p/1 aqui") == "veja aqui"


def test_remove_emojis_e_pontuacao():
    assert limpar("Adorei!!! 😍👍") == "adorei"


def test_texto_so_com_emojis():
    assert so_emojis("😍😍😍")
    assert not so_emojis("bom 👍")


def test_espacos_unicos():
    assert limpar("  muito    bom  ") == "muito bom"
