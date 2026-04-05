from unittest.mock import patch
from resources.lib.filter import (
    filter_results,
    parse_title_metadata,
    _sort_results,
)


def _make_result(title, size="5000000000", pubdate="", link="http://example.com/nzb"):
    return {
        "title": title,
        "link": link,
        "size": size,
        "indexer": "test",
        "pubdate": pubdate,
        "age": "1 day",
    }


# --- parse_title_metadata with real PTT (not mocked) ---


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


def test_parse_title_metadata_1080p_x264():
    """Real PTT parsing of a typical 1080p x264 release."""
    meta = parse_title_metadata("Inception.2010.1080p.BluRay.x264-FGT")
    assert meta["resolution"] == "1080p"
    assert meta["codec"] == "x264/AVC"
    assert meta["group"] == "FGT"


def test_parse_title_metadata_720p_web():
    meta = parse_title_metadata("The.Office.S09E23.720p.WEB-DL.AAC2.0.H.264-NTb")
    assert meta["resolution"] == "720p"


def test_parse_title_metadata_4k_hdr():
    meta = parse_title_metadata(
        "Dune.Part.Two.2024.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX"
    )
    assert meta["resolution"] == "2160p"


def test_parse_title_metadata_empty_title():
    """Empty title should return empty metadata without crashing."""
    meta = parse_title_metadata("")
    assert meta["resolution"] == ""
    assert meta["codec"] == ""
    assert meta["group"] == ""
    assert meta["hdr"] == []
    assert meta["audio"] == []
    assert meta["languages"] == []


def test_parse_title_metadata_special_characters():
    """Title with special characters should not crash."""
    meta = parse_title_metadata("Spider-Man.No.Way.Home.2021.1080p.BluRay.x264-SPARKS")
    assert meta["resolution"] == "1080p"
    assert meta["group"] == "SPARKS"


def test_parse_title_metadata_dots_and_dashes():
    """Complex title with many dots and dashes."""
    meta = parse_title_metadata(
        "Mr.Robot.S04E13.Series.Finale.Part.2.1080p.AMZN.WEB-DL.DDP5.1.H.264-NTG"
    )
    assert meta["resolution"] == "1080p"


# --- Full search->filter pipeline with real PTT ---


def _all_pass_settings():
    """Settings that accept everything."""
    return {
        "resolutions": ["2160p", "1080p", "720p", "480p"],
        "hdr": ["HDR10", "HDR10+", "Dolby Vision", "HLG", "SDR"],
        "audio": ["Atmos", "TrueHD", "DTS-HD MA", "DTS:X", "DD+", "DD", "AAC"],
        "codecs": ["x265/HEVC", "x264/AVC", "AV1", "VP9", "MPEG-2"],
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


@patch("resources.lib.filter._get_filter_settings")
def test_filter_pipeline_realistic_titles(mock_settings):
    """Full pipeline: search results with realistic NZB titles, parsed by PTT."""
    mock_settings.return_value = {
        "resolutions": ["1080p"],
        "hdr": ["SDR"],
        "audio": ["Atmos", "TrueHD", "DTS-HD MA", "DTS:X", "DD+", "DD", "AAC"],
        "codecs": ["x265/HEVC", "x264/AVC"],
        "languages": [],
        "exclude_keywords": ["cam"],
        "require_keywords": [],
        "release_group": [],
        "exclude_release_group": ["YIFY"],
        "min_size": 0,
        "max_size": 0,
        "sort_order": 0,
        "max_results": 25,
    }
    results = [
        _make_result(
            "The.Matrix.1999.2160p.UHD.BluRay.REMUX.HDR.HEVC.DTS-HD.MA.7.1-FraMeSToR"
        ),
        _make_result("The.Matrix.1999.1080p.BluRay.x264.DTS-FGT"),
        _make_result("The.Matrix.1999.1080p.BluRay.x264-YIFY"),
        _make_result("The.Matrix.1999.CAM.x264-JUNK"),
        _make_result("The.Matrix.1999.720p.WEB-DL.x264-GRP"),
    ]
    filtered = filter_results(results)
    # Should keep only the 1080p x264 FGT release (YIFY excluded, CAM excluded,
    # 2160p excluded by resolution, 720p excluded by resolution)
    assert len(filtered) == 1
    assert "FGT" in filtered[0]["title"]


@patch("resources.lib.filter._get_filter_settings")
def test_filter_pipeline_empty_results(mock_settings):
    mock_settings.return_value = _all_pass_settings()
    filtered = filter_results([])
    assert filtered == []


@patch("resources.lib.filter._get_filter_settings")
def test_filter_pipeline_all_filtered_out(mock_settings):
    mock_settings.return_value = {
        "resolutions": ["480p"],
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
    ]
    filtered = filter_results(results)
    assert len(filtered) == 0


# --- Existing filter tests ---


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


# --- Edge case tests ---


@patch("resources.lib.filter._get_filter_settings")
def test_filter_very_large_size(mock_settings):
    """100GB+ files should not overflow or crash."""
    mock_settings.return_value = _all_pass_settings()
    results = [_make_result("Movie.2024.2160p.REMUX-GRP", size="107374182400")]
    filtered = filter_results(results)
    assert len(filtered) == 1


@patch("resources.lib.filter._get_filter_settings")
def test_filter_zero_size(mock_settings):
    """Zero-size results should pass if no min_size set."""
    mock_settings.return_value = _all_pass_settings()
    results = [_make_result("Movie.2024.1080p-GRP", size="0")]
    filtered = filter_results(results)
    assert len(filtered) == 1


@patch("resources.lib.filter._get_filter_settings")
def test_filter_empty_size(mock_settings):
    """Empty size string should not crash."""
    mock_settings.return_value = _all_pass_settings()
    results = [_make_result("Movie.2024.1080p-GRP", size="")]
    filtered = filter_results(results)
    assert len(filtered) == 1


@patch("resources.lib.filter._get_filter_settings")
def test_filter_require_keywords(mock_settings):
    mock_settings.return_value = {
        "resolutions": [],
        "hdr": [],
        "audio": [],
        "codecs": [],
        "languages": [],
        "exclude_keywords": [],
        "require_keywords": ["remux"],
        "release_group": [],
        "exclude_release_group": [],
        "min_size": 0,
        "max_size": 0,
        "sort_order": 0,
        "max_results": 25,
    }
    results = [
        _make_result("Movie.2024.1080p.BluRay.REMUX.HEVC-GRP"),
        _make_result("Movie.2024.1080p.BluRay.x264-GRP"),
    ]
    filtered = filter_results(results)
    assert len(filtered) == 1
    assert "REMUX" in filtered[0]["title"]


# --- Sort order tests ---


def test_sort_by_size_largest_first():
    results = [
        _make_result("Small", size="1000000000"),
        _make_result("Large", size="9000000000"),
    ]
    for r in results:
        r["_meta"] = parse_title_metadata(r["title"])
    settings = _all_pass_settings()
    settings["sort_order"] = 1
    sorted_r = _sort_results(results, settings)
    assert sorted_r[0]["title"] == "Large"


def test_sort_by_size_smallest_first():
    results = [
        _make_result("Large", size="9000000000"),
        _make_result("Small", size="1000000000"),
    ]
    for r in results:
        r["_meta"] = parse_title_metadata(r["title"])
    settings = _all_pass_settings()
    settings["sort_order"] = 2
    sorted_r = _sort_results(results, settings)
    assert sorted_r[0]["title"] == "Small"


def test_sort_relevance_preserves_order():
    results = [
        _make_result("First"),
        _make_result("Second"),
        _make_result("Third"),
    ]
    for r in results:
        r["_meta"] = parse_title_metadata(r["title"])
    settings = _all_pass_settings()
    settings["sort_order"] = 0
    sorted_r = _sort_results(results, settings)
    assert sorted_r[0]["title"] == "First"
    assert sorted_r[1]["title"] == "Second"
    assert sorted_r[2]["title"] == "Third"
