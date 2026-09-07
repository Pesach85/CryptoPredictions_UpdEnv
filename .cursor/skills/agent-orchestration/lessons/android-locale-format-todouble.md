# Lesson: Android locale String.format → toDouble

Never round doubles via `String.format(...).toDouble()` — IT/EU locales emit `,` and crash (`For Input string: "1,130"`). Use `round(v * 10^d) / 10^d` or `String.format(Locale.US, ...)`.
