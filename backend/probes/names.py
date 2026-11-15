"""The plain name of a label, shown wherever its key would be. One rule for the probe pack and
for the review, so a probe and the technique it flags carry the same name."""


def plain_name(key: str) -> str:
    """`fear_appeal` reads "Fear appeal"; one answer of a label, `theme:sport`, "Theme: sport"."""
    name, _, value = key.partition(":")
    label = name.replace("_", " ").capitalize()
    return f"{label}: {value.replace('_', ' ')}" if value else label
