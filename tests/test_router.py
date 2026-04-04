from urllib.parse import urlencode
from resources.lib.router import parse_route, parse_params


def test_parse_route_root():
    assert parse_route("plugin://plugin.video.nzbdav/") == "/"


def test_parse_route_search():
    assert parse_route("plugin://plugin.video.nzbdav/search") == "/search"


def test_parse_route_resolve():
    assert parse_route("plugin://plugin.video.nzbdav/resolve") == "/resolve"


def test_parse_route_install_player():
    assert (
        parse_route("plugin://plugin.video.nzbdav/install_player") == "/install_player"
    )


def test_parse_params_movie():
    query = "?" + urlencode(
        {"type": "movie", "title": "The Matrix", "year": "1999", "imdb": "tt0133093"}
    )
    params = parse_params(query)
    assert params["type"] == "movie"
    assert params["title"] == "The Matrix"
    assert params["year"] == "1999"
    assert params["imdb"] == "tt0133093"


def test_parse_params_episode():
    query = "?" + urlencode(
        {"type": "episode", "title": "Breaking Bad", "season": "5", "episode": "14"}
    )
    params = parse_params(query)
    assert params["type"] == "episode"
    assert params["title"] == "Breaking Bad"
    assert params["season"] == "5"
    assert params["episode"] == "14"


def test_parse_params_empty():
    params = parse_params("")
    assert params == {}
