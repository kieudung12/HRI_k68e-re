"""DeepFace dò mặt; EfficientNet-B2 hoặc DeepFace Emotion phân loại biểu cảm."""

import hashlib
import os
from pathlib import Path
import urllib.request

os.environ['DEEPFACE_BACKEND_ENGINE'] = 'onnx'
MODEL_REVISION = '520a051c64cd191521e5934655314e769a319684'
MODEL_URL = (f'https://raw.githubusercontent.com/sb-ai-lab/EmotiEffLib/{MODEL_REVISION}/'
             'models/affectnet_emotions/onnx/enet_b2_7.onnx')
MODEL_SHA256 = '7863032d8c0c0bc259aa0dd7b8ebf6b607af454e7a0ea82be2b37767914ecd0f'
LABELS = ('angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise')


def download_model():
    workspace = Path(os.environ.get('B8_WS', Path(__file__).resolve().parents[3]))
    path = workspace / 'models' / 'enet_b2_7.onnx'
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == MODEL_SHA256:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.onnx.part')
    print('Dang tai model bieu cam EfficientNet-B2 (~30 MB)...', flush=True)
    with urllib.request.urlopen(MODEL_URL, timeout=60) as response, temporary.open('wb') as target:
        while chunk := response.read(1024 * 1024):
            target.write(chunk)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != MODEL_SHA256:
        raise RuntimeError('Model tai chua day du / sai checksum. Chay lai bash setup.sh.')
    temporary.replace(path)
    return path


class Recognizer:
    def __init__(self, detector='opencv', classifier='hsemotion'):
        import cv2
        from deepface import DeepFace

        self.detector, self.classifier, self.deepface = detector, classifier, DeepFace
        cv2.setNumThreads(2)
        if classifier == 'hsemotion':
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = 4
            self.session = ort.InferenceSession(str(download_model()), sess_options=options,
                                                providers=['CPUExecutionProvider'])
        elif classifier == 'deepface':
            DeepFace.build_model(model_name='Emotion', task='facial_attribute')
        else:
            raise ValueError('classifier phải là hsemotion hoặc deepface')
        if detector == 'retinaface':
            from retinaface import RetinaFace
            RetinaFace.build_model()

    def analyze(self, frame):
        import cv2
        import numpy as np

        try:
            faces = self.deepface.extract_faces(
                frame, detector_backend=self.detector, enforce_detection=True,
                align=True, color_face='rgb', normalize_face=False)
        except ValueError as error:
            if 'Face could not be detected' in str(error):
                return None
            raise
        if not faces:
            return None
        face = max(faces, key=lambda f: f['facial_area']['w'] * f['facial_area']['h'])
        crop, region = face['face'], face['facial_area']
        if min(region['w'], region['h']) < 70:
            return {'region': region, 'emotion': None, 'small_face': True}
        if self.classifier == 'hsemotion':
            # Theo tiền xử lý HSEmotion: RGB 260x260, chuẩn hóa ImageNet, HWC -> NCHW.
            # Nguồn và giấy phép: THIRD_PARTY.md.
            image = cv2.resize(crop, (260, 260)).astype(np.float32) / 255.0
            image = (image - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
                [0.229, 0.224, 0.225], dtype=np.float32)
            batch = image.transpose(2, 0, 1)[None].astype(np.float32)
            logits = self.session.run(None, {self.session.get_inputs()[0].name: batch})[0][0]
            probabilities = np.exp(logits - logits.max())
            probabilities /= probabilities.sum()
            scores = {label: float(value * 100) for label, value in zip(LABELS, probabilities)}
        else:
            prediction = self.deepface.analyze(
                cv2.cvtColor(crop.astype(np.uint8), cv2.COLOR_RGB2BGR),
                actions=['emotion'], detector_backend='skip', align=False, silent=True)[0]
            scores = {key: float(value) for key, value in prediction['emotion'].items()}
        return {'region': region, 'emotion': scores,
                'dominant_emotion': max(scores, key=scores.get),
                'brightness': float(cv2.cvtColor(crop.astype(np.uint8), cv2.COLOR_RGB2GRAY).mean())}


if __name__ == '__main__':
    print('Model san sang:', download_model())
