"""المتتبع: يلف MediaPipe HandLandmarker ويرجع نقاط اليد بالبكسل."""
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from . import MODEL_PATH
from .camera import CameraError

vision = mp.tasks.vision


@dataclass
class Hand:
    landmarks: list  # 21 نقطة [x, y, z] بالبكسل (x و y بنفس المقياس)
    handedness: str  # "Left" أو "Right"
    score: float     # ثقة النموذج إنها يد (0 إلى 1)


class HandTracker:
    def __init__(self, model_path: Path = MODEL_PATH, num_hands: int = 2):
        if not Path(model_path).exists():
            raise CameraError("NO_MODEL")
        options = vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,  # VIDEO: يستفيد من الإطار السابق فيصير أسرع
            num_hands=num_hands,
        )
        self._lm = vision.HandLandmarker.create_from_options(options)
        self._last_ts = -1

    def process(self, frame_bgr: np.ndarray, timestamp_ms: int) -> list[Hand]:
        h, w = frame_bgr.shape[:2]
        # MediaPipe يريد الوقت دايماً يتزايد، فنضمن هذا
        ts = max(timestamp_ms, self._last_ts + 1)
        self._last_ts = ts
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)  # OpenCV يعطي BGR، والنموذج يريد RGB
        result = self._lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
        hands = []
        for lms, handed in zip(result.hand_landmarks, result.handedness):
            pts = [[p.x * w, p.y * h, p.z * w] for p in lms]
            hands.append(Hand(pts, handed[0].category_name, handed[0].score))
        return hands

    def close(self) -> None:
        self._lm.close()
