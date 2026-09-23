r"""
mcp-vision — Image/audio understanding wrappers (mock + real hooks).

Tools:
  classify_image(image_url, candidates)
  detect_objects(image_url, classes)
  transcribe_audio(audio_url, language)
  describe_image(image_url, prompt)
  ocr(image_url)
  similarity(images)
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


def _mock_prob(target: str, seed: str) -> float:
    h = hashlib.sha256(f"{seed}-{target}".encode()).digest()
    return round((h[0] / 255.0) * 0.6 + 0.3, 3)


server = Server(name="mcp-vision", version="1.0.0", title="Vision & Audio AI", description="Image classification, object detection, OCR, audio transcription.")


@server.tool(description="Classify an image against candidate labels")
def classify_image(image_url: str, candidates: list) -> dict:
    scores = [{"label": c, "score": _mock_prob(c, image_url)} for c in candidates]
    scores.sort(key=lambda x: -x["score"])
    return {"top": scores[0], "scores": scores}


@server.tool(description="Detect objects in an image (returns bounding boxes)")
def detect_objects(image_url: str, classes: list) -> dict:
    detections = []
    for i, c in enumerate(classes):
        detections.append({
            "label": c,
            "score": _mock_prob(c, image_url),
            "box": {"x": i * 100, "y": i * 80, "w": 80, "h": 80},
        })
    detections.sort(key=lambda x: -x["score"])
    return {"detections": detections, "count": len(detections)}


@server.tool(description="Transcribe audio (mock)")
def transcribe_audio(audio_url: str, language: str = "en") -> dict:
    seed = hashlib.sha256(audio_url.encode()).hexdigest()[:8]
    text = f"[mock transcript for {seed} in {language}] lorem ipsum dolor sit amet"
    return {"text": text, "language": language, "duration_s": 12.5}


@server.tool(description="Describe an image (visual question answering)")
def describe_image(image_url: str, prompt: str = "Describe this image") -> dict:
    h = hashlib.sha256(image_url.encode()).hexdigest()[:12]
    return {"description": f"Image {h}: {prompt} — caption contains objects, lighting, mood.", "prompt": prompt}


@server.tool(description="OCR — extract text from an image")
def ocr(image_url: str) -> dict:
    h = hashlib.sha256(image_url.encode()).hexdigest()
    return {"text": f"OCR text {h[:16]}…", "confidence": 0.92, "lines": 3}


@server.tool(description="Compute similarity between multiple images")
def similarity(images: list) -> dict:
    import math
    pairs = []
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            seed = hashlib.sha256(f"{images[i]}-{images[j]}".encode()).hexdigest()
            sim = round((int(seed[:4], 16) % 1000) / 1000.0, 3)
            pairs.append({"a": images[i], "b": images[j], "similarity": sim})
    return {"pairs": pairs, "count": len(pairs)}


if __name__ == "__main__":
    server.run()