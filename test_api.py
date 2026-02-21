import requests
import json
import time
from pprint import pprint

BASE_URL = "http://localhost:8000"

# ========== HELPER FUNCTIONS ==========
def print_separator(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_response(title, response):
    print(f"\n▶ {title}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        # Try to parse as JSON, if fails then it might be HTML
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(f"✅ Received non-JSON response (length: {len(response.text)} chars)")
            # Print first 200 chars of HTML to verify
            print(f"Preview: {response.text[:200]}...")
    else:
        print(f"Error: {response.text}")
    print("-"*40)

def save_html_response(filename, content):
    """Save HTML response to a file for viewing in browser"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Saved to {filename}")

# ========== 1. REGISTER & LOGIN ==========
print_separator("STEP 1: AUTHENTICATION")

# Register (ignore if already exists)
register = requests.post(f"{BASE_URL}/api/register", 
    json={"username": "testuser", "password": "testpass123"})
if register.status_code == 200:
    print_response("Register", register)

# Login
login = requests.post(f"{BASE_URL}/api/login", 
    json={"username": "testuser", "password": "testpass123"})
print_response("Login", login)

auth_session = login.json().get("session_id")
if not auth_session:
    print("❌ Login failed! Exiting.")
    exit()

headers = {"Authorization": f"testuser:{auth_session}"}
print(f"\n✅ Auth Header: {headers}")



# ========== 19. GENERATE WEBSITE (NEW FEATURE) ==========
print_separator("STEP 19: GENERATE WEBSITE FROM BRAND DATA")

print("🔄 Generating website... This may take a few seconds...")
website = requests.post(f"{BASE_URL}/generate-website", 
    headers=headers,
    json={})  # Empty body, uses auth

print_response("Website Generation", website)

if website.status_code == 200:
    # Save the HTML to a file for viewing
    html_content = website.text
    save_html_response("generated_brand_website.html", html_content)
    print("🌐 You can open 'generated_brand_website.html' in your browser to see the result!")
    
    # Quick verification of injected data
    if "const BRAND_DATA" in html_content:
        print("✅ Brand data successfully injected into template")
    else:
        print("⚠️ Brand data injection may have failed")
    
    # Check if logo was included
    if "logo_image_base64" in html_content and len(html_content.split("logo_image_base64")[1]) > 100:
        print("✅ Logo image included in website")
else:
    print("❌ Website generation failed")

# ========== 20. GENERATE WEBSITE WITH AUTO-COMPLETION ==========
print_separator("STEP 20: TEST WEBSITE AUTO-COMPLETION (MISSING ELEMENTS)")

# Create a new session with minimal data to test auto-completion
print("🔄 Creating minimal session to test auto-completion...")

# Register a new user for this test
mini_register = requests.post(f"{BASE_URL}/api/register", 
    json={"username": "miniuser", "password": "minipass"})
mini_login = requests.post(f"{BASE_URL}/api/login", 
    json={"username": "miniuser", "password": "minipass"})
mini_auth = mini_login.json().get("session_id")
mini_headers = {"Authorization": f"miniuser:{mini_auth}"}

# Minimal intake (only basic info)
mini_intake = requests.post(f"{BASE_URL}/api/intake", 
    headers=mini_headers,
    json={
        "answers": {
            "q1": "A tech startup for AI-powered productivity tools",
            "q2": "Young professionals who want to be more efficient",
            "q3": "Modern, innovative, helpful"
        }
    })
print_response("Minimal Intake", mini_intake)

# Generate website WITHOUT generating anything else first
print("🔄 Generating website with minimal data (should auto-complete missing elements)...")
mini_website = requests.post(f"{BASE_URL}/generate-website", 
    headers=mini_headers,
    json={})

print_response("Auto-complete Website Generation", mini_website)

if mini_website.status_code == 200:
    save_html_response("auto_complete_website.html", mini_website.text)
    print("🌐 Saved to 'auto_complete_website.html'")
    
    # Verify that elements were auto-generated
    mini_status = requests.get(f"{BASE_URL}/api/session-status", headers=mini_headers)
    if mini_status.status_code == 200:
        status_data = mini_status.json()
        print("\n✅ Auto-completion verification:")
        print(f"   - Brand name generated: {status_data.get('brand_name') is not None}")
        print(f"   - Tagline generated: {status_data.get('has_tagline')}")
        print(f"   - Logo prompt generated: {status_data.get('has_logo')}")
        print(f"   - Color palette generated: {status_data.get('has_color_palette')}")

# ========== 21. BACKUP SESSIONS ==========
print_separator("STEP 21: BACKUP SESSIONS")

backup = requests.post(f"{BASE_URL}/api/backup-sessions", headers=headers)
print_response("Backup Created", backup)

# ========== 22. TEST STATELESS CHAT (OLD ENDPOINT) ==========
print_separator("STEP 22: TEST STATELESS CHAT (FOR COMPARISON)")

stateless_chat = requests.post(f"{BASE_URL}/api/chat", 
    json={
        "user_message": "Give me one quick tip for sustainable fashion branding"
    })
print_response("Stateless Chat (No Context)", stateless_chat)

# ========== 23. TEST WEBSITE WITH DIFFERENT COLOR SCHEMES ==========
print_separator("STEP 23: TEST WEBSITE WITH DIFFERENT COLOR SCHEMES")

# Generate another color palette with different tone
alt_colors = requests.post(f"{BASE_URL}/api/get-colors-from-session", 
    headers=headers,
    json={
        "retry": True,
        "feedback": "Make it more vibrant and energetic, with brighter accent colors"
    })
print_response("Alternative Color Palette", alt_colors)

# Regenerate website with new colors
print("🔄 Regenerating website with new color scheme...")
website_v2 = requests.post(f"{BASE_URL}/generate-website", 
    headers=headers,
    json={})

if website_v2.status_code == 200:
    save_html_response("generated_brand_website_v2.html", website_v2.text)
    print("🌐 Saved to 'generated_brand_website_v2.html'")

print_separator("✅ ALL TESTS COMPLETED")
print("Check the responses above to verify all features are working!")
print("\nKey things to verify:")
print("1. ✅ Intake parser extracted all fields correctly")
print("2. ✅ Brand names generated with feedback incorporated")
print("3. ✅ Color palette returns HEX codes separately")
print("4. ✅ Chat history limited to 7 messages")
print("5. ✅ All generation functions work with session context")
print("6. ✅ Domain availability checker works")
print("7. ✅ Full brand kit generates everything at once")
print("8. ✅ Website generation creates HTML files")
print("9. ✅ Auto-completion works when elements are missing")
print("10. ✅ Color schemes can be updated and regenerated")

print("\n📁 Generated Files:")
print("   - generated_brand_website.html (main brand site)")
print("   - auto_complete_website.html (test with minimal data)")
print("   - generated_brand_website_v2.html (updated color scheme)")
print("\n🌐 Open these files in your browser to see the results!")