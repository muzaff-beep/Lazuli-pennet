# CI Packaging Fix Applied

This development repository snapshot includes the setuptools package-discovery fix for the GitHub Actions failure:

`Multiple top-level packages discovered in a flat-layout`

Applied configuration:

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["lazulinet*", "lazulinet_gui*"]
exclude = ["modules*", "android*", "debian*", "tests*"]
```

The live GitHub repository was observed at commit `9fcf5da11b0416471f1ac570dab1db3ea6e14f2f` when the CI failure was inspected. The connected GitHub app is read-only, so this ZIP is provided as a local fixed development snapshot rather than a pushed commit.
