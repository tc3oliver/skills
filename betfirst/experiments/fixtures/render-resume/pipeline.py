"""Build the timeline. Rendering can fail between individual segments."""


def build_timeline(segments, manifest, render):
    for segment in segments:
        key = segment.title
        if not manifest.is_complete(key):
            artifact = render(segment)
            manifest.commit(key, artifact)
    return [manifest.read(segment.title) for segment in segments]
