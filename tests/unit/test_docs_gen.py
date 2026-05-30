from pca.docs_gen import contract_to_markdown, registry_index_markdown


def test_markdown_renders(registry) -> None:
    c = registry.resolve("customer.create")
    md = contract_to_markdown(c)
    assert "customer.create" in md
    assert "Input" in md and "Output" in md
    idx = registry_index_markdown(registry.list())
    assert "Contract Reference" in idx
    assert "customer.create" in idx
