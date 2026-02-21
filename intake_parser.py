from pydantic import BaseModel
from typing import List, Optional
import json
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL")

class BrandConfig(BaseModel):
    industry: str
    target_audience: str
    tone: str
    keywords: List[str]
    goals: str
    unique_value_proposition: str
    brand_personality: str
    visual_style_preference: Optional[str] = "modern"

def extract_brand_config(answers: dict) -> BrandConfig:
    answers_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in answers.items()])
    
    prompt = f"""
    You are a brand strategy expert. Analyze these user answers and extract a structured brand configuration.
    
    User Answers:
    {answers_text}
    
    Return a STRICT JSON object with exactly these keys:
    - industry: (the main industry/business sector)
    - target_audience: (who they're trying to reach)
    - tone: (brand voice - professional, playful, luxury, etc.)
    - keywords: (array of 5-7 core brand keywords)
    - goals: (what they want to achieve)
    - unique_value_proposition: (what makes them different)
    - brand_personality: (if it were a person, describe it)
    - visual_style_preference: (minimalist, bold, classic, etc. - assume "modern" if not specified)
    
    If any information is missing, make intelligent assumptions based on context.
    Return ONLY the JSON object, no other text.
    """
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        config_dict = json.loads(response.choices[0].message.content)
        return BrandConfig(**config_dict)
    except:
        return BrandConfig(
            industry=answers.get("q1", "technology"),
            target_audience=answers.get("q2", "general consumers"),
            tone=answers.get("q3", "professional"),
            keywords=["innovation", "quality", "trust"],
            goals="establish market presence",
            unique_value_proposition="superior quality and service",
            brand_personality="professional and trustworthy",
            visual_style_preference="modern"
        )