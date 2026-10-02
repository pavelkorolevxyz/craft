# Video and images

## Video

A recording uses `screenshot` like an image: `<video class="media-cover">` in `.shot`. If the top left title covers what matters, use `.s-shot--title-center`.

`media.js` loads after `deck.js` and runs every video. `data-media` sets the role:

| Role | Behavior |
|---|---|
| `demo` (default) | Restarts on entering the slide, keeps its position across its reveals |
| `scene` | Shared scene background: pages with the same `data-scene` continue one position |
| `manual` | Does not start on its own, keeps `controls` |

Options: `loop`, `data-playback-rate`, `data-rewind` (back to the start after the end), `data-sound`. Only the open page's video plays; a blocked one retries on the next gesture. Every video needs a `poster` and `preload="none"`.

Preload radius on `.deck`: `data-prewarm-images` (3 pages), `data-prewarm-videos` (1), `data-release-videos` (4, then a video is released).

## Images and cropping

An image starts at the left edge of the text area. A frame with `.media-contain` takes the image's aspect ratio. Mark a photo crop with `data-crop` on the container. Mark a window where text is meant to show only partly with `data-clip="intended"`. Without a mark, the check treats cropping as an error.
