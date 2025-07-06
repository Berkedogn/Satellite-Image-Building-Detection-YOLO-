import cv2
import os
from config import OUTPUT_FOLDER, CONFIDENCE_THRESHOLD


def draw_boxes_with_id(image_path, results, model):
    """
    Draw bounding boxes with ID, class name, and confidence on the image.

    Args:
        image_path (str): Path to the input image.
        results (list): List of inference results from the model.
        model: The YOLO model instance (to get class names).

    Returns:
        str: Path to the output image with boxes drawn.
    """
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Iterate through each detection result
    for r in results:
        if r.boxes is None:
            continue

        boxes = r.boxes.xyxy.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy()
        confidences = r.boxes.conf.cpu().numpy()

        # Enumerate to get an ID for each bbox
        for idx, (box, cls_id, conf) in enumerate(zip(boxes, classes, confidences), start=1):
            if conf < CONFIDENCE_THRESHOLD:
                continue

            x1, y1, x2, y2 = map(int, box)
            label = f"{idx}: {model.names[int(cls_id)]} ({conf:.2f})"

            # Draw rectangle
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Calculate text size
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            # Draw background for text
            cv2.rectangle(img, (x1, y1 - th - 4), (x1 + tw, y1), (0, 255, 0), -1)
            # Put text (ID: Class (conf))
            cv2.putText(img, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    # Ensure output folder exists
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    output_path = os.path.join(OUTPUT_FOLDER, "detected_with_id.jpg")
    cv2.imwrite(output_path, img)
    return output_path


def draw_boxes(image_path, results, model):
    """
    Legacy function: draw bounding boxes without IDs.
    """
    return draw_boxes_with_id(image_path, results, model)
