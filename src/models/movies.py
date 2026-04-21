from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Movie:
    id: str

    # IDs
    tmdb_id: Optional[int]
    imdb_id: Optional[str]

    # Core
    title: str
    original_title: Optional[str]
    release_date: Optional[str]
    year: Optional[int]

    # Content
    genres: List[str]
    overview: Optional[str]

    # Metadata
    runtime: Optional[int]
    language: Optional[str]
    country: Optional[List[str]]

    # Metrics
    popularity: Optional[float]
    vote_average: Optional[float]
    vote_count: Optional[int]

    # Financial
    revenue: Optional[int]
    budget: Optional[int]

    # Media
    poster_url: Optional[str]
    backdrop_url: Optional[str]

    # People
    director: Optional[str]
    cast: Optional[List[str]]

    # Production
    production_companies: Optional[List[str]]

    # Enrichment
    rt_score: Optional[float]
    rt_reviews: Optional[int]

    # Processing
    source_priority_score: Optional[float]
