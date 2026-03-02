from flask import Flask, render_template, request
import os
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads/"
RESULT_FOLDER = "static/results/"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# --------- Resize Image ----------
def resize_image(image, size=(512, 512)):
    return cv2.resize(image, size)


# --------- Patch Creation ----------
def create_patches(image, patch_size=32):
    patches = []
    h, w, _ = image.shape
    for i in range(0, h, patch_size):
        for j in range(0, w, patch_size):
            patch = image[i:i+patch_size, j:j+patch_size]
            patches.append((patch, i, j))
    return patches


# --------- Simple Feature Extraction ----------
def compute_features(patch):
    # Green ratio (vegetation proxy)
    green = np.mean(patch[:, :, 1])
    # Brightness (built-up density proxy)
    brightness = np.mean(cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY))
    return green, brightness


# --------- Rule-Based Classification ----------
def classify_patch(green, brightness):
    if brightness > 150 and green < 80:
        return 2  # High Risk
    elif brightness > 100:
        return 1  # Medium
    else:
        return 0  # Low


# --------- Generate Vulnerability Map ----------
def generate_map(image):
    low = 0
    medium = 0
    high = 0
    image = resize_image(image)
    patches = create_patches(image)

    result_map = np.zeros((512, 512, 3), dtype=np.uint8)

    for patch, i, j in patches:
        green, brightness = compute_features(patch)
        risk = classify_patch(green, brightness)

        if risk == 2:
            color = [0, 0, 255]# Red = High
            high +=1
        elif risk == 1:
            color = [0, 165, 255]  # Orange = Medium
            medium+=1
        else:
            color = [0, 255, 0]  # Green = Low
            low+=1

        result_map[i:i+32, j:j+32] = color
        total = low + medium + high
        stats = {
            "low": round((low/total)*100, 2),
            "medium": round((medium/total)*100, 2),
            "high": round((high/total)*100, 2)
        }
    return result_map,stats


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files["image"]
        path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(path)

        image = cv2.imread(path)
        result,stats = generate_map(image)

        result_path = os.path.join(RESULT_FOLDER, "output.png")
        cv2.imwrite(result_path, result)

        return render_template("index.html",
                               uploaded_image=path,
                               result_image=result_path,
                               stats=stats)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)