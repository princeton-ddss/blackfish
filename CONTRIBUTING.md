# Blackfish Contributing Guidelines

**All  contributions are welcome as long as everyone involved is treated with respect.**

## Code Contributions
For advice on setting up your development environment, see our [development guide](https://princeton-ddss.github.io/blackfish/contrib).

### Steps
1. Clone the repository and create a feature branch
If addressing an open issue, create a feature branch from the issue. Otherwise, give the feature branch a descriptive name (e.g., `support-hdf5-files`).
2. If fixing a bug, write a test and confirm that it fails (if possible)
3. Implement your fix or feature
4. If adding a feature, write appropriate tests (if possible)
Make sure `pre-commit` is installed. If not, your PR is *very* likely to fail.
5. Open a GitHub Pull Request to the `master` branch
If the PR closes an issue, make sure to note this in the description (i.e., "Closes #78").

### Code Review
In addition to passing automated tests, PRs must pass code review before they are merged. Feedback will include optional changes and required changes. Required changes must be addressed in order for the PR to be merged. If you disagree with required changes, you can argue your position respectfully, but understand that maintainers have the final say. Do not be discouraged or frustrated with reviewers. **Remember: feedback is a gif!**

![Feedback is a gif](https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExcmR4c2FmandtZzBkeW9lOGxzMnM0anB0MWdvMTFnNjZ2ZWo0N2N5dSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/ZF8GoFOeBDwHFsVYqt/giphy.gif)

#### Early Feedback
Speaking of feedback, getting early feedback is one way to avoid wasted effort and dissapointment. There are two ways to request feedback on your ideas. First, you can create an issue describing the issue you wish to resolve or feature that you want to contribute. This is a good option if you are not sure about how to approach the issue and want to avoid heading down the wrong path. The other option is to open a draft PR. This option works well if you know what you're doing (you have an implementation of some sort), but would like a second opinion before you get too far (remember the 90/10 rule!). Additionally, it means the maintainers have one less issue to worry about 😊


### Code Style
Code style (linting) and formatting is enforced by `ruff` and included in the repository's `pre-commit` configuration. The same `pre-commit` hooks are run automatically on all PR requests, so developers should install `pre-commit` to avoid unnecessary failed GitHub Actions.

#### Docstrings
Provide docstrings for functions, methods, and classes for which the behavior is not obvious. We try to follow the docstring formatting rules from the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

### Type Hints
Inclusion of type hints is checked by `mypy` as part of our `pre-commit` and GitHub Actions configuration.

## Documentation Contributions
Improving documentation is a great way to contribute to Blackfish. Our documentation is nearly always in need to attention. You'll find all our documentation in the `docs/` directory. We use [`mkdocs-material`](https://squidfunk.github.io/mkdocs-material/) for documentation. You can preview changes by installing all `dev` dependencies (`uv sync --dev`) and running `mkdocs serve`.

## Bug Reports
We encourage users to report bugs by creating an issue on GitHub and labeling it as a bug fix. Before raising an issue, please check for duplicate issues.

## Feature Requests
Please let us know if you think Blackfish is missing an important feature by creating an issue on GitHub and labeling it as a feature request.
