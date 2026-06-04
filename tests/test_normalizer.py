"""Tests unitaires des normalisations transverses (dates, textes)."""

from horragor.transform.normalizer import normalize_date, normalize_movie, normalize_text


class TestNormalizeDate:
    def test_full_iso_date_unchanged(self):
        assert normalize_date("1999-10-29") == "1999-10-29"

    def test_year_only_becomes_first_january(self):
        assert normalize_date("1978") == "1978-01-01"

    def test_none_returns_none(self):
        assert normalize_date(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_date("") is None

    def test_invalid_returns_none(self):
        assert normalize_date("pas une date") is None


class TestNormalizeText:
    def test_strips_html_tags(self):
        assert normalize_text("<p>Hello <b>world</b></p>") == "Hello world"

    def test_collapses_whitespace(self):
        assert normalize_text("trop   d'\tespaces\n ici") == "trop d' espaces ici"

    def test_none_returns_none(self):
        assert normalize_text(None) is None


class TestNormalizeMovie:
    def test_preserves_unmapped_fields_and_normalizes(self):
        raw = {
            "tmdb_id": 42,
            "title": "  The   Thing ",
            "overview": "<i>Antarctic horror</i>",
            "original_title": "The Thing",
            "release_date": "1982",
            "genre_ids": [27],
            "vote_average": 8.2,
        }
        out = normalize_movie(raw)
        assert out["tmdb_id"] == 42  # champ non mappé préservé
        assert out["genre_ids"] == [27]
        assert out["vote_average"] == 8.2
        assert out["title"] == "The Thing"
        assert out["overview"] == "Antarctic horror"
        assert out["release_date"] == "1982-01-01"
