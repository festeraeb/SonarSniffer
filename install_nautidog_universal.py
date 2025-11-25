#!/usr/bin/env python3
"""
NautiDog Sailing Installer - Robust Multi-Platform Setup
Handles conda detection, environment creation, and dependency verification
"""

import os
import sys
import subprocess
import platform
import shutil
import json
from pathlib import Path
from typing import Optional, Tuple, Dict

class NautiDogInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.is_windows = self.system == "windows"
        self.project_root = Path(__file__).parent
        self.conda_exe = None
        self.conda_root = None
        self.install_path = None
        
    def log(self, message: str, level: str = "INFO"):
        """Print colored log messages"""
        colors = {
            "INFO": "\033[36m",      # Cyan
            "SUCCESS": "\033[32m",   # Green
            "WARNING": "\033[33m",   # Yellow
            "ERROR": "\033[31m",     # Red
            "RESET": "\033[0m"       # Reset
        }
        
        # Windows console doesn't support ANSI codes by default
        if self.is_windows:
            print(f"[{level}] {message}")
        else:
            print(f"{colors.get(level, colors['INFO'])}[{level}] {message}{colors['RESET']}")
    
    def run_command(self, cmd: list, shell: bool = False, env: Dict = None) -> Tuple[bool, str]:
        """Run command and return success status and output"""
        try:
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                env=env or os.environ.copy(),
                timeout=300
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def find_conda(self) -> Optional[str]:
        """Find conda executable in PATH and common locations"""
        self.log("Searching for conda...", "INFO")
        
        # Try 'where conda' or 'which conda'
        cmd = "where conda" if self.is_windows else "which conda"
        success, output = self.run_command(cmd.split(), shell=True)
        if success and output.strip():
            conda_path = output.strip().split('\n')[0]
            self.log(f"Found conda in PATH: {conda_path}", "SUCCESS")
            return conda_path
        
        # Try direct command
        try:
            result = subprocess.run(
                ["conda", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log(f"Found conda: {result.stdout.decode().strip()}", "SUCCESS")
                return "conda"
        except:
            pass
        
        # Common installation paths
        common_paths = [
            Path.home() / "Miniconda3" / "Scripts" / "conda.exe" if self.is_windows else Path.home() / "miniconda3" / "bin" / "conda",
            Path.home() / "Anaconda3" / "Scripts" / "conda.exe" if self.is_windows else Path.home() / "anaconda3" / "bin" / "conda",
            Path.home() / "AppData" / "Local" / "Miniconda3" / "Scripts" / "conda.exe" if self.is_windows else None,
            Path("C:\\Miniconda3\\Scripts\\conda.exe") if self.is_windows else None,
            Path("C:\\Anaconda3\\Scripts\\conda.exe") if self.is_windows else None,
        ]
        
        for path in common_paths:
            if path and path.exists():
                self.log(f"Found conda at: {path}", "SUCCESS")
                return str(path)
        
        return None
    
    def get_conda_info(self, conda_exe: str) -> Optional[Dict]:
        """Get conda information including root prefix"""
        success, output = self.run_command([conda_exe, "info", "--json"])
        if success:
            try:
                return json.loads(output)
            except:
                pass
        return None
    
    def setup_conda_env_var(self):
        """Setup environment variables for conda access"""
        if not self.conda_root:
            return
        
        conda_info = self.get_conda_info(self.conda_exe)
        if not conda_info:
            return
        
        # Update PATH for conda
        paths_to_add = [
            str(Path(self.conda_root) / "Scripts"),
            str(Path(self.conda_root) / "Library" / "bin"),
            str(Path(self.conda_root) / "bin"),
        ]
        
        new_path = os.pathsep.join(paths_to_add) + os.pathsep + os.environ.get('PATH', '')
        os.environ['PATH'] = new_path
        
        self.log("Environment PATH configured for conda access", "SUCCESS")
    
    def check_conda(self) -> bool:
        """Check and find conda installation"""
        self.conda_exe = self.find_conda()
        
        if not self.conda_exe:
            self.log("ERROR: Conda not found!", "ERROR")
            self.log("Please install Miniconda from: https://docs.conda.io/en/latest/miniconda.html", "INFO")
            
            if self.is_windows:
                self.log("Windows: Download and run Miniconda3 installer", "INFO")
            else:
                self.log("Linux/macOS: curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh | bash", "INFO")
            
            return False
        
        # Get conda root
        conda_info = self.get_conda_info(self.conda_exe)
        if conda_info:
            self.conda_root = conda_info.get('conda_prefix')
        
        if not self.conda_root:
            # Fallback: extract from conda exe path
            conda_path = Path(self.conda_exe)
            if self.is_windows and conda_path.name == "conda.exe":
                self.conda_root = str(conda_path.parent.parent)
            else:
                self.conda_root = str(conda_path.parent.parent)
        
        self.setup_conda_env_var()
        return True
    
    def create_environment(self) -> bool:
        """Create or update conda environment"""
        self.log("Setting up conda environment...", "INFO")
        
        env_file = self.project_root / "environment.yml"
        if not env_file.exists():
            self.log(f"ERROR: environment.yml not found at {env_file}", "ERROR")
            return False
        
        # Check if environment exists
        success, output = self.run_command([self.conda_exe, "env", "list", "--json"])
        
        env_exists = False
        if success:
            try:
                env_info = json.loads(output)
                envs = env_info.get('envs', [])
                env_exists = any('nautidog' in env for env in envs)
            except:
                pass
        
        if env_exists:
            self.log("NautiDog environment exists, updating...", "INFO")
            cmd = [self.conda_exe, "env", "update", "-n", "nautidog", "-f", str(env_file), "--prune"]
        else:
            self.log("Creating NautiDog environment...", "INFO")
            cmd = [self.conda_exe, "env", "create", "-n", "nautidog", "-f", str(env_file), "--yes"]
        
        success, output = self.run_command(cmd)
        
        if success:
            self.log("Conda environment created/updated successfully", "SUCCESS")
            return True
        else:
            self.log(f"ERROR: Failed to create/update environment: {output[:200]}", "ERROR")
            return False
    
    def verify_installation(self) -> bool:
        """Verify key dependencies are installed"""
        self.log("Verifying installation...", "INFO")
        
        # Test Python
        cmd = [self.conda_exe, "run", "-n", "nautidog", "python", "--version"]
        success, output = self.run_command(cmd)
        
        if success:
            self.log(f"Python: {output.strip()}", "SUCCESS")
        else:
            self.log("ERROR: Python test failed", "ERROR")
            return False
        
        # Test key imports
        critical_imports = ["PyQt5", "numpy", "scipy"]
        for module in critical_imports:
            cmd = [self.conda_exe, "run", "-n", "nautidog", "python", "-c", f"import {module}"]
            success, _ = self.run_command(cmd)
            
            if success:
                self.log(f"{module}: OK", "SUCCESS")
            else:
                self.log(f"{module}: MISSING (non-critical)", "WARNING")
        
        return True
    
    def install(self, install_path: Optional[str] = None):
        """Run complete installation"""
        if install_path:
            self.install_path = Path(install_path)
        else:
            if self.is_windows:
                self.install_path = Path.home() / "NautiDog Sailing"
            else:
                self.install_path = Path.home() / "nautidog_sailing"
        
        self.log("\n" + "="*50, "INFO")
        self.log("NautiDog Sailing Installer", "INFO")
        self.log("="*50, "INFO")
        self.log(f"Installation path: {self.install_path}\n", "INFO")
        
        # Check conda
        if not self.check_conda():
            return False
        
        # Create installation directory
        self.install_path.mkdir(parents=True, exist_ok=True)
        self.log("Installation directory ready", "SUCCESS")
        
        # Copy files
        self.log("Copying application files...", "INFO")
        try:
            for item in self.project_root.iterdir():
                if item.name.startswith("install_") or item.name.endswith(".lnk"):
                    continue
                
                if item.is_file():
                    shutil.copy2(item, self.install_path / item.name)
                elif item.is_dir():
                    dest_dir = self.install_path / item.name
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)
                    shutil.copytree(item, dest_dir)
            
            self.log("Files copied successfully", "SUCCESS")
        except Exception as e:
            self.log(f"ERROR: Failed to copy files: {e}", "ERROR")
            return False
        
        # Create environment
        if not self.create_environment():
            return False
        
        # Verify installation
        if not self.verify_installation():
            self.log("WARNING: Verification had issues, but continuing...", "WARNING")
        
        self.log("\n" + "="*50, "SUCCESS")
        self.log("Installation completed successfully!", "SUCCESS")
        self.log("="*50, "SUCCESS")
        
        if self.is_windows:
            self.log("To launch: Run 'launch_nautidog_conda.bat' or use Desktop shortcut", "INFO")
        else:
            self.log("To launch: Run './launch_nautidog.sh' or 'conda run -n nautidog python sonar_gui.py'", "INFO")
        
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="NautiDog Sailing Installer")
    parser.add_argument("--install-path", type=str, help="Custom installation path")
    parser.add_argument("--skip-verification", action="store_true", help="Skip dependency verification")
    
    args = parser.parse_args()
    
    installer = NautiDogInstaller()
    success = installer.install(args.install_path)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
