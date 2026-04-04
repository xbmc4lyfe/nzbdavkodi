import os
from unittest.mock import patch
from resources.lib.hydra import search_hydra, parse_results


def _load_fixture(name):
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", name)
    with open(fixture_path, "r") as f:
        return f.read()


def test_parse_results_movie():
    xml_text = _load_fixture("hydra_movie_response.xml")
    results = parse_results(xml_text)
    assert len(results) == 2
    assert (
        results[0]["title"]
        == "The.Matrix.1999.2160p.UHD.BluRay.REMUX.HDR.HEVC.DTS-HD.MA.7.1-GROUP"
    )
    assert results[0]["link"] == "http://hydra:5076/getnzb/abc123?apikey=testkey"
    assert results[0]["size"] == "45000000000"
    assert results[0]["indexer"] == "NZBgeek"
    assert "pubdate" in results[0]


def test_parse_results_tv():
    xml_text = _load_fixture("hydra_tv_response.xml")
    results = parse_results(xml_text)
    assert len(results) == 1
    assert (
        results[0]["title"]
        == "Breaking.Bad.S05E14.Ozymandias.1080p.BluRay.x265.DTS-HD.MA.5.1-NTb"
    )
    assert results[0]["size"] == "4200000000"


def test_parse_results_empty():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:newznab="http://www.newznab.com/DTD/2010/feeds/attributes/">
        <channel><newznab:response offset="0" total="0"/></channel>
    </rss>"""
    results = parse_results(xml_text)
    assert results == []


@patch("resources.lib.hydra._get_settings")
@patch("resources.lib.hydra._http_get")
def test_search_hydra_movie(mock_http, mock_settings):
    mock_settings.return_value = ("http://hydra:5076", "testkey")
    mock_http.return_value = _load_fixture("hydra_movie_response.xml")

    results = search_hydra("movie", "The Matrix", year="1999", imdb="tt0133093")
    assert len(results) == 2

    call_url = mock_http.call_args[0][0]
    assert "t=movie" in call_url
    assert "imdbid=tt0133093" in call_url
    assert "apikey=testkey" in call_url


@patch("resources.lib.hydra._get_settings")
@patch("resources.lib.hydra._http_get")
def test_search_hydra_tv(mock_http, mock_settings):
    mock_settings.return_value = ("http://hydra:5076", "testkey")
    mock_http.return_value = _load_fixture("hydra_tv_response.xml")

    results = search_hydra("episode", "Breaking Bad", season="5", episode="14")
    assert len(results) == 1

    call_url = mock_http.call_args[0][0]
    assert "t=tvsearch" in call_url
    assert "season=5" in call_url
    assert "ep=14" in call_url


@patch("resources.lib.hydra._get_settings")
@patch("resources.lib.hydra._http_get")
def test_search_hydra_connection_error(mock_http, mock_settings):
    mock_settings.return_value = ("http://hydra:5076", "testkey")
    mock_http.side_effect = Exception("Connection refused")

    results = search_hydra("movie", "The Matrix")
    assert results == []
