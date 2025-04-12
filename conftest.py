import pytest

def pytest_collection_modifyitems(config, items):
    skip = pytest.mark.skip(reason="Fallan temporalmente solo porque ya no tenemos configurado azure")
    
    for item in items:
        if "azure" in item.keywords:
            item.add_marker(skip)