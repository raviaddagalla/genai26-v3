from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL")

def build_chat_prompt(session, user_message, chat_history):
    recent_history = chat_history[-10:] if chat_history else []
    
    history_text = ""
    for msg in recent_history:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"
    
    brand_context = f"""
    Current Brand Information:
    - Brand Name: {session.get('brand_name', 'Not generated yet')}
    - Industry: {session.get('industry', 'Unknown')}
    - Tone: {session.get('tone', 'Unknown')}
    - Target Audience: {session.get('target_audience', 'Unknown')}
    - Brand Personality: {session.get('brand_personality', 'Unknown')}
    - Keywords: {session.get('keywords', 'Unknown')}
    """
    
    prompt = f"""
    You are BizForge, an expert branding consultant with full context of this brand.
    
    {brand_context}
    
    Conversation History:
    {history_text}
    
    User: {user_message}
    
    Provide strategic, actionable advice that aligns with the brand's personality and goals.
    Be helpful, specific, and reference the brand context where relevant.
    """
    
    return prompt

def chat_with_context(session, user_message):
    prompt = build_chat_prompt(session, user_message, session["chat_history"])
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    
    ai_response = response.choices[0].message.content
    
    session["chat_history"].append({"role": "user", "content": user_message})
    session["chat_history"].append({"role": "assistant", "content": ai_response})
    
    if len(session["chat_history"]) > 4:
        session["chat_history"] = session["chat_history"][-4:]
    
    return ai_response