from groq import Groq
from dotenv import load_dotenv
import os
from competitor_analyzer import analyze_competitor_site
from typing import Optional, List

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL")

def generate_brand_names(
    industry: str,
    keywords: str,
    tone: str,
    exclude: Optional[List[str]] = None,
    feedback: Optional[str] = None
) -> List[str]:
    exclude_text = ""
    if exclude:
        exclude_text = f"\nDo NOT generate these names again: {exclude}"
    
    feedback_text = ""
    if feedback:
        feedback_text = f"\nUser requested changes: {feedback}\nPlease incorporate this feedback in your new suggestions."

    prompt = f"""
    Generate 10 unique brand names.

    Industry: {industry}
    Keywords: {keywords}
    Tone: {tone}

    {exclude_text}
    {feedback_text}

    Return only a numbered list.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response.choices[0].message.content

    lines = raw_output.split("\n")
    clean_names = []

    for line in lines:
        line = line.strip()
        if line and "." in line:
            clean_names.append(line.split(".", 1)[1].strip())

    # Remove duplicates within the same response
    clean_names = list(dict.fromkeys(clean_names))

    return clean_names


def generate_marketing_content(brand_description: str, tone: str, content_type: str):
    prompt = f"""
    You are BizForge, an expert marketing copywriter.

    Brand Description: {brand_description}
    Tone: {tone}
    Content Type: {content_type}

    Generate high-quality, professional marketing content.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


def analyze_sentiment(text: str, brand_tone: str):
    prompt = f"""
    You are a branding sentiment analyst.

    Analyze the sentiment of the following text.
    Consider alignment with brand tone: {brand_tone}

    Text:
    {text}

    Return:
    - Sentiment (Positive / Neutral / Negative)
    - Confidence score (0-100%)
    - Short explanation
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

import requests

HF_API_KEY = os.getenv("HF_API_KEY")
IBM_MODEL = os.getenv("IBM_MODEL")

def chat_with_ai(user_message: str):
    prompt = f"""
    You are BizForge, an expert branding consultant.

    Provide strategic, actionable, professional branding advice.

    User Question:
    {user_message}
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def generate_logo_prompt(
    brand_name: str,
    industry: str,
    keywords: str,
    exclude: Optional[List[str]] = None,
    feedback: Optional[str] = None
):
    exclude_text = ""
    if exclude:
        exclude_text = f"\nDo NOT generate these logo prompts again: {exclude}"
    
    feedback_text = ""
    if feedback:
        feedback_text = f"\nUser requested changes: {feedback}\nPlease incorporate this feedback."

    prompt = f"""
    You are a professional brand identity designer.

    Create a detailed, high-quality logo design prompt.

    Brand Name: {brand_name}
    Industry: {industry}
    Core Keywords: {keywords}

    {exclude_text}
    {feedback_text}

    Include:
    - Visual style
    - Color suggestions
    - Typography style
    - Symbol concepts
    - Emotional tone
    - Background style

    Write it as a ready-to-use prompt for an AI image generator.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

from PIL import Image
from io import BytesIO
import base64

SDXL_MODEL = os.getenv("SDXL_MODEL")

def generate_logo_image(prompt: str):
    url = f"https://router.huggingface.co/hf-inference/models/{SDXL_MODEL}"

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Accept": "image/png"
    }

    payload = {
        "inputs": prompt
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return f"Error: {response.text}"

    # Convert image bytes to base64 so FastAPI can return it
    image_bytes = response.content
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    return encoded_image

def get_color_palette(
    tone: str,
    industry: str,
    brand_name: Optional[str] = None,
    exclude: Optional[List[str]] = None,
    feedback: Optional[str] = None
):
    exclude_text = ""
    if exclude:
        exclude_text = f"\nDo NOT generate these color palettes again: {exclude}"
    
    feedback_text = ""
    if feedback:
        feedback_text = f"\nUser requested changes: {feedback}\nPlease incorporate this feedback."

    brand_context = f"Brand Name: {brand_name}" if brand_name else ""

    prompt = f"""
    You are a professional brand identity designer.

    Generate a cohesive brand color palette.

    Industry: {industry}
    Brand Tone: {tone}
    {brand_context}

    {exclude_text}
    {feedback_text}

    Provide:
    - 5 HEX color codes
    - Short explanation for each color
    - Suggested primary and secondary color

    Format clearly.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response.choices[0].message.content
    
    # Extract HEX codes using regex
    import re
    hex_codes = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', raw_output)
    
    # Return both the full description and extracted HEX codes
    return {
        "full_description": raw_output,
        "hex_codes": hex_codes[:5],  # Limit to first 5
        "primary": hex_codes[0] if hex_codes else None,
        "secondary": hex_codes[1] if len(hex_codes) > 1 else None
    }

import speech_recognition as sr
import tempfile

def transcribe_audio(file):
    recognizer = sr.Recognizer()

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(file)
        temp_audio_path = temp_audio.name

    try:
        with sr.AudioFile(temp_audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except Exception as e:
        return f"Error: {str(e)}"

def generate_tagline(
    brand_name: str,
    industry: str,
    tone: str,
    exclude: Optional[List[str]] = None,
    feedback: Optional[str] = None
):
    exclude_text = ""
    if exclude:
        exclude_text = f"\nAvoid repeating these previous taglines: {exclude}"
    
    feedback_text = ""
    if feedback:
        feedback_text = f"\nUser requested changes: {feedback}\nPlease incorporate this feedback."

    prompt = f"""
    Generate 5 unique taglines.

    Brand: {brand_name}
    Industry: {industry}
    Tone: {tone}

    {exclude_text}
    {feedback_text}
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def generate_product_description(
    brand_name: str,
    industry: str,
    tone: str,
    product_name: str,
    product_features: str,
    exclude: Optional[List[str]] = None,
    feedback: Optional[str] = None
):
    exclude_text = ""
    if exclude:
        exclude_text = f"\nDo not repeat previous descriptions: {exclude}"
    
    feedback_text = ""
    if feedback:
        feedback_text = f"\nUser requested changes: {feedback}\nPlease incorporate this feedback."

    prompt = f"""
    Write a product description.

    Brand: {brand_name}
    Industry: {industry}
    Tone: {tone}

    Product: {product_name}
    Features: {product_features}

    {exclude_text}
    {feedback_text}
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def generate_social_post(
    brand_name: str,
    industry: str,
    tone: str,
    platform: str,
    topic: str,
    exclude: Optional[List[str]] = None,
    feedback: Optional[str] = None
):
    exclude_text = ""
    if exclude:
        exclude_text = f"\nAvoid repeating these posts: {exclude}"
    
    feedback_text = ""
    if feedback:
        feedback_text = f"\nUser requested changes: {feedback}\nPlease incorporate this feedback."

    prompt = f"""
    Create a {platform} post.

    Brand: {brand_name}
    Industry: {industry}
    Tone: {tone}
    Topic: {topic}

    {exclude_text}
    {feedback_text}
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def generate_email(
    brand_name: str,
    industry: str,
    tone: str,
    email_type: str,
    subject_topic: str,
    exclude: Optional[List[str]] = None,
    feedback: Optional[str] = None
):
    exclude_text = ""
    if exclude:
        exclude_text = f"\nAvoid repeating previous emails: {exclude}"
    
    feedback_text = ""
    if feedback:
        feedback_text = f"\nUser requested changes: {feedback}\nPlease incorporate this feedback."

    prompt = f"""
    Write a {email_type} email.

    Brand: {brand_name}
    Industry: {industry}
    Tone: {tone}
    Topic: {subject_topic}

    {exclude_text}
    {feedback_text}
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def summarize_text(
    brand_name: str,
    tone: str,
    text: str,
    exclude: Optional[List[str]] = None,
    feedback: Optional[str] = None
):
    exclude_text = ""
    if exclude:
        exclude_text = f"\nAvoid repeating this previous summary: {exclude}"
    
    feedback_text = ""
    if feedback:
        feedback_text = f"\nUser requested changes: {feedback}\nPlease incorporate this feedback."

    prompt = f"""
    Summarize this text.

    Brand: {brand_name}
    Tone: {tone}

    Text:
    {text}

    {exclude_text}
    {feedback_text}
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def generate_competitor_analysis(url: str):
    structured_data = analyze_competitor_site(url)

    if "error" in structured_data:
        return structured_data

    prompt = f"""
    You are a competitive brand strategist.

    Below is structured data scraped from a competitor website.

    Pages Scraped: {structured_data['pages_scraped']}
    Top Keywords: {structured_data['top_keywords']}
    Headings: {structured_data['headings']}
    Detected Brand Colors: {structured_data['detected_colors']}
    Calls-To-Action: {structured_data['ctas']}
    Product/Service Links: {structured_data['product_links']}

    Website Text Sample:
    {structured_data['text_sample']}

    Provide:
    - Competitor positioning summary
    - Core products/services offered
    - Messaging style analysis
    - Color psychology interpretation
    - CTA strategy analysis
    - What strategic elements are strong
    - What could be copied or improved

    Be analytical and structured.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "structured_data": structured_data,
        "strategic_analysis": response.choices[0].message.content
    }