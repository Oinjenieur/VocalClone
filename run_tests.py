import os
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestRunner:
    def __init__(self):
        self.test_dir = Path("test_results")
        self.test_dir.mkdir(exist_ok=True)
        
        # Création d'un dossier pour les résultats de cette session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.test_dir / timestamp
        self.session_dir.mkdir(exist_ok=True)
        
        # Configuration des tests
        self.test_scripts = [
            "generate_test_samples.py",
            "setup_models.py",
            "test_models.py"
        ]

    def run_script(self, script_name: str) -> bool:
        """Exécute un script Python"""
        try:
            logger.info(f"Exécution de {script_name}...")
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True
            )
            
            # Sauvegarde des logs
            log_file = self.session_dir / f"{script_name}.log"
            with open(log_file, "w") as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write("\nErreurs:\n")
                    f.write(result.stderr)
            
            if result.returncode == 0:
                logger.info(f"{script_name} exécuté avec succès")
                return True
            else:
                logger.error(f"Erreur lors de l'exécution de {script_name}")
                return False
                
        except Exception as e:
            logger.error(f"Exception lors de l'exécution de {script_name}: {e}")
            return False

    def run_all_tests(self):
        """Exécute tous les tests"""
        success = True
        
        for script in self.test_scripts:
            if not self.run_script(script):
                success = False
                break
        
        if success:
            logger.info("Tous les tests ont été exécutés avec succès")
        else:
            logger.error("Les tests ont échoué")
            sys.exit(1)

def main():
    runner = TestRunner()
    runner.run_all_tests()

if __name__ == "__main__":
    main() 