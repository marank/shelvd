from apps.providers.services import gtin


def test_normalize() -> None:
    assert gtin.normalize("045496 598976") == "0045496598976"  # UPC-A → GTIN-13
    assert gtin.normalize("4006381333931") == "4006381333931"
    assert gtin.normalize("96385074") == "96385074"  # EAN-8
    assert gtin.normalize("4006381333932") is None  # wrong check digit
    assert gtin.normalize("123") is None
    assert gtin.normalize("") is None


def test_normalize_code() -> None:
    assert gtin.normalize_code(" 045496 598976") == "0045496598976"
    assert gtin.normalize_code("4006381333932") is None  # GTIN digits, wrong check digit
    assert gtin.normalize_code("1836540t") == "1836540T"  # article number
    assert gtin.normalize_code("NTR-IPKD-NOE") == "NTR-IPKD-NOE"
    assert gtin.normalize_code("123") is None
    assert gtin.normalize_code("a b?c") is None
