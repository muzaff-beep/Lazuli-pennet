# CI fix: python-for-Android release ref

Observed failure:

```text
git clone -b develop --single-branch https://github.com/kivy/python-for-android.git
git reset --hard 58d21141f17c889bf8585f5665921d72028f8831
fatal: Could not parse object '58d21141f17c889bf8585f5665921d72028f8831'.
```

The release commit belongs to the `v2026.05.09` release tag. Buildozer's
single-ref checkout therefore must clone that release ref, not `develop`.

Correct configuration:

```ini
p4a.branch = v2026.05.09
p4a.commit = 58d21141f17c889bf8585f5665921d72028f8831
```

This retains exact commit pinning while making the commit available to the
Buildozer checkout.
