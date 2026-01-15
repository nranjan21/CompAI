
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
from groq import Groq
import cohere

# Load env vars
load_dotenv(override=True)

def mask(key):
    if not key: return "None"
    if len(key) < 8: return "****"
    return f"{key[:4]}...{key[-4:]}"

print("\n🔍 DIAGNOSTIC START")
print("===================")

# 1. Check Environment Variables
print("\n1. Checking API Constants...")
g_key = os.getenv("GOOGLE_API_KEY")
gr_key = os.getenv("GROQ_API_KEY")
c_key = os.getenv("COHERE_API_KEY")

print(f"GOOGLE_API_KEY: {mask(g_key)}")
print(f"GROQ_API_KEY:   {mask(gr_key)}")
print(f"COHERE_API_KEY: {mask(c_key)}")

# 2. Test Gemini
print("\n2. Testing Gemini Connection...")
if g_key:
    try:
        genai.configure(api_key=g_key)
        # Update 2026
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Hello, reply with 'OK'.")
        print(f"✅ Gemini Success: {response.text.strip()}")
    except Exception as e:
        print(f"❌ Gemini Failed: {type(e).__name__}: {e}")
else:
    print("⚠️ Gemini Skipped (No Key)")

# 3. Test Groq
print("\n3. Testing Groq Connection...")
if gr_key:
    try:
        client = Groq(api_key=gr_key)
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello, reply with 'OK'."}],
            # Update 2026
            model="llama-3.3-70b-versatile",
        )
        print(f"✅ Groq Success: {chat_completion.choices[0].message.content.strip()}")
    except Exception as e:
        print(f"❌ Groq Failed: {type(e).__name__}: {e}")
else:
    print("⚠️ Groq Skipped (No Key)")

# 4. Test Cohere
print("\n4. Testing Cohere Connection...")
if c_key:
    try:
        client = cohere.Client(api_key=c_key)
        response = client.chat(
            message="Hello, reply with 'OK'.",
            # Update 2026
            model="command-r",
        )
        print(f"✅ Cohere Success: {response.text.strip()}")
    except Exception as e:
        print(f"❌ Cohere Failed: {type(e).__name__}: {e}")
else:
    print("⚠️ Cohere Skipped (No Key)")

print("\n=================")
print("DIAGNOSTIC END")
