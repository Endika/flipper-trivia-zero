import pytest

from trivia_pack.category_map import (
    CATEGORY_MAP,
    BucketId,
    map_opentdb_to_bucket,
)


def test_general_knowledge_maps_to_cultura_general() -> None:
    assert map_opentdb_to_bucket("General Knowledge") == BucketId.CULTURA_GENERAL


def test_geography_maps_to_geografia() -> None:
    assert map_opentdb_to_bucket("Geography") == BucketId.GEOGRAFIA


def test_sports_maps_to_deportes_y_ocio() -> None:
    assert map_opentdb_to_bucket("Sports") == BucketId.DEPORTES_Y_OCIO


def test_entertainment_subcategories_map_to_entretenimiento() -> None:
    for sub in (
        "Entertainment: Books",
        "Entertainment: Film",
        "Entertainment: Music",
        "Entertainment: Television",
        "Entertainment: Video Games",
        "Entertainment: Comics",
        "Entertainment: Japanese Anime & Manga",
    ):
        bucket = map_opentdb_to_bucket(sub)
        # Books map to Arts & Literature; the rest go to Entertainment
        if sub == "Entertainment: Books":
            assert bucket == BucketId.ARTE_Y_LITERATURA
        else:
            assert bucket == BucketId.ENTRETENIMIENTO


def test_science_subcategories_map_to_ciencia_y_naturaleza() -> None:
    for sub in (
        "Science & Nature",
        "Science: Computers",
        "Science: Mathematics",
        "Science: Gadgets",
        "Animals",
        "Vehicles",
    ):
        assert map_opentdb_to_bucket(sub) == BucketId.CIENCIA_Y_NATURALEZA


def test_history_and_politics_map_to_historia() -> None:
    assert map_opentdb_to_bucket("History") == BucketId.HISTORIA
    assert map_opentdb_to_bucket("Politics") == BucketId.HISTORIA


def test_mythology_and_art_map_to_arte_y_literatura() -> None:
    assert map_opentdb_to_bucket("Mythology") == BucketId.ARTE_Y_LITERATURA
    assert map_opentdb_to_bucket("Art") == BucketId.ARTE_Y_LITERATURA


def test_unknown_opentdb_category_raises() -> None:
    with pytest.raises(KeyError):
        map_opentdb_to_bucket("Some Future Category")


def test_full_table_covers_all_24_opentdb_categories() -> None:
    # Spec §4.4: 24 OpenTDB categories must each have a bucket.
    expected = {
        "General Knowledge",
        "Entertainment: Books",
        "Entertainment: Film",
        "Entertainment: Music",
        "Entertainment: Musicals & Theatres",
        "Entertainment: Television",
        "Entertainment: Video Games",
        "Entertainment: Board Games",
        "Entertainment: Comics",
        "Entertainment: Japanese Anime & Manga",
        "Entertainment: Cartoon & Animations",
        "Celebrities",
        "Science & Nature",
        "Science: Computers",
        "Science: Mathematics",
        "Science: Gadgets",
        "Animals",
        "Vehicles",
        "Geography",
        "History",
        "Politics",
        "Mythology",
        "Art",
        "Sports",
    }
    assert set(CATEGORY_MAP.keys()) == expected
