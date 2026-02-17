from openclaw_memory_bench.adapters.milady_memory import MiladyMemoryAdapter


def test_initialize_defaults_gateway_namespace_to_milady() -> None:
    adapter = MiladyMemoryAdapter()
    adapter.initialize({})
    assert adapter.gateway_namespace == "milady"


def test_initialize_preserves_explicit_gateway_namespace_override() -> None:
    adapter = MiladyMemoryAdapter()
    adapter.initialize({"gateway_namespace": "openclaw"})
    assert adapter.gateway_namespace == "openclaw"
