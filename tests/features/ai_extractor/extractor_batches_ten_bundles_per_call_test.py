from hypothesis import given, example, strategies as st

@example(bundle_count=0, expected_calls=0)
@example(bundle_count=7, expected_calls=1)
@example(bundle_count=10, expected_calls=1)
@example(bundle_count=11, expected_calls=2)
@example(bundle_count=20, expected_calls=2)
@example(bundle_count=28, expected_calls=3)
@given(bundle_count=st.integers(), expected_calls=st.integers())
def test_ai_extractor_batches_bundles_per_call(bundle_count, expected_calls):
    ...

