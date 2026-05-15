from hypothesis import given, example, strategies as st

@example(processed_count=4)
@example(processed_count=7)
@example(processed_count=0)
@example(processed_count=9)
@given(processed_count=st.integers())
def test_ai_classifier_mid_batch_failure_recovery(processed_count):
    ...

