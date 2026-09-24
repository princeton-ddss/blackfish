# Contributing Guidelines

Blackfish is happy to consider contributions from the research community. **All contributions are welcome as long as everyone involved is treated with respect.**

## Code Contributions

For advice on setting up your development environment, see our [Developer Guide](../developer/index.md).

### Steps

1. **Start from an issue.** For anything beyond a small fix, open an issue
   first, or comment on an existing one, so we can agree on the approach
   before you write code — see [Early Feedback](#early-feedback).
2. **Fork the repository and create a branch.** Give it a descriptive name
   (e.g. `feature/support-hdf5-files`). Maintainers with write access can
   branch directly from the issue instead of forking.
3. **Set up your environment.** The [Developer Guide](../developer/index.md)
   covers installation and the `pre-commit` hooks. Install the hooks — the
   same checks run on every PR, so skipping them usually means a failed build.
4. **Write a test.** For a bug, write one that fails before your fix. For a
   feature, write enough to show it works.
5. **Implement your change.** Don't be afraid to ask for help or advice.
6. **Open a pull request against `main`.** If it closes an issue, say so in
   the description (e.g. "Closes #78").

!!! tip "Before you open the PR"

    [`CONTRIBUTING.md`](https://github.com/princeton-ddss/blackfish/blob/main/CONTRIBUTING.md)
    in the repository root has the full pre-flight checklist — tests, linting,
    and the release steps for maintainers.

### Code Review

In addition to passing automated tests, PRs must pass code review before they are merged. Feedback will include optional changes and required changes. Required changes must be addressed in order for the PR to be merged. If you disagree with required changes, you can argue your position respectfully, but understand that maintainers have the final say.

#### Early Feedback

Getting early feedback is one way to avoid wasted effort and disappointment. There are two ways to request feedback on your ideas. First, you can create an issue describing the bug you wish to fix or feature that you want to contribute. This is a good option if you are not sure about how to approach the issue and want to avoid heading down the wrong path. The other option is to open a draft PR. This option works well if you know what you're doing (you have an implementation of some sort), but would like a second opinion before you get too far.

### Code Style

Code style and formatting (linting) is enforced by `ruff` and included in the repository's `pre-commit` configuration. The same `pre-commit` hooks are run automatically on all PRs, so developers should install `pre-commit` to avoid unnecessary failed GitHub Actions.

#### Docstrings

Provide docstrings for functions, methods, and classes for which the behavior is not obvious. We try to follow the docstring formatting rules from the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

### Type Hints

Inclusion of type hints is checked by `mypy` as part of our `pre-commit` and GitHub Actions configuration.

## Documentation Contributions

Improving documentation is a great way to contribute to Blackfish.

For a typo or a small correction, use the edit icon at the top of any page. It
opens that page on GitHub and forks the repository for you — so the whole
change happens in the browser, without cloning anything.

For anything larger, the documentation lives in `lib/docs/` and is built with
[Zensical](https://zensical.org/). Preview your changes by running
`just docs-serve` from `lib/`.

## Bug Reports

We encourage users to report bugs by creating an issue on GitHub and labeling it as a bug fix. Before raising an issue, please check for duplicate issues.

## Feature Requests

Please let us know if you think Blackfish is missing an important feature by creating an issue on GitHub and labeling it as a feature request.
