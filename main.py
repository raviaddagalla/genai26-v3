from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os
from pydantic import BaseModel
import uuid
import json
import re
from typing import Optional, List
from datetime import datetime
from availability_checker import check_domain_availability
from intake_parser import extract_brand_config, BrandConfig
from auth_manager import load_users, register_user, login_user, save_users
from chat_service import chat_with_context

brand_sessions = {}
from ai_service import (
    generate_brand_names,
    generate_marketing_content,
    analyze_sentiment,
    chat_with_ai,
    generate_logo_prompt,
    generate_logo_image,
    get_color_palette,
    transcribe_audio,
    generate_tagline,
    generate_product_description,
    generate_social_post,
    generate_email,
    summarize_text,
    generate_competitor_analysis
)


# Load environment variables
load_dotenv()

app = FastAPI(title="BizForge API")

# Enable CORS (important for frontend later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # we'll tighten this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== TEMPLATE LOADING ==========
TEMPLATE_HTML = None
TEMPLATE_PATH = "brand-landing-template.html"

def load_template():
    global TEMPLATE_HTML
    try:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            TEMPLATE_HTML = f.read()
        print(f"✅ Template loaded: {len(TEMPLATE_HTML)} bytes")
    except Exception as e:
        print(f"❌ Failed to load template: {e}")
        TEMPLATE_HTML = None

# ========== PERSISTENCE ==========
SESSIONS_FILE = "sessions.json"

def load_sessions():
    global brand_sessions
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r') as f:
                brand_sessions = json.load(f)
                print(f"Loaded {len(brand_sessions)} sessions")
        except:
            brand_sessions = {}
    else:
        brand_sessions = {}

def save_sessions():
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(brand_sessions, f, indent=2)
    print(f"Saved {len(brand_sessions)} sessions")

@app.on_event("startup")
def startup_event():
    load_sessions()
    load_template()
    print("BizForge API started with persistence and template")

@app.on_event("shutdown")
def shutdown_event():
    save_sessions()
    print("Sessions saved on shutdown")

# ========== AUTH DEPENDENCY ==========
def get_session_from_auth_dependency(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No auth header")
    
    try:
        username, auth_session_id = authorization.split(":")
        users = load_users()
        if username in users and users[username]["session_id"] == auth_session_id:
            # Return the BRAND session ID stored in user data
            return users[username].get("brand_session_id")
        else:
            raise HTTPException(status_code=401, detail="Invalid auth")
    except:
        raise HTTPException(status_code=401, detail="Invalid auth format")

# ========== REQUEST MODELS ==========
class AuthRequest(BaseModel):
    username: str
    password: str

class RetryableRequest(BaseModel):
    retry: bool = False
    feedback: Optional[str] = None

class IntakeAnswers(BaseModel):
    answers: dict

class GenerateBrandFromSession(RetryableRequest):
    pass

class ContentRequest(BaseModel):
    brand_description: str
    tone: str
    content_type: str

class SentimentRequest(BaseModel):
    text: str
    brand_tone: str

class ChatRequest(BaseModel):
    user_message: str

class LogoSessionRequest(RetryableRequest):
    pass

class ColorFromSessionRequest(RetryableRequest):
    pass

class ColorRequest(BaseModel):
    tone: str
    industry: str

class TaglineRequest(RetryableRequest):
    pass

class ProductDescriptionRequest(RetryableRequest):
    product_name: str
    product_features: str

class SocialPostRequest(RetryableRequest):
    platform: str
    topic: str

class EmailRequest(RetryableRequest):
    email_type: str
    topic: str

class SummarizeRequest(RetryableRequest):
    text: str

class CompetitorAnalysisRequest(BaseModel):
    url: str

class ChatSessionRequest(BaseModel):
    message: str

class FullBrandKitRequest(BaseModel):
    product_name: Optional[str] = None
    product_features: Optional[str] = None
    social_platform: Optional[str] = None
    social_topic: Optional[str] = None
    email_type: Optional[str] = None
    email_topic: Optional[str] = None
    retry_all: bool = False

class NameAvailabilityRequest(BaseModel):
    names: List[str]

class GenerateWebsiteRequest(BaseModel):
    pass  # No body needed, uses auth

# ========== ROOT ==========
@app.get("/")
def root():
    return {"message": "BizForge backend is running 🚀"}

# ========== AUTH ENDPOINTS ==========
@app.post("/api/register")
def register(request: AuthRequest):
    result = register_user(request.username, request.password)
    return result

@app.post("/api/login")
def login(request: AuthRequest):
    result = login_user(request.username, request.password)
    return result

@app.post("/api/logout")
def logout(request: AuthRequest):
    return {"success": True}

# ========== INTAKE ENDPOINT ==========
@app.post("/api/intake")
def process_intake(answers: IntakeAnswers, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No auth header")
    
    try:
        username, auth_session_id = authorization.split(":")
        users = load_users()
        
        if username not in users or users[username]["session_id"] != auth_session_id:
            raise HTTPException(status_code=401, detail="Invalid auth")
        
        # Check if user already has a brand session
        if users[username].get("brand_session_id") and users[username]["brand_session_id"] in brand_sessions:
            session_id = users[username]["brand_session_id"]
            session = brand_sessions[session_id]
            print(f"Using existing session: {session_id}")
        else:
            # Create new brand session for this user
            session_id = str(uuid.uuid4())
            users[username]["brand_session_id"] = session_id
            save_users(users)
            print(f"Created new session: {session_id}")
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth error: {str(e)}")
    
    config = extract_brand_config(answers.answers)
    
    # Create or update session
    brand_sessions[session_id] = {
        "industry": config.industry,
        "target_audience": config.target_audience,
        "tone": config.tone,
        "keywords": ", ".join(config.keywords),
        "goals": config.goals,
        "uvp": config.unique_value_proposition,
        "brand_personality": config.brand_personality,
        "visual_style": config.visual_style_preference,
        
        "brand_name": None,
        "tagline": None,
        "logo_prompt": None,
        "logo_image": None,
        "color_palette": None,
        "color_palette_hex": None,
        "color_palette_primary": None,
        "color_palette_secondary": None,
        "product_description": None,
        "social_post": None,
        "email": None,
        
        "chat_history": [],
        "version": 1,
        
        "history": {
            "brand_names": [],
            "taglines": [],
            "product_descriptions": [],
            "social_posts": [],
            "emails": [],
            "color_palettes": [],
            "summaries": [],
            "logo_prompts": []
        }
    }
    
    save_sessions()
    return {
        "session_id": session_id,
        "config": config.dict(),
        "message": "Brand session created successfully."
    }

# ========== BRAND COMPLETENESS ORCHESTRATOR ==========
def ensure_brand_completeness(session, session_id):
    """
    Checks if all required brand elements exist.
    If missing, calls existing generators to create them.
    Returns True if any generation was triggered.
    """
    generated = False
    
    # Brand name is required for everything else
    if not session.get("brand_name"):
        print("⚠️ Brand name missing, generating...")
        names = generate_brand_names(
            industry=session["industry"],
            keywords=session["keywords"],
            tone=session["tone"],
            exclude=None
        )
        if names:
            session["history"]["brand_names"].extend(names)
            session["brand_name"] = names[0]
            session["version"] += 1
            generated = True
    
    # Tagline
    if not session.get("tagline") and session.get("brand_name"):
        print("⚠️ Tagline missing, generating...")
        tagline_result = generate_tagline(
            brand_name=session["brand_name"],
            industry=session["industry"],
            tone=session["tone"],
            exclude=None
        )
        
        # Store the full result in history
        session["history"]["taglines"].append(tagline_result)
        
        # Simple parsing: take first line or first sentence
        lines = tagline_result.split('\n')
        first_tagline = None
        
        # Try to find first numbered or bullet item
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line[0] in ['•', '-', '*']):
                # Clean up the line
                if '.' in line and line[0].isdigit():
                    first_tagline = line.split('.', 1)[1].strip()
                else:
                    first_tagline = line.lstrip('0123456789.•-* ').strip()
                break
        
        # If no numbered items, take first non-empty line
        if not first_tagline:
            for line in lines:
                if line.strip():
                    first_tagline = line.strip()
                    break
        
        # Fallback to first 50 chars
        if not first_tagline:
            first_tagline = tagline_result[:50] + '...' if len(tagline_result) > 50 else tagline_result
        
        session["tagline"] = first_tagline
        session["version"] += 1
        generated = True
    
    # Logo prompt (image generation is optional, but prompt is needed)
    if not session.get("logo_prompt") and session.get("brand_name"):
        print("⚠️ Logo prompt missing, generating...")
        logo_prompt = generate_logo_prompt(
            brand_name=session["brand_name"],
            industry=session["industry"],
            keywords=session["keywords"],
            exclude=None
        )
        session["history"]["logo_prompts"].append(logo_prompt)
        session["logo_prompt"] = logo_prompt
        session["version"] += 1
        generated = True
    
    # Color palette
    if not session.get("color_palette") and session.get("brand_name"):
        print("⚠️ Color palette missing, generating...")
        palette_result = get_color_palette(
            tone=session["tone"],
            industry=session["industry"],
            brand_name=session["brand_name"],
            exclude=None
        )
        
        session["history"]["color_palettes"].append(palette_result["full_description"])
        session["color_palette"] = palette_result["full_description"]
        session["color_palette_hex"] = palette_result["hex_codes"]
        session["color_palette_primary"] = palette_result["primary"]
        session["color_palette_secondary"] = palette_result["secondary"]
        session["version"] += 1
        generated = True
    
    if generated:
        save_sessions()
    
    return generated

# ========== SESSION TO BRAND DATA MAPPER ==========
def map_session_to_brand_data(session):
    """
    Transforms flat session storage into nested template format.
    No session structure modification.
    """
    
    # Get color palette - handle both old and new format
    if session.get("color_palette_hex"):
        primary = session.get("color_palette_primary", session["color_palette_hex"][0] if session["color_palette_hex"] else "#0d1117")
        secondary = session.get("color_palette_secondary", session["color_palette_hex"][1] if len(session["color_palette_hex"]) > 1 else "#161b22")
        accent = session["color_palette_hex"][2] if len(session["color_palette_hex"]) > 2 else (session["color_palette_hex"][0] if session["color_palette_hex"] else "#f97316")
    else:
        # Fallback defaults
        primary = "#0d1117"
        secondary = "#161b22"
        accent = "#f97316"
    
    background = primary
    text_color = "#e8edf3"
    
    # Extract target audience segments
    target_audience = session.get("target_audience", "Professionals")
    
    # Get features from session or create defaults
    features = []
    if session.get("product_description"):
        # Try to extract features from product description (simple split)
        desc_lines = session["product_description"].split('\n')
        feature_lines = [l for l in desc_lines if l.strip() and ('•' in l or '-' in l or 'feature' in l.lower())][:3]
        
        for i, line in enumerate(feature_lines[:3]):
            features.append({
                "title": f"Feature {i+1}",
                "description": line.replace('•', '').replace('-', '').strip()
            })
    
    # Ensure at least 3 features
    while len(features) < 3:
        features.append({
            "title": f"Capability {len(features)+1}",
            "description": "Powered by our innovative approach and deep industry expertise."
        })
    
    # Build the nested structure
    brand_data = {
        "brand_identity": {
            "brand_name": session.get("brand_name", "Your Brand"),
            "tagline": session.get("tagline", "Tagline pending"),
            "industry": session.get("industry", "Technology"),
            "target_audience": target_audience,
            "brand_personality": session.get("brand_personality", "Innovative · Bold · Reliable"),
            "unique_value_proposition": session.get("uvp", "Transforming ideas into impact.")
        },
        
        "design_system": {
            "primary_color": primary,
            "secondary_color": secondary,
            "accent_color": accent,
            "background_color": background,
            "text_color": text_color
        },
        
        "logo": {
            "logo_prompt": session.get("logo_prompt", "Abstract brand mark"),
            "logo_image_base64": session.get("logo_image", "")
        },
        
        "content": {
            "hero_description": session.get("goals", "Building something extraordinary."),
            "features": features,
            "about_section": f"We are {session.get('brand_name', 'a forward-thinking company')}. {session.get('brand_personality', 'We combine innovation with purpose.')}",
            "cta_text": "Ready to start?",
            "cta_button_text": "Get Started →"
        },
        
        "meta": {
            "domain_checked": False,
            "generation_version": session.get("version", 1),
            "created_at": str(datetime.now().isoformat())
        }
    }
    
    return brand_data

# ========== TEMPLATE INJECTOR ==========
def inject_brand_data_into_template(template_html, brand_data):
    """
    Replaces the BRAND_DATA object in template with our generated data.
    Uses string replace instead of regex to avoid Unicode escape issues.
    Returns complete HTML string.
    """
    import json
    
    # Convert brand_data to JSON string with proper formatting
    brand_data_json = json.dumps(brand_data, indent=2)
    
    # Find the exact marker in the template
    marker_start = "const BRAND_DATA = {"
    marker_end = "};"
    
    # Find the position of the marker
    start_idx = template_html.find(marker_start)
    if start_idx == -1:
        print("⚠️ BRAND_DATA marker not found in template")
        return template_html
    
    # Find the end of the BRAND_DATA object
    # Look for the closing brace after the start
    brace_count = 0
    in_string = False
    escape_next = False
    end_idx = -1
    
    for i in range(start_idx, len(template_html)):
        char = template_html[i]
        
        # Handle string literals
        if char == '"' and not escape_next:
            in_string = not in_string
        elif char == '\\' and not escape_next:
            escape_next = True
        else:
            escape_next = False
        
        # Count braces only when not in a string
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1  # Include the closing brace
                    break
    
    if end_idx == -1:
        print("⚠️ Could not find end of BRAND_DATA object")
        return template_html
    
    # Extract the part before and after
    before = template_html[:start_idx]
    after = template_html[end_idx:]
    
    # Construct the new HTML with injected data
    new_marker = f"const BRAND_DATA = {brand_data_json};"
    injected_html = before + new_marker + after
    
    return injected_html

# ========== BRAND GENERATION ENDPOINTS ==========
@app.post("/api/generate-brand")
def generate_brand_from_session(
    request: GenerateBrandFromSession,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    exclude_list = session["history"]["brand_names"][-20:] if request.retry else None

    result = generate_brand_names(
        industry=session["industry"],
        keywords=session["keywords"],
        tone=session["tone"],
        exclude=exclude_list,
        feedback=request.feedback if request.retry else None
    )

    session["history"]["brand_names"].extend(result)
    session["brand_name"] = result[0]
    session["version"] += 1
    save_sessions()

    return {
        "brand_names": result,
        "selected_brand_name": session["brand_name"],
        "version": session["version"]
    }

@app.post("/api/generate-content")
def generate_content(request: ContentRequest):
    result = generate_marketing_content(
        brand_description=request.brand_description,
        tone=request.tone,
        content_type=request.content_type
    )
    return {"content": result}

@app.post("/api/analyze-sentiment")
def sentiment_analysis(request: SentimentRequest):
    result = analyze_sentiment(
        text=request.text,
        brand_tone=request.brand_tone
    )
    return {"analysis": result}

@app.post("/api/chat")
def chat(request: ChatRequest):
    result = chat_with_ai(request.user_message)
    return {"response": result}

@app.post("/api/generate-logo")
def generate_logo_from_session(
    request: LogoSessionRequest,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    if not session.get("brand_name"):
        return {"error": "Generate brand name first"}

    exclude_list = session["history"]["logo_prompts"][-20:] if request.retry else None

    logo_prompt = generate_logo_prompt(
        brand_name=session["brand_name"],
        industry=session["industry"],
        keywords=session["keywords"],
        exclude=exclude_list,
        feedback=request.feedback if request.retry else None
    )

    session["history"]["logo_prompts"].append(logo_prompt)
    session["logo_prompt"] = logo_prompt
    session["version"] += 1
    save_sessions()

    image_base64 = generate_logo_image(logo_prompt)
    session["logo_image"] = image_base64
    save_sessions()

    return {
        "brand_name": session["brand_name"],
        "logo_prompt": logo_prompt,
        "image_base64": image_base64,
        "version": session["version"]
    }

@app.post("/api/get-colors-from-session")
def color_palette_from_session(
    request: ColorFromSessionRequest,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    if not session.get("brand_name"):
        return {"error": "Generate brand name first"}

    exclude_list = session["history"]["color_palettes"][-20:] if request.retry else None

    result = get_color_palette(
        tone=session["tone"],
        industry=session["industry"],
        brand_name=session["brand_name"],
        exclude=exclude_list,
        feedback=request.feedback if request.retry else None
    )

    # Store both the full description and parsed HEX codes
    session["history"]["color_palettes"].append(result["full_description"])
    session["color_palette"] = result["full_description"]
    session["color_palette_hex"] = result["hex_codes"]  # Store HEX codes separately
    session["color_palette_primary"] = result["primary"]
    session["color_palette_secondary"] = result["secondary"]
    session["version"] += 1
    save_sessions()

    return {
        "brand_name": session["brand_name"],
        "palette": result["full_description"],
        "hex_codes": result["hex_codes"],
        "primary": result["primary"],
        "secondary": result["secondary"],
        "version": session["version"]
    }

@app.post("/api/get-colors")
def color_palette(request: ColorRequest):
    result = get_color_palette(
        tone=request.tone,
        industry=request.industry,
        brand_name=None,
        exclude=None
    )
    return {
        "palette": result["full_description"],
        "hex_codes": result["hex_codes"],
        "primary": result["primary"],
        "secondary": result["secondary"]
    }

@app.post("/api/transcribe-voice")
async def transcribe_voice(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    result = transcribe_audio(audio_bytes)
    return {"transcription": result}

@app.post("/api/generate-tagline")
def generate_tagline_from_session(
    request: TaglineRequest,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    if not session.get("brand_name"):
        return {"error": "Generate brand name first"}

    exclude_list = session["history"]["taglines"][-20:] if request.retry else None

    result = generate_tagline(
        brand_name=session["brand_name"],
        industry=session["industry"],
        tone=session["tone"],
        exclude=exclude_list,
        feedback=request.feedback if request.retry else None
    )

    # Store the full result in history
    session["history"]["taglines"].append(result)
    
    # Simple parsing: take first line or first sentence
    lines = result.split('\n')
    first_tagline = None
    
    # Try to find first numbered or bullet item
    for line in lines:
        line = line.strip()
        if line and (line[0].isdigit() or line[0] in ['•', '-', '*']):
            # Clean up the line
            if '.' in line and line[0].isdigit():
                first_tagline = line.split('.', 1)[1].strip()
            else:
                first_tagline = line.lstrip('0123456789.•-* ').strip()
            break
    
    # If no numbered items, take first non-empty line
    if not first_tagline:
        for line in lines:
            if line.strip():
                first_tagline = line.strip()
                break
    
    # Fallback to first 50 chars
    if not first_tagline:
        first_tagline = result[:50] + '...' if len(result) > 50 else result
    
    session["tagline"] = first_tagline
    session["version"] += 1
    save_sessions()

    return {
        "brand_name": session["brand_name"],
        "taglines": result,
        "selected_tagline": first_tagline,
        "version": session["version"]
    }

@app.post("/api/generate-product-description")
def generate_product_from_session(
    request: ProductDescriptionRequest,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    if not session.get("brand_name"):
        return {"error": "Generate brand name first"}

    exclude_list = session["history"]["product_descriptions"][-20:] if request.retry else None

    result = generate_product_description(
        brand_name=session["brand_name"],
        industry=session["industry"],
        tone=session["tone"],
        product_name=request.product_name,
        product_features=request.product_features,
        exclude=exclude_list,
        feedback=request.feedback if request.retry else None
    )

    session["history"]["product_descriptions"].append(result)
    session["product_description"] = result
    session["version"] += 1
    save_sessions()

    return {
        "brand_name": session["brand_name"],
        "product_description": result,
        "version": session["version"]
    }

@app.post("/api/generate-social-post")
def generate_social_from_session(
    request: SocialPostRequest,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    if not session.get("brand_name"):
        return {"error": "Generate brand name first"}

    exclude_list = session["history"]["social_posts"][-20:] if request.retry else None

    result = generate_social_post(
        brand_name=session["brand_name"],
        industry=session["industry"],
        tone=session["tone"],
        platform=request.platform,
        topic=request.topic,
        exclude=exclude_list,
        feedback=request.feedback if request.retry else None
    )

    session["history"]["social_posts"].append(result)
    session["social_post"] = result
    session["version"] += 1
    save_sessions()

    return {
        "brand_name": session["brand_name"],
        "social_post": result,
        "version": session["version"]
    }

@app.post("/api/generate-email")
def generate_email_from_session(
    request: EmailRequest,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    if not session.get("brand_name"):
        return {"error": "Generate brand name first"}

    exclude_list = session["history"]["emails"][-20:] if request.retry else None

    result = generate_email(
        brand_name=session["brand_name"],
        industry=session["industry"],
        tone=session["tone"],
        email_type=request.email_type,
        subject_topic=request.topic,
        exclude=exclude_list,
        feedback=request.feedback if request.retry else None
    )

    session["history"]["emails"].append(result)
    session["email"] = result
    session["version"] += 1
    save_sessions()

    return {
        "brand_name": session["brand_name"],
        "email": result,
        "version": session["version"]
    }

@app.post("/api/summarize-text")
def summarize_from_session(
    request: SummarizeRequest,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    if not session.get("brand_name"):
        return {"error": "Generate brand name first"}

    exclude_list = session["history"]["summaries"][-20:] if request.retry else None

    result = summarize_text(
        brand_name=session["brand_name"],
        tone=session["tone"],
        text=request.text,
        exclude=exclude_list,
        feedback=request.feedback if request.retry else None
    )

    session["history"]["summaries"].append(result)
    session["version"] += 1
    save_sessions()

    return {
        "brand_name": session["brand_name"],
        "summary": result,
        "version": session["version"]
    }

@app.post("/api/analyze-competitor")
def analyze_competitor(request: CompetitorAnalysisRequest):
    result = generate_competitor_analysis(request.url)
    return result

@app.get("/api/session-status")
def session_status(authorization: str = Header(None)):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    return {
        "session_id": session_id,
        "brand_name": session.get("brand_name"),
        "has_tagline": session.get("tagline") is not None,
        "has_logo": session.get("logo_prompt") is not None,
        "has_color_palette": session.get("color_palette") is not None,
        "has_product_description": session.get("product_description") is not None,
        "has_social_post": session.get("social_post") is not None,
        "has_email": session.get("email") is not None,
        "version": session.get("version", 1),
        "chat_history_length": len(session.get("chat_history", [])),
        "has_color_palette_hex": session.get("color_palette_hex") is not None,
        "primary_color": session.get("color_palette_primary"),
        "secondary_color": session.get("color_palette_secondary"),
        "history_counts": {
            "brand_names": len(session["history"]["brand_names"]),
            "taglines": len(session["history"]["taglines"]),
            "product_descriptions": len(session["history"]["product_descriptions"]),
            "social_posts": len(session["history"]["social_posts"]),
            "emails": len(session["history"]["emails"]),
            "color_palettes": len(session["history"]["color_palettes"]),
            "summaries": len(session["history"]["summaries"]),
            "logo_prompts": len(session["history"]["logo_prompts"])
        }
    }

@app.post("/api/chat-with-context")
def chat_with_context_endpoint(
    request: ChatSessionRequest,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)
    
    if not session:
        return {"error": "Brand session not found"}
    
    response = chat_with_context(session, request.message)
    save_sessions()
    
    return {
        "response": response,
        "history_length": len(session["chat_history"])
    }

@app.post("/api/generate-full-brand-kit")
def generate_full_brand_kit(
    request: FullBrandKitRequest,
    authorization: str = Header(None)
):
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return {"error": "No active brand session. Please complete intake first."}
    
    session = brand_sessions.get(session_id)

    if not session:
        return {"error": "Brand session not found"}

    # ---------- BRAND NAME ----------
    if not session.get("brand_name") or request.retry_all:
        exclude = session["history"]["brand_names"][-20:] if request.retry_all else None

        names = generate_brand_names(
            industry=session["industry"],
            keywords=session["keywords"],
            tone=session["tone"],
            exclude=exclude
        )

        session["history"]["brand_names"].extend(names)
        session["brand_name"] = names[0]
        session["version"] += 1

    # ---------- TAGLINE ----------
    exclude = session["history"]["taglines"][-20:] if request.retry_all else None

    tagline_result = generate_tagline(
        brand_name=session["brand_name"],
        industry=session["industry"],
        tone=session["tone"],
        exclude=exclude
    )

    session["history"]["taglines"].append(tagline_result)
    
    # Simple parsing: take first line or first sentence
    lines = tagline_result.split('\n')
    first_tagline = None
    
    # Try to find first numbered or bullet item
    for line in lines:
        line = line.strip()
        if line and (line[0].isdigit() or line[0] in ['•', '-', '*']):
            if '.' in line and line[0].isdigit():
                first_tagline = line.split('.', 1)[1].strip()
            else:
                first_tagline = line.lstrip('0123456789.•-* ').strip()
            break
    
    # If no numbered items, take first non-empty line
    if not first_tagline:
        for line in lines:
            if line.strip():
                first_tagline = line.strip()
                break
    
    # Fallback
    if not first_tagline:
        first_tagline = tagline_result[:50] + '...' if len(tagline_result) > 50 else tagline_result
    
    session["tagline"] = first_tagline
    session["version"] += 1

    # ---------- LOGO ----------
    exclude = session["history"]["logo_prompts"][-20:] if request.retry_all else None

    logo_prompt = generate_logo_prompt(
        brand_name=session["brand_name"],
        industry=session["industry"],
        keywords=session["keywords"],
        exclude=exclude
    )

    session["history"]["logo_prompts"].append(logo_prompt)
    session["logo_prompt"] = logo_prompt
    session["version"] += 1

    logo_image = generate_logo_image(logo_prompt)
    session["logo_image"] = logo_image

    # ---------- COLOR PALETTE ----------
    exclude = session["history"]["color_palettes"][-20:] if request.retry_all else None

    palette_result = get_color_palette(
        tone=session["tone"],
        industry=session["industry"],
        brand_name=session["brand_name"],
        exclude=exclude
    )

    session["history"]["color_palettes"].append(palette_result["full_description"])
    session["color_palette"] = palette_result["full_description"]
    session["color_palette_hex"] = palette_result["hex_codes"]
    session["color_palette_primary"] = palette_result["primary"]
    session["color_palette_secondary"] = palette_result["secondary"]
    session["version"] += 1

    # ---------- OPTIONAL PRODUCT ----------
    product_result = None
    if request.product_name and request.product_features:
        exclude = session["history"]["product_descriptions"][-20:] if request.retry_all else None

        product_result = generate_product_description(
            brand_name=session["brand_name"],
            industry=session["industry"],
            tone=session["tone"],
            product_name=request.product_name,
            product_features=request.product_features,
            exclude=exclude
        )

        session["history"]["product_descriptions"].append(product_result)
        session["product_description"] = product_result
        session["version"] += 1

    # ---------- OPTIONAL SOCIAL ----------
    social_result = None
    if request.social_platform and request.social_topic:
        exclude = session["history"]["social_posts"][-20:] if request.retry_all else None

        social_result = generate_social_post(
            brand_name=session["brand_name"],
            industry=session["industry"],
            tone=session["tone"],
            platform=request.social_platform,
            topic=request.social_topic,
            exclude=exclude
        )

        session["history"]["social_posts"].append(social_result)
        session["social_post"] = social_result
        session["version"] += 1

    # ---------- OPTIONAL EMAIL ----------
    email_result = None
    if request.email_type and request.email_topic:
        exclude = session["history"]["emails"][-20:] if request.retry_all else None

        email_result = generate_email(
            brand_name=session["brand_name"],
            industry=session["industry"],
            tone=session["tone"],
            email_type=request.email_type,
            subject_topic=request.email_topic,
            exclude=exclude
        )

        session["history"]["emails"].append(email_result)
        session["email"] = email_result
        session["version"] += 1

    save_sessions()

    return {
        "brand_name": session["brand_name"],
        "tagline": session["tagline"],
        "logo_prompt": logo_prompt,
        "logo_image_base64": logo_image,
        "color_palette": session["color_palette"],
        "color_palette_hex": session["color_palette_hex"],
        "color_palette_primary": session["color_palette_primary"],
        "color_palette_secondary": session["color_palette_secondary"],
        "product_description": product_result,
        "social_post": social_result,
        "email": email_result,
        "version": session["version"]
    }

@app.post("/api/check-domain-availability")
def check_domain_availability_endpoint(request: NameAvailabilityRequest):
    results = []

    for name in request.names:
        clean_name = name.lower().replace(" ", "")
        domain = f"{clean_name}.com"

        available = check_domain_availability(domain)

        results.append({
            "name": name,
            "domain": domain,
            "available": available
        })

    return {"results": results}

@app.post("/api/backup-sessions")
def backup_sessions(authorization: str = Header(None)):
    save_sessions()
    
    import datetime
    backup_file = f"sessions_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_file, 'w') as f:
        json.dump(brand_sessions, f, indent=2)
    
    return {"success": True, "backup_file": backup_file}

# ========== NEW WEBSITE GENERATION ENDPOINT ==========
@app.post("/generate-website", response_class=HTMLResponse)
def generate_website(
    request: GenerateWebsiteRequest,
    authorization: str = Header(None)
):
    """
    Generates a complete brand website by:
    1. Getting session from auth
    2. Ensuring all brand elements exist
    3. Mapping to template format
    4. Injecting into template
    5. Returning HTML
    """
    # 1. Get session
    session_id = get_session_from_auth_dependency(authorization)
    if not session_id:
        return HTMLResponse(content="No active brand session", status_code=401)
    
    session = brand_sessions.get(session_id)
    if not session:
        return HTMLResponse(content="Session not found", status_code=404)
    
    # 2. Ensure completeness (auto-generate missing elements)
    ensure_brand_completeness(session, session_id)
    
    # 3. Map to template format
    brand_data = map_session_to_brand_data(session)
    
    # 4. Inject logo if available
    if session.get("logo_prompt") and not session.get("logo_image"):
        try:
            logo_image = generate_logo_image(session["logo_prompt"])
            session["logo_image"] = logo_image
            brand_data["logo"]["logo_image_base64"] = logo_image
            save_sessions()
        except Exception as e:
            print(f"⚠️ Logo generation failed: {e}")
    elif session.get("logo_image"):
        brand_data["logo"]["logo_image_base64"] = session["logo_image"]
    
    # 5. Inject into template
    if not TEMPLATE_HTML:
        return HTMLResponse(content="Template not loaded", status_code=500)
    
    final_html = inject_brand_data_into_template(TEMPLATE_HTML, brand_data)
    
    # 6. Return HTML response
    return HTMLResponse(content=final_html)