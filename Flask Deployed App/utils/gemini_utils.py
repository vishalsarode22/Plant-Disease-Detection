import os
import base64

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')


def encode_image_to_base64(image_path):
    """Convert image file to base64 string for Gemini Vision."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_gemini_insights(label: str, confidence: float, is_unknown: bool, image_path: str = None) -> dict:
    """
    Get insights from Gemini.
    - If unknown AND image_path provided → use Gemini Vision to identify the leaf
    - If known → ask Gemini for disease treatment info
    - If API unavailable → use fallback text
    """
    if not GEMINI_API_KEY:
        return _fallback_insights(label, confidence, is_unknown)

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        # ── CASE 1: Unknown leaf → use Gemini Vision to identify it ──
        if is_unknown and image_path and os.path.exists(image_path):
            return _gemini_vision_identify(image_path, confidence, genai)

        # ── CASE 2: Known prediction → get treatment info ──
        else:
            return _gemini_text_insights(label, confidence, genai)

    except Exception as e:
        print(f"[Gemini Error] {e}")
        return _fallback_insights(label, confidence, is_unknown)


def _gemini_vision_identify(image_path: str, confidence: float, genai) -> dict:
    """Use Gemini Vision to identify unknown leaf from image."""
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Encode image
    image_data = encode_image_to_base64(image_path)
    ext = image_path.rsplit('.', 1)[-1].lower()
    mime_type = 'image/jpeg' if ext in ['jpg', 'jpeg'] else 'image/png'

    prompt = """You are an expert botanist and plant pathologist.

Look at this leaf image carefully and provide a structured response:

**1. Plant Identification**
What plant does this leaf belong to? Give your best identification with confidence level (High/Medium/Low).

**2. Observed Condition**
Does the leaf appear healthy or does it show signs of disease/stress? Describe what you see.

**3. Possible Disease (if any)**
If the leaf shows disease symptoms, name the most likely disease and describe its characteristics.

**4. Recommended Treatment**
Provide specific actionable treatment steps for the identified condition.

**5. Prevention Tips**
How can the farmer prevent this issue in the future?

Note: Our AI model could not confidently identify this leaf from its 14 trained plant categories. Please give your best assessment based on visual analysis.

Keep language simple and farmer-friendly."""

    response = model.generate_content([
        {'mime_type': mime_type, 'data': image_data},
        prompt
    ])

    return {
        'raw': response.text,
        'is_unknown': True,
        'source': 'gemini_vision',
        'vision_used': True
    }


def _gemini_text_insights(label: str, confidence: float, genai) -> dict:
    """Get treatment insights for a known prediction."""
    model = genai.GenerativeModel('gemini-1.5-flash')

    parts = label.split(' - ')
    plant = parts[0] if len(parts) > 0 else 'Plant'
    disease = parts[1] if len(parts) > 1 else 'Condition'
    is_healthy = 'Healthy' in disease

    if is_healthy:
        prompt = f"""The AI detected a healthy {plant} plant with {confidence*100:.1f}% confidence.

Provide structured advice in these sections:

**1. Plant & Health Overview**
Brief description of the {plant} plant and what a healthy one looks like.

**2. Optimal Growing Conditions**
Key conditions needed for this plant to thrive.

**3. Maintenance Tips**
Bullet points of best practices to keep this plant healthy.

**4. Common Threats to Watch**
What diseases or pests commonly affect {plant} and early warning signs.

Keep it practical and farmer-friendly."""
    else:
        prompt = f"""The AI detected '{disease}' in a {plant} plant with {confidence*100:.1f}% confidence.

Provide structured advice in these sections:

**1. Disease Overview**
What is {disease}? Brief explanation of this disease.

**2. Causes & Symptoms**
What causes it and visible symptoms to identify it.

**3. Immediate Treatment Steps**
Specific step-by-step treatment. Use bullet points.

**4. Recommended Products**
Types of fungicides/pesticides/treatments commonly used.

**5. Prevention for Next Season**
How to prevent recurrence. Use bullet points.

Keep language simple and suitable for farmers."""

    response = model.generate_content(prompt)

    return {
        'raw': response.text,
        'is_unknown': False,
        'source': 'gemini',
        'vision_used': False
    }


def _fallback_insights(label: str, confidence: float, is_unknown: bool) -> dict:
    """Fallback when Gemini API is not available."""
    if is_unknown:
        raw = """**Plant Identification**
Our AI model could not confidently identify this leaf. It may belong to a plant not in our 14 trained categories (such as Mango, Banana, Papaya, Neem, etc.).

**What You Should Do**
- Take a clearer, well-lit photo with the leaf filling the frame
- Try from directly above the leaf on a plain background
- Consult your local agricultural expert or Krishi Vigyan Kendra (KVK)
- Use apps like PlantNet or iNaturalist for broader plant identification

**General Leaf Health Tips**
- Yellow spots usually indicate fungal infection
- Brown crispy edges often mean water stress or sunburn
- Dark lesions with yellow halos suggest bacterial infection
- Powdery white coating is typically powdery mildew"""
    else:
        parts = label.split(' - ')
        plant = parts[0] if len(parts) > 0 else 'Plant'
        disease = parts[1] if len(parts) > 1 else 'Condition'

        if 'Healthy' in disease:
            raw = f"""**Plant Overview**
Your {plant} plant appears healthy with {confidence*100:.1f}% confidence.

**Maintenance Tips**
- Water regularly but avoid waterlogging
- Ensure proper sunlight exposure
- Apply balanced fertilizer monthly
- Monitor weekly for early disease signs

**Prevention**
- Practice crop rotation each season
- Keep area clean of fallen leaves and debris
- Use disease-resistant varieties when replanting"""
        else:
            raw = f"""**Disease Overview**
{disease} detected in {plant} with {confidence*100:.1f}% confidence.

**Immediate Treatment**
- Remove and destroy all infected leaves immediately
- Apply appropriate fungicide or bactericide
- Avoid overhead watering — water at the base only
- Improve air circulation by spacing plants properly

**Prevention**
- Use certified disease-free seeds
- Rotate crops every season
- Sanitize tools with diluted bleach regularly
- Apply neem oil spray as preventive measure"""

    return {
        'raw': raw,
        'is_unknown': is_unknown,
        'source': 'fallback',
        'vision_used': False
    }