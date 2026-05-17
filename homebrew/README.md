# Homebrew tap for dotpanel

To install dotpanel via Homebrew:

```bash
brew tap hioTEC/dotpanel
brew install dotpanel
dot init
```

## Manual tap setup

If you haven't published this formula to a tap repo yet:

```bash
# From a local checkout:
brew install --build-from-source --formula ./homebrew/dotpanel.rb
```

## Publishing the tap

Create a new public repo on GitHub named `homebrew-dotpanel`, then:

```bash
mkdir homebrew-dotpanel
cp homebrew/dotpanel.rb homebrew-dotpanel/Formula/dotpanel.rb
cd homebrew-dotpanel
git init && git add . && git commit -m "Add dotpanel formula"
gh repo create hioTEC/homebrew-dotpanel --public --push --source .
```

After that, users can `brew tap hioTEC/dotpanel && brew install dotpanel`.
