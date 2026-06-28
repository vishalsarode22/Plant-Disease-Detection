import os
import uuid
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv

load_dotenv()

from utils.model_utils import load_model, predict_disease
from utils.db_utils import init_db, save_prediction, get_history
from utils.gemini_utils import get_gemini_insights

# ==============================
# APP CONFIG
# ==============================
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE_MB = 5

app = Flask(__name__)
app.secret_key = 'leafmitra-secret-2024'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_MB * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==============================
# INIT MODEL + DB
# ==============================
model, disease_info, supplement_info = load_model()
init_db()

# ==============================
# HELPER
# ==============================
def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# ==============================
# ROUTES
# ==============================

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/predict', methods=['POST'])
def predict():

    if 'image' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('home'))

    file = request.files['image']

    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('home'))

    if not allowed_file(file.filename):
        flash('Only JPG, JPEG, PNG allowed.', 'error')
        return redirect(url_for('home'))

    # Save image
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Validate image
    try:
        img = Image.open(filepath)
        img.verify()
    except Exception:
        os.remove(filepath)
        flash('Invalid image file.', 'error')
        return redirect(url_for('home'))

    # Prediction
    try:
        label, confidence, is_unknown = predict_disease(filepath, model)
    except Exception as e:
        flash(f'Prediction error: {str(e)}', 'error')
        return redirect(url_for('home'))

    # ==============================
    # DISEASE / SUPPLEMENT INFO
    # ==============================
    d_info = None
    s_info = None

    if (disease_info is not None and hasattr(disease_info, "empty") and not disease_info.empty):

        from utils.model_utils import IDX_TO_CLASS

        pred_index = None
        for idx, lbl in IDX_TO_CLASS.items():
            if lbl == label:
                pred_index = idx
                break

        if pred_index is not None:
            try:
                d_info = {
                    'disease_name': disease_info['disease_name'][pred_index],
                    'description':  disease_info['description'][pred_index],
                    'steps':        disease_info['Possible Steps'][pred_index],
                    'image_url':    disease_info['image_url'][pred_index],
                }

                if (supplement_info is not None and hasattr(supplement_info, "empty") and not supplement_info.empty):
                    s_info = {
                        'name':     supplement_info['supplement name'][pred_index],
                        'image':    supplement_info['supplement image'][pred_index],
                        'buy_link': supplement_info['buy link'][pred_index],
                    }

            except Exception as e:
                print(f"[WARN] Info mapping issue: {e}")

    # ==============================
    # GEMINI AI INSIGHTS
    # ==============================
    gemini = None
    try:
        gemini = get_gemini_insights(
            label      = label,
            confidence = confidence,        # raw 0.0–1.0 float
            is_unknown = is_unknown,
            image_path = filepath if is_unknown else None,
        )
    except Exception as e:
        print(f"[WARN] Gemini failed: {e}")

    # ==============================
    # SAVE TO HISTORY
    # ==============================
    save_prediction(
        image_path  = filename,
        label       = label,
        confidence  = round(confidence * 100, 2),
        is_unknown  = is_unknown,
        gemini_text = gemini['raw'] if gemini else '',
    )

    return render_template(
        'result.html',
        image_filename = filename,
        label          = label,
        confidence     = round(confidence * 100, 2),
        is_unknown     = is_unknown,
        d_info         = d_info,
        s_info         = s_info,
        gemini         = gemini,
    )


# ==============================
# ABOUT
# ==============================
@app.route('/about')
def about():
    return render_template('about.html')


# ==============================
# HISTORY
# ==============================
@app.route('/history')
def history():
    records = get_history(limit=20)
    return render_template('history.html', records=records)


# ==============================
# MARKET
# ==============================
@app.route('/market')
def market():
    market_items = []

    if supplement_info is not None and hasattr(supplement_info, "empty") and not supplement_info.empty:
        for i in range(len(supplement_info['supplement name'])):
            disease_name = ""
            if disease_info is not None and hasattr(disease_info, "empty") and not disease_info.empty:
                disease_name = disease_info['disease_name'][i]

            market_items.append({
                'supplement_name': supplement_info['supplement name'][i],
                'disease_name':    disease_name,
                'image_url':       supplement_info['supplement image'][i],
                'buy_link':        supplement_info['buy link'][i],
            })

    # Load expert-submitted supplements
    try:
        conn = sqlite3.connect('leafmitra.db')
        rows = conn.execute(
            'SELECT supplement_name, disease_name, supplement_image FROM expert_submissions'
        ).fetchall()
        conn.close()
        for row in rows:
            market_items.append({
                'supplement_name': row[0],
                'disease_name':    row[1],
                'image_url':       f"uploads/{row[2]}" if row[2] else '',
                'buy_link':        '#',
            })
    except Exception as e:
        print(f"[WARN] Expert submissions load failed: {e}")

    return render_template('market.html', market_items=market_items)


# ==============================
# EXPERT SUBMISSION
# ==============================
@app.route('/expert', methods=['GET', 'POST'])
def expert():
    success = False

    if request.method == 'POST':

        leaf_img = request.files.get('leaf_image')
        supp_img = request.files.get('supplement_image')

        leaf_filename = None
        supp_filename = None

        if leaf_img and allowed_file(leaf_img.filename):
            ext = leaf_img.filename.rsplit('.', 1)[1].lower()
            leaf_filename = f"{uuid.uuid4().hex}.{ext}"
            leaf_img.save(os.path.join(app.config['UPLOAD_FOLDER'], leaf_filename))

        if supp_img and allowed_file(supp_img.filename):
            ext = supp_img.filename.rsplit('.', 1)[1].lower()
            supp_filename = f"{uuid.uuid4().hex}.{ext}"
            supp_img.save(os.path.join(app.config['UPLOAD_FOLDER'], supp_filename))

        conn = sqlite3.connect('leafmitra.db')
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expert_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disease_name TEXT,
                disease_description TEXT,
                prevention TEXT,
                supplement_name TEXT,
                supplement_description TEXT,
                leaf_image TEXT,
                supplement_image TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            INSERT INTO expert_submissions (
                disease_name, disease_description, prevention,
                supplement_name, supplement_description,
                leaf_image, supplement_image
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form.get('disease_name'),
            request.form.get('disease_description'),
            request.form.get('prevention'),
            request.form.get('supplement_name'),
            request.form.get('supplement_description'),
            leaf_filename,
            supp_filename,
        ))
        conn.commit()
        conn.close()
        success = True

    return render_template('expert.html', success=success)


# ==============================
# CONTACT
# ==============================
@app.route('/contact-us')
def contact():
    return render_template('contact-us.html')


# ==============================
# ERROR HANDLERS
# ==============================
@app.errorhandler(413)
def file_too_large(e):
    flash('File too large.', 'error')
    return redirect(url_for('home'))


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


# ==============================
# RUN APP
# ==============================
if __name__ == '__main__':
    app.run(debug=True)