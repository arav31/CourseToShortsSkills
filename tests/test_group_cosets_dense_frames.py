import os
import shutil
import subprocess
import unittest
from pathlib import Path


WIDTH = 270
HEIGHT = 480


def decoded_gray_frames(video: Path, start: float, end: float) -> list[bytes]:
    command = [
        shutil.which("ffmpeg") or "ffmpeg",
        "-v", "error", "-i", str(video),
        "-vf", f"trim=start={start}:end={end},setpts=PTS-STARTPTS,scale={WIDTH}:{HEIGHT},format=gray",
        "-fps_mode", "passthrough", "-f", "rawvideo", "-",
    ]
    payload = subprocess.run(command, check=True, capture_output=True).stdout
    frame_size = WIDTH * HEIGHT
    if len(payload) % frame_size:
        raise AssertionError("ffmpeg returned an incomplete decoded frame")
    return [payload[offset : offset + frame_size] for offset in range(0, len(payload), frame_size)]


def active_pixels(frame: bytes, region: tuple[int, int, int, int]) -> int:
    left, top, right, bottom = region
    return sum(
        frame[y * WIDTH + x] >= 52
        for y in range(top, bottom)
        for x in range(left, right)
    )


class CosetsDenseFrameRetentionTests(unittest.TestCase):
    def test_every_critical_window_frame_retains_persistent_regions(self) -> None:
        configured = os.environ.get("GROUP_COSETS_RENDER", "").strip()
        if not configured:
            self.skipTest("set GROUP_COSETS_RENDER to validate a production Cosets MP4")
        video = Path(configured)
        self.assertTrue(video.is_file(), video)
        regions = {
            "title": (102, 17, 168, 42),
            "canonical_formula": (18, 54, 252, 80),
            "subgroup_formula": (76, 143, 194, 179),
            "first_coset_row": (62, 219, 210, 256),
        }
        for start, end in ((17.5, 18.5), (34.5, 36.0)):
            frames = decoded_gray_frames(video, start, end)
            self.assertGreaterEqual(len(frames), round((end - start) * 30) - 1)
            for name, region in regions.items():
                counts = [active_pixels(frame, region) for frame in frames]
                reference = max(counts)
                self.assertGreater(reference, 20, f"{name} has no readable foreground")
                minimum = min(counts)
                self.assertGreaterEqual(
                    minimum,
                    reference * 0.72,
                    f"{name} lost persistent pixels in {start:.1f}-{end:.1f}s: {minimum}/{reference}",
                )


if __name__ == "__main__":
    unittest.main()
