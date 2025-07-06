from ultralytics import YOLO
from config import MODEL_PATH

def load_model():
    return YOLO(MODEL_PATH)

def detect_objects(model, image_path):
    return model(image_path)