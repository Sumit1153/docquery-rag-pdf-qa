import math
import pytest
from app.repository import SCHEMA, as_vector


def test_3072_dimensions():
    data = as_vector([0.5] * 3072)
    assert data.startswith("[0.5,0.5,") and data.endswith("]")
    assert data.count(",") == 3071


def test_wrong_vector_dimensions():
    with pytest.raises(ValueError, match="3072"):
        as_vector([0.1] * 4)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_rejected(bad):
    with pytest.raises(ValueError, match="non-finite"):
        as_vector([bad] + [0.0] * 3071)


def test_schema_has_vector_and_page_metadata():
    assert "VECTOR(3072)" in SCHEMA
    assert "page_number INTEGER" in SCHEMA
    assert "ON DELETE CASCADE" in SCHEMA
