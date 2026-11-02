# Making a release

Manual steps to cut a release

With the workflows now in place, the pipeline is almost fully automated. The manual work is described below.

## Per-release steps

1. Label every pull request with one of the release-category labels (breaking-change, new-feature, bugfix, enhancement, refactor, performance, maintenance, ci, dependencies, documentation). The PR Labels workflow blocks merging without one. Add major or minor if you want to override the version bump; by default breaking-change bumps major, new-feature bumps minor, everything else bumps patch.
2. Merge to main. Release Drafter then automatically creates or updates a draft release named vX.Y.Z with the changes grouped by category. Nothing to do here.
3. Review the draft under Releases: check the resolved version, adjust the tag if needed (it must start with v, since the workflow strips that prefix), and tidy the notes.
4. Publish the release by selecting Publish release on the draft. This is the only real trigger: it creates the git tag.

What you never do by hand:
- Writing release notes from scratch.
