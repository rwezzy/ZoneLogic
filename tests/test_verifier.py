from zonelogic.crosscheck import corroborate

# Caption fragments taken from real VAST search results seen today.
NYC = ("The scene is a busy urban intersection in New York City, viewed from an elevated perspective. "
       "A white van is stopped at the marked crosswalk, with a silver SUV driving past it. "
       "Pedestrians are crossing the street at a marked crosswalk.")
TORONTO = ("A white pickup truck is visible ahead, stopped at the intersection. "
           "There are no pedestrians or cyclists visible in the scene. No lane-blocking vehicles are present.")


def test_agrees_with_synonyms_and_plurals():
    assert corroborate("car", NYC) == "agrees"       # van, SUV
    assert corroborate("person", NYC) == "agrees"    # Pedestrians
    assert corroborate("truck", TORONTO) == "agrees"  # pickup truck


def test_negation_is_a_contradiction():
    assert corroborate("person", TORONTO) == "contradicts"   # "no pedestrians or cyclists"
    assert corroborate("bicycle", TORONTO) == "contradicts"


def test_positive_mention_beats_a_negated_one():
    # "No lane-blocking vehicles" is negated, but "pickup truck" is a positive truck mention.
    assert corroborate("truck", TORONTO) == "agrees"


def test_silent():
    assert corroborate("bottle", NYC) == "silent"
    assert corroborate("car", "") == "silent"
    assert corroborate("car", None) == "silent"
