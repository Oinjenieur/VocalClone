from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional

app = FastAPI(
    title="Voice Cloning Service",
    description="API pour le clonage vocal utilisant OpenVoice",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VoiceCloneRequest(BaseModel):
    text: str
    language: str
    style: Optional[str] = None

@app.post("/clone-voice")
async def clone_voice(
    audio_file: UploadFile = File(...),
    request: VoiceCloneRequest = None
):
    """
    Endpoint pour cloner une voix à partir d'un fichier audio
    """
    # TODO: Implémenter la logique de clonage vocal
    return {"message": "Service en cours de développement"}

@app.get("/health")
async def health_check():
    """
    Endpoint pour vérifier l'état du service
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 