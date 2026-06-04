"""Tests du parsing Rotten Tomatoes et de l'adapter canonique."""

import json

from horragor.ingestion.rotten.parser import _percent, _year, parse_movie_page
from horragor.reconciliation import adapters
from horragor.reconciliation.adapters import rotten_films

# Fixture HTML reproduisant la structure réelle d'une page film RT :
# JSON-LD (titre/année/genres/tomatometer) + web components (audience/consensus).
FIXTURE_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@type": "Movie",
  "name": "Hereditary",
  "dateCreated": "2018-01-21",
  "genre": ["Horror", "Mystery & Thriller"],
  "aggregateRating": {"@type": "AggregateRating", "name": "Tomatometer", "ratingValue": "90"}
}
</script></head>
<body>
<media-scorecard>
  <rt-text slot="title">Hereditary</rt-text>
  <rt-text slot="critics-score">90%</rt-text>
  <rt-text slot="audience-score">72%</rt-text>
</media-scorecard>
<div id="critics-consensus">Certified fresh. Critics Consensus Hereditary is unsettling.</div>
</body></html>
"""


class TestHelpers:
    def test_percent(self):
        assert _percent("90%") == 90
        assert _percent("  72 %") == 72
        assert _percent(None) is None
        assert _percent("Tomatometer") is None

    def test_year(self):
        assert _year("2018-01-21") == 2018
        assert _year(None) is None


class TestParseMoviePage:
    def test_extracts_all_fields(self):
        out = parse_movie_page(FIXTURE_HTML)
        assert out["title"] == "Hereditary"
        assert out["year"] == 2018
        assert out["genres"] == ["Horror", "Mystery & Thriller"]
        assert out["tomatometer"] == 90  # via JSON-LD
        assert out["audience"] == 72  # via web component
        assert out["critics_consensus"] == "Hereditary is unsettling."

    def test_strips_disambiguation_year_suffix(self):
        # RT nomme certains films « Titre (YYYY) » : le suffixe doit sauter
        # pour ne pas casser le fuzzy matching titre+année.
        html = FIXTURE_HTML.replace('"name": "Hereditary"', '"name": "A Quiet Place (2018)"')
        out = parse_movie_page(html)
        assert out["title"] == "A Quiet Place"

    def test_audience_falls_back_to_none_when_absent(self):
        html = '<html><body><media-scorecard></media-scorecard></body></html>'
        out = parse_movie_page(html)
        assert out["audience"] is None
        assert out["tomatometer"] is None
        assert out["title"] is None


class TestRottenAdapter:
    def test_maps_scores_and_source(self, tmp_path, monkeypatch):
        data = [
            {
                "title": "Hereditary",
                "year": 2018,
                "genres": ["Horror"],
                "tomatometer": 90,
                "audience": 72,
                "critics_consensus": "Unsettling.",
            }
        ]
        p = tmp_path / "rotten_clean.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(adapters, "ROTTEN_CLEAN", p)

        films = rotten_films()
        assert len(films) == 1
        f = films[0]
        assert f.rt_tomatometer == 90
        assert f.rt_audience == 72
        assert f.rt_critics_consensus == "Unsettling."
        assert f.sources == ["rotten_tomatoes"]

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(adapters, "ROTTEN_CLEAN", tmp_path / "absent.json")
        assert rotten_films() == []
