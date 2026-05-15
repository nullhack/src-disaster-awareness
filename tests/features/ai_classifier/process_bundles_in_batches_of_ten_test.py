from hypothesis import given, example, strategies as st

@example(bundle_count=0, batch_count=0)
@example(bundle_count=10, batch_count=1)
@example(bundle_count=23, batch_count=3)
@example(bundle_count=11, batch_count=2)
@given(bundle_count=st.integers(), batch_count=st.integers())
def test_ai_classifier_batch_size_processing(bundle_count, batch_count):
    ...

