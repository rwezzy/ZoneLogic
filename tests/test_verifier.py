from narrate.verifier import verify_claim

def test_confirmed():
    assert verify_claim("A person walks to the door", [{"class": "person", "confidence": .9}]).status == "confirmed"

def test_unconfirmed():
    v = verify_claim("A dog and a person", [{"class": "person", "confidence": .9}])
    assert v.status == "unconfirmed" and v.missing == ["dog"]

def test_low_conf_ignored():
    assert verify_claim("A car stops", [{"class": "car", "confidence": .1}]).status == "unconfirmed"

def test_unverifiable():
    assert verify_claim("It is quiet", []).status == "unverifiable"
