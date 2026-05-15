from hypothesis import given, example, strategies as st

@example(processed_count=0, failed_count=10)
@example(processed_count=4, failed_count=6)
@example(processed_count=9, failed_count=1)
@given(processed_count=st.integers(), failed_count=st.integers())
def test_ai_extractor_mid_batch_failure_saves_bundles(processed_count, failed_count):
    ...

