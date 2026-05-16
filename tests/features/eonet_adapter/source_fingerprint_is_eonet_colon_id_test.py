from disaster_surveillance_reporter.adapters.eonet import EONETAdapter


def test_eonet_record_fingerprint_format():
    adapter = EONETAdapter()
    fingerprint = adapter._compute_fingerprint("EONET_20104")
    assert fingerprint == "EONET:EONET_20104"
