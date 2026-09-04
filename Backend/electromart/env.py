"""Load the project's .env file into os.environ.

settings.py reads every setting with os.environ.get(), but nothing was
actually putting the .env file into the environment - so the values in .env
(SECRET_KEY, the SMTP credentials, ...) were silently ignored and only the
hard-coded defaults were ever used. This module closes that gap.

Written against the standard library on purpose: no extra pip package, so a
teammate who has not re-run `pip install -r requirements.txt` can still start
the server.

A real environment variable always wins over the file, which is what a
deployment needs: Render/Railway inject their own values and must not be
overridden by a .env that happens to be in the image.
"""
import os


def load_env(path, override=False):
    """Parse a KEY=VALUE file and merge it into os.environ.

    Returns the list of keys taken from the file. A missing file is not an
    error - the defaults in settings.py are meant to work on their own.
    """
    if not os.path.exists(path):
        return []

    loaded = []
    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            # Blank lines, comments, and the "export KEY=..." style some
            # shells use are all tolerated.
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[len('export '):].lstrip()
            if '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            # An app password may legitimately contain spaces, so only strip
            # quotes that wrap the whole value.
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if not key:
                continue
            if override or key not in os.environ:
                os.environ[key] = value
                loaded.append(key)
    return loaded
