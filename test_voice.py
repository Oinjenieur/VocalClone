import os
import torch
from openvoice import se_extractor
from openvoice.api import BaseSpeakerTTS, ToneColorConverter
from pydub.utils import which

# Spécifier le chemin vers ffmpeg
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg"
if which("ffmpeg") is None:
    raise Exception("ffmpeg n'est pas trouvé dans le PATH")

# Initialisation
ckpt_base = 'checkpoints/base_speakers/EN'
ckpt_converter = 'checkpoints/converter'
device = "cuda:0" if torch.cuda.is_available() else "cpu"
output_dir = 'outputs'

print(f"Using device: {device}")
print(f"ffmpeg path: {which('ffmpeg')}")

# Création du dossier de sortie
os.makedirs(output_dir, exist_ok=True)

# Initialisation des modèles
base_speaker_tts = BaseSpeakerTTS(
    config_path='checkpoints/base_speakers/EN/config.json',
    device=device,
)
base_speaker_tts.load_ckpt('checkpoints/base_speakers/EN/checkpoint.pth')

tone_color_converter = ToneColorConverter(f'{ckpt_converter}/config.json', device=device)
tone_color_converter.load_ckpt(f'{ckpt_converter}/checkpoint.pth')

# Chargement de l'empreinte vocale source
source_se = torch.load(f'{ckpt_base}/en_style_se.pth').to(device)

# Extraction de l'empreinte vocale de votre fichier audio
reference_speaker = 'resources/reference_voice.mp3'
target_se, audio_name = se_extractor.get_se(reference_speaker, tone_color_converter, target_dir='processed', vad=True)

# Texte à générer avec phonétisation pour améliorer la prononciation française
text = "Bohn-JOOR, juh swee FLOH-bee-DOO, votr ah-see-stahn AI pray-fay-RAY"
src_path = 'resources/reference_voice.wav'

# Génération du texte avec une vitesse légèrement réduite pour une meilleure articulation
base_speaker_tts.tts(text, src_path, speaker='cheerful', language='English', speed=0.9)

# Conversion avec votre voix
save_path = f'{output_dir}/output_french_cheerful.wav'
encode_message = "@MyShell"
tone_color_converter.convert(
    audio_src_path=src_path,
    src_se=source_se,
    tgt_se=target_se,
    output_path=save_path,
    message=encode_message)

print(f"Audio généré avec succès : {save_path}") 