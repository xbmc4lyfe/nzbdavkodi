from unittest.mock import patch
from resources.lib.filter import filter_results, parse_title_metadata


def _make_result(title, size="5000000000"):
    return {
        "title": title,
        "link": "http://example.com/nzb",
        "size": size,
        "indexer": "test",
        "pubdate": "",
        "age": "1 day",
    }


def test_parse_title_metadata_movie():
    meta = parse_title_metadata(
        "The.Matrix.1999.2160p.BluRay.REMUX.HEVC.DTS-HD.MA.7.1-GROUP"
    )
    assert meta["resolution"] == "2160p"
    assert meta["codec"] in ("hevc", "HEVC", "x265/HEVC")
    assert meta["group"] == "GROUP"


def test_parse_title_metadata_no_resolution():
    meta = parse_title_metadata("Some.Random.Title-GROUP")
    assert meta["resolution"] == ""


@patch("resources.lib.filter._get_filter_settings")
def test_filter_excludes_resolution(mock_settings):
    mock_settings.return_value = {
        "resolutions": ["1080p"],
        "hdr": [],
        "audio": [],
        "codecs": [],
        "languages": [],
        "exclude_keywords": [],
        "require_keywords": [],
        "release_group": [],
        "exclude_release_group": [],
        "min_size": 0,
        "max_size": 0,
        "sort_order": 0,
        "max_results": 25,
    }
    results = [
        _make_result("Movie.2024.2160p.BluRay.HEVC-GRP"),
        _make_result("Movie.2024.1080p.BluRay.x264-GRP"),
        _make_result("Movie.2024.720p.WEB-DL.x264-GRP"),
    ]
    filtered = filter_results(results)
    assert len(filtered) == 1
    assert "1080p" in filtered[0]["title"]


@patch("resources.lib.filter._get_filter_settings")
def test_filter_excludes_keywords(mock_settings):
    mock_settings.return_value = {
        "resolutions": ["2160p", "1080p", "720p", "480p"],
        "hdr": [],
        "audio": [],
        "codecs": [],
        "languages": [],
        "exclude_keywords": ["cam", "ts"],
        "require_keywords": [],
        "release_group": [],
        "exclude_release_group": [],
        "min_size": 0,
        "max_size": 0,
        "sort_order": 0,
        "max_results": 25,
    }
    results = [
        _make_result("Movie.2024.CAM.x264-GRP"),
        _make_result("Movie.2024.1080p.BluRay.x264-GRP"),
    ]
    filtered = filter_results(results)
    assert len(filtered) == 1
    assert "BluRay" in filtered[0]["title"]


@patch("resources.lib.filter._get_filter_settings")
def test_filter_size_range(mock_settings):
    mock_settings.return_value = {
        "resolutions": ["2160p", "1080p", "720p", "480p"],
        "hdr": [],
        "audio": [],
        "codecs": [],
        "languages": [],
        "exclude_keywords": [],
        "require_keywords": [],
        "release_group": [],
        "exclude_release_group": [],
        "min_size": 1000,
        "max_size": 10000,
        "sort_order": 0,
        "max_results": 25,
    }
    results = [
        _make_result("Small.Movie-GRP", size="500000000"),
        _make_result("Good.Movie-GRP", size="5000000000"),
        _make_result("Huge.Movie-GRP", size="50000000000"),
    ]
    filtered = filter_results(results)
    assert len(filtered) == 1
    assert "Good" in filtered[0]["title"]


@patch("resources.lib.filter._get_filter_settings")
def test_filter_max_results(mock_settings):
    mock_settings.return_value = {
        "resolutions": ["2160p", "1080p", "720p", "480p"],
        "hdr": [],
        "audio": [],
        "codecs": [],
        "languages": [],
        "exclude_keywords": [],
        "require_keywords": [],
        "release_group": [],
        "exclude_release_group": [],
        "min_size": 0,
        "max_size": 0,
        "sort_order": 0,
        "max_results": 2,
    }
    results = [_make_result("Movie.{}.1080p-GRP".format(i)) for i in range(5)]
    filtered = filter_results(results)
    assert len(filtered) == 2


@patch("resources.lib.filter._get_filter_settings")
def test_filter_preferred_release_group_boosted(mock_settings):
    mock_settings.return_value = {
        "resolutions": ["2160p", "1080p", "720p", "480p"],
        "hdr": [],
        "audio": [],
        "codecs": [],
        "languages": [],
        "exclude_keywords": [],
        "require_keywords": [],
        "release_group": ["SPARKS"],
        "exclude_release_group": [],
        "min_size": 0,
        "max_size": 0,
        "sort_order": 0,
        "max_results": 25,
    }
    results = [
        _make_result("Movie.2024.1080p.BluRay.x264-OTHER"),
        _make_result("Movie.2024.1080p.BluRay.x264-SPARKS"),
    ]
    filtered = filter_results(results)
    assert filtered[0]["title"].endswith("-SPARKS")


@patch("resources.lib.filter._get_filter_settings")
def test_filter_exclude_release_group(mock_settings):
    mock_settings.return_value = {
        "resolutions": ["2160p", "1080p", "720p", "480p"],
        "hdr": [],
        "audio": [],
        "codecs": [],
        "languages": [],
        "exclude_keywords": [],
        "require_keywords": [],
        "release_group": [],
        "exclude_release_group": ["YIFY"],
        "min_size": 0,
        "max_size": 0,
        "sort_order": 0,
        "max_results": 25,
    }
    results = [
        _make_result("Movie.2024.1080p.BluRay.x264-YIFY"),
        _make_result("Movie.2024.1080p.BluRay.x264-SPARKS"),
    ]
    filtered = filter_results(results)
    assert len(filtered) == 1
    assert "SPARKS" in filtered[0]["title"]
