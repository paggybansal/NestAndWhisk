from apps.core.delivery import get_delhi_ncr_delivery_experience


def test_delivery_experience_defaults_to_generic_delhi_ncr_guidance():
    experience = get_delhi_ncr_delivery_experience()

    assert experience["status"] == "default"
    assert experience["badge"] == "Delhi NCR local delivery"
    assert "same-day or next-day" in experience["eta"].lower()


def test_delivery_experience_marks_known_delhi_ncr_city_and_postal_code_as_eligible():
    experience = get_delhi_ncr_delivery_experience(city="Gurgaon", postal_code="122002")

    assert experience["status"] == "eligible"
    assert experience["matched_city"] == "Gurugram"
    assert experience["normalized_postal_code"] == "122002"
    assert experience["is_express_zone"] is True


def test_delivery_experience_marks_city_and_out_of_zone_postal_code_as_conflict():
    experience = get_delhi_ncr_delivery_experience(city="Delhi", postal_code="560001")

    assert experience["status"] == "city_conflict"
    assert experience["is_express_zone"] is False
    assert "outside our usual delhi ncr express range" in experience["headline"].lower()
