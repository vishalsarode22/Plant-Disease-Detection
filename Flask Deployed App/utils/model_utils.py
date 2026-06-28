# utils/model_utils.py

import torch
import torchvision.transforms.functional as TF
import pandas as pd
from PIL import Image
import sys
import os

# Add parent folder to path so CNN.py can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import CNN

# ==============================
# CONFIDENCE THRESHOLD
# ==============================
CONFIDENCE_THRESHOLD = 0.70

# ==============================
# CLASS LABELS
# ==============================
IDX_TO_CLASS = {
    0:  'Apple - Apple Scab',
    1:  'Apple - Black Rot',
    2:  'Apple - Cedar Apple Rust',
    3:  'Apple - Healthy',
    4:  'Background (No Leaf)',
    5:  'Blueberry - Healthy',
    6:  'Cherry - Powdery Mildew',
    7:  'Cherry - Healthy',
    8:  'Corn - Cercospora Leaf Spot',
    9:  'Corn - Common Rust',
    10: 'Corn - Northern Leaf Blight',
    11: 'Corn - Healthy',
    12: 'Grape - Black Rot',
    13: 'Grape - Esca (Black Measles)',
    14: 'Grape - Leaf Blight',
    15: 'Grape - Healthy',
    16: 'Orange - Huanglongbing (Citrus Greening)',
    17: 'Peach - Bacterial Spot',
    18: 'Peach - Healthy',
    19: 'Pepper Bell - Bacterial Spot',
    20: 'Pepper Bell - Healthy',
    21: 'Potato - Early Blight',
    22: 'Potato - Late Blight',
    23: 'Potato - Healthy',
    24: 'Raspberry - Healthy',
    25: 'Soybean - Healthy',
    26: 'Squash - Powdery Mildew',
    27: 'Strawberry - Leaf Scorch',
    28: 'Strawberry - Healthy',
    29: 'Tomato - Bacterial Spot',
    30: 'Tomato - Early Blight',
    31: 'Tomato - Late Blight',
    32: 'Tomato - Leaf Mold',
    33: 'Tomato - Septoria Leaf Spot',
    34: 'Tomato - Spider Mites',
    35: 'Tomato - Target Spot',
    36: 'Tomato - Yellow Leaf Curl Virus',
    37: 'Tomato - Mosaic Virus',
    38: 'Tomato - Healthy',
}


def load_model():
    """
    Load the CNN model and CSV files.
    Returns: (model, disease_info, supplement_info)
    """
    try:
        disease_info    = pd.read_csv('disease_info.csv',    encoding='cp1252')
        supplement_info = pd.read_csv('supplement_info.csv', encoding='cp1252')
    except FileNotFoundError as e:
        print(f"[WARNING] CSV file not found: {e}")
        disease_info    = None
        supplement_info = None

    try:
        model = CNN.CNN(39)
        model.load_state_dict(
            torch.load(
                "plant_disease_model_1_latest.pt",
                map_location=torch.device('cpu')
            )
        )
        model.eval()
        print("[INFO] Model loaded successfully.")
    except Exception as e:
        print(f"[WARNING] Could not load model: {e}")
        model = None

    return model, disease_info, supplement_info


def predict_disease(image_path, model):
    """
    Predict disease from a leaf image.

    Steps:
      1. Open and resize image to 224x224
      2. Convert to tensor
      3. Run through model
      4. Apply softmax to get probabilities
      5. Get highest probability (confidence)
      6. If confidence < threshold  →  Unknown Plant
      7. If class == 4 (background) →  Unknown Plant
      8. Otherwise → return predicted label

    Returns:
      label       (str)   - predicted class name or 'Unknown Plant'
      confidence  (float) - score between 0.0 and 1.0
      is_unknown  (bool)  - True if plant is not in dataset
    """

    # Step 1: Preprocess image
    image = Image.open(image_path).convert('RGB').resize((224, 224))
    input_tensor = TF.to_tensor(image).unsqueeze(0)   # [1, 3, 224, 224]

    # Step 2: Guard if model not loaded
    if model is None:
        print("[WARNING] Model not loaded. Returning Unknown.")
        return 'Unknown Plant', 0.0, True

    # Step 3: Run inference
    with torch.no_grad():
        output       = model(input_tensor)                        # raw logits
        probs        = torch.softmax(output, dim=1)               # probabilities
        confidence, pred_idx = torch.max(probs, dim=1)           # top prediction

    confidence = confidence.item()    # tensor → float
    pred_index = pred_idx.item()      # tensor → int

    # Step 4: Debug log (visible in terminal)
    raw_label = IDX_TO_CLASS.get(pred_index, 'Unknown')
    print("=" * 45)
    print(f"[DEBUG] Raw Predicted Class : {pred_index} → {raw_label}")
    print(f"[DEBUG] Confidence Score    : {confidence * 100:.2f}%")
    print(f"[DEBUG] Threshold           : {CONFIDENCE_THRESHOLD * 100:.0f}%")
    print("=" * 45)

    # Step 5: Background / no-leaf image
    if pred_index == 4:
        print("[RESULT] Background detected → Unknown Plant")
        return 'Unknown Plant', confidence, True

    # Step 6: Confidence too low → plant not in dataset
    if confidence < CONFIDENCE_THRESHOLD:
        print(f"[RESULT] Low confidence → Unknown Plant")
        return 'Unknown Plant', confidence, True

    # Step 7: Valid prediction
    print(f"[RESULT] Detected: {raw_label} at {confidence*100:.2f}%")
    return raw_label, confidence, False
