from scripts.evaluate_recommender import (
    build_candidate_pool,
    chronological_split,
    evaluate_metrics,
    fetch_catalog,
    normalize_tmdb_result,
    select_watchlist,
)


def _item(item_id, media_type="movie", release_date="2020-01-01", popularity=10):
    return {
        "title": f"Title {item_id}",
        "tmdb_id": item_id,
        "media_type": media_type,
        "genre_ids": [item_id % 5 + 1],
        "release_date": release_date,
        "popularity": popularity,
    }


def test_normalize_tmdb_result_handles_movie_and_tv_date_shapes():
    movie = normalize_tmdb_result(
        {"id": 1, "title": " Movie ", "release_date": "2020-02-03", "genre_ids": [28]},
        "movie",
    )
    show = normalize_tmdb_result(
        {"id": 2, "name": "Show", "first_air_date": "2021-04-05", "genre_ids": [18]},
        "tv",
    )

    assert movie["title"] == "Movie"
    assert movie["release_date"] == "2020-02-03"
    assert show["media_type"] == "tv"
    assert show["release_date"] == "2021-04-05"


def test_normalize_tmdb_result_discards_missing_evaluation_fields():
    assert normalize_tmdb_result({"id": 1, "title": "No date", "genre_ids": [28]}, "movie") is None
    assert normalize_tmdb_result(
        {"id": 2, "title": "No genres", "release_date": "2020-01-01", "genre_ids": []},
        "movie",
    ) is None


def test_fetch_catalog_deduplicates_pages_and_normalizes_shapes():
    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Session:
        def __init__(self):
            self.calls = []

        def get(self, url, params, timeout):
            self.calls.append((url, params, timeout))
            if params["page"] == 1 and url.endswith("/movie"):
                return Response({
                    "total_pages": 1,
                    "results": [
                        {"id": 1, "title": "Movie", "release_date": "2020-01-01", "genre_ids": [28]},
                    ],
                })
            return Response({
                "total_pages": 1,
                "results": [
                    {"id": 1, "name": "Show", "first_air_date": "2021-01-01", "genre_ids": [18]},
                ],
            })

    session = Session()
    catalog, pages_fetched = fetch_catalog("key", pages_per_media_type=2, session=session, request_delay=0)

    assert pages_fetched == 2
    assert {(item["tmdb_id"], item["media_type"]) for item in catalog} == {(1, "movie"), (1, "tv")}
    assert len(session.calls) == 2


def test_watchlist_selection_is_deterministic_and_media_balanced():
    catalog = [_item(index, "movie" if index % 2 else "tv") for index in range(20)]

    first = select_watchlist(catalog, size=10, seed=7)
    second = select_watchlist(catalog, size=10, seed=7)

    assert first == second
    assert {item["media_type"] for item in first} == {"movie", "tv"}
    assert len(first) == 10


def test_chronological_split_keeps_latest_entries_for_holdout():
    watchlist = [_item(index, release_date=f"2020-01-{index + 1:02d}") for index in range(6)]

    training, holdout = chronological_split(watchlist, holdout_size=2)

    assert [item["tmdb_id"] for item in training] == [0, 1, 2, 3]
    assert [item["tmdb_id"] for item in holdout] == [4, 5]


def test_candidate_pool_contains_holdout_and_unseen_negatives():
    watchlist = [_item(index) for index in range(4)]
    holdout = watchlist[-1:]
    catalog = watchlist + [_item(10), _item(11), _item(12)]

    pool, negative_count = build_candidate_pool(
        catalog, watchlist, holdout, negative_count=2, seed=7
    )

    assert negative_count == 2
    assert len(pool) == 3
    assert {item["tmdb_id"] for item in pool}.issubset({3, 10, 11, 12})
    assert 3 in {item["tmdb_id"] for item in pool}


def test_evaluate_metrics_accepts_tmdb_media_type_in_holdout():
    training = [{**_item(1), "tmdb_media_type": "movie"}]
    holdout = [{**_item(2), "tmdb_media_type": "movie"}]
    candidates = [{**_item(2), "media_type": "movie"}, _item(10, media_type="tv")]

    metrics = evaluate_metrics(training, holdout, candidates, ks=(1,))

    assert metrics["precision@1"]["value"] == 1.0
