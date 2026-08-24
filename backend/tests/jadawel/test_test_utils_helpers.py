from jadawel.test_utils.helpers import AnyList


def test_any_list_matches_lists_from_either_comparison_direction():
    assert AnyList() == ["value"]
    assert ["value"] == AnyList()
    assert AnyList() != {"value": True}
