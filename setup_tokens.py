import argparse
from config import config
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_github_token(token: str):
    """Configure le token GitHub"""
    try:
        config.set_token('github', token)
        logger.info("Token GitHub configuré avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la configuration du token GitHub: {e}")

def setup_huggingface_token(token: str):
    """Configure le token Hugging Face"""
    try:
        config.set_token('huggingface', token)
        logger.info("Token Hugging Face configuré avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la configuration du token Hugging Face: {e}")

def main():
    parser = argparse.ArgumentParser(description='Configure les tokens pour les services')
    parser.add_argument('--github-token', help='Token GitHub')
    parser.add_argument('--huggingface-token', help='Token Hugging Face')
    
    args = parser.parse_args()
    
    if args.github_token:
        setup_github_token(args.github_token)
    if args.huggingface_token:
        setup_huggingface_token(args.huggingface_token)

if __name__ == "__main__":
    main() 