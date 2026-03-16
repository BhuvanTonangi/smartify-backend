import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

# Load API keys from the .env file
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Smartify Backend")

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# Using flash because it is incredibly fast and completely free
model = genai.GenerativeModel('gemini-1.5-flash') 

# Define what data the Android app will send us
class NotificationData(BaseModel):
    app: str
    title: str
    text: str

@app.post("/process")
async def process_notification(notif: NotificationData):
    try:
        prompt = f"""
        Analyze this mobile notification:
        App: {notif.app}
        Title: {notif.title}
        Text: {notif.text}
        
        Provide a priority (High, Medium, or Low), an urgency score from 1 to 10, and a 1-line summary.
        Respond ONLY with a valid JSON object in this exact format:
        {{"priority": "High|Medium|Low", "score": 8, "summary": "Your summary here"}}
        """
        
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        ai_result = json.loads(response.text)
        
        db_record = {
            "app_name": notif.app,
            "title": notif.title,
            "original_text": notif.text,
            "priority": ai_result.get("priority", "Low"),
            "score": ai_result.get("score", 0),
            "summary": ai_result.get("summary", "No summary available.")
        }
        
        supabase.table("notifications").insert(db_record).execute()
        return {"status": "success", "data": db_record}

    except Exception as e:
        print(f"Error processing notification: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# A simple check to ensure the server is alive
@app.get("/")
def home():
    return {"message": "Smartify Backend is running!"}