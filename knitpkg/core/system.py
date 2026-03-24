from pathlib import Path
import subprocess
import os
from typing import List, Optional
from knitpkg.mql.models import Target


class System:
    def __init__(self):
        pass

    def get_compile_cmd(self, compiler_path: Path, src_file_path: Path, inc_path: Path, log_file: Path) -> str:
        pass

    def get_default_mql5_compiler(self) -> str:
        return ""
    
    def get_default_mql4_compiler(self) -> str:
        return "/"
    
    def _get_mql_target_paths(self, target: Target, base_path: Path) -> List[Path]:
        return []
    
    @staticmethod
    def is_valid_target_path(target_path: Path) -> bool:
        """Check if a path is a valid MQL path with all required subdirectories."""
        required_dirs = ["Include", "Experts", "Indicators", "Scripts", "Libraries"]
        return all((target_path / dir_name).is_dir() for dir_name in required_dirs)



class WindowsSystem(System):
    def __init__(self):
        pass

    def get_compile_cmd(self, compiler_path: Path, src_file_path: Path, inc_path: Path, log_file: Path) -> str:
        cmd = f'{compiler_path.name} /compile:"{src_file_path}" /log:"{log_file}"'

        if inc_path:
            cmd += f' /inc:"{inc_path}"'
        
        return cmd

    def get_home_user_path(self) -> Path:
        return Path.home()
    
    def get_default_mql5_compiler(self) -> str:
        return r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"
    
    def get_default_mql4_compiler(self) -> str:
        return r"C:\Program Files (x86)\MetaTrader 4\metaeditor.exe"
    
    def _get_mql_target_paths(self, target: Target, base_path: Path) -> List[Path]:
        target_paths = []
        if not base_path.exists():
            return target_paths

        # Iterate through subfolders (e.g., "D0E8209F77C15E0B37B07412A6190423")
        # Using os.walk to ensure we only go one level deep in the terminal folders
        for root, dirs, _ in os.walk(base_path):
            for d in dirs:
                terminal_id_path = Path(root) / d
                mql_path = terminal_id_path / target.value.upper()
                if System.is_valid_target_path(mql_path):
                    target_paths.append(mql_path)

                # Also consider the terminal ID path itself if it contains all required dirs;
                # this handles cases when Data folder is under 'C:\Program Files\MetaTrader 5'.
                if System.is_valid_target_path(terminal_id_path):
                    target_paths.append(terminal_id_path)

            # Only search one level deep in Terminal folders
            break

        return target_paths

    def find_mql_paths(self, target: Target) -> List[Path]:
        """
        Locates MetaTrader data directories (MQL5 or MQL4) containing essential
        sub-folders (Include, Experts, Indicators, Scripts, Libraries).

        It searches common base locations like AppData roaming and default
        Program Files installations. For each base path, it inspects
        terminal-specific sub-folders (e.g., hash-named) to confirm the presence
        of all required MQL directories.

        Parameters
        ----------
        target : Target
            The MetaTrader target platform (Target.mql5 or Target.mql4).

        Returns
        -------
        List[Path]
            A list of absolute Path objects, each pointing to a valid mql5 or mql4
            data folder. The list may be empty if no suitable directories are found.

        Notes
        -----
        * Does not raise an exception if no paths are found; returns an empty list.
        * Used by commands like `kp compile` and `kp init` for auto-detection.
        """
        possible_paths = [
            Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal",
        ]

        if target == Target.mql5:
            possible_paths.append(
                Path("C:/Program Files/MetaTrader 5"), # Common default for MQL5
            )
        elif target == Target.mql4:
            possible_paths.append(
                Path("C:/Program Files (x86)/MetaTrader 4"),
            )

        found_mql_paths: List[Path] = []

        for base_path in possible_paths:
            target_path = self._get_mql_target_paths(target, base_path)
            if target_path:
                found_mql_paths.extend(target_path)

        return found_mql_paths

    
class PosixWineSystem(System):
    def __init__(self):
        pass

    @staticmethod
    def normalize_path(system_path: str, platform_key: str) -> str:
        winepath_result = subprocess.run(['winepath', platform_key, system_path], stdout=subprocess.PIPE)
        winepath_out = winepath_result.stdout
        winepath_out_utf8 = winepath_out.decode('utf-8')
        return winepath_out_utf8.strip()

    @staticmethod
    def win_normalize_path(posix_path: str) -> str:
        return PosixWineSystem.normalize_path(posix_path, '-w')

    @staticmethod
    def posix_normalize_path(win_path: str) -> str:
        return PosixWineSystem.normalize_path(win_path, '-u')

    @staticmethod
    def get_home_path() -> Path:
        winecmd_result = subprocess.run(['wine', 'cmd', '/c', 'echo', '%USERPROFILE%'], stdout=subprocess.PIPE)
        winecmd_out = winecmd_result.stdout
        winecmd_out_utf8 = winecmd_out.decode('utf-8')
        return Path(winecmd_out_utf8.strip())

    def get_compile_cmd(self, compiler_path: Path, src_file_path: Path, inc_path: Path, log_file: Path) -> str:
        compiler_dir_path = compiler_path.parent
        cmd = (
            f"wine start /wait {compiler_path.name}"
            f" /compile:\"{src_file_path.relative_to(compiler_dir_path)}\""
            f" /log:\"{log_file.relative_to(compiler_dir_path)}\""
        )

        if inc_path:
            cmd += f" /inc:\"{inc_path.relative_to(compiler_dir_path)}\""

        return cmd

    def get_default_mql5_compiler(self) -> str:
        return str(Path.home()) + r"/.mt5/drive_c/Program Files/MetaTrader 5/MetaEditor64.exe"
    
    def get_default_mql4_compiler(self) -> str:
        return str(Path.home()) + r"/.mt5/drive_c/Program Files (x86)/MetaTrader 4/metaeditor.exe"
    
    def _get_mql_target_paths(self, target: Target, base_path: Path) -> List[Path]:
        target_paths = []
        if not base_path.exists():
            return target_paths

        # Iterate through subfolders (e.g., "D0E8209F77C15E0B37B07412A6190423")
        # Using os.walk to ensure we only go one level deep in the terminal folders
        for root, dirs, _ in os.walk(base_path):
            for d in dirs:
                terminal_id_path = Path(root) / d
                mql_path = terminal_id_path / target.value.upper()
                if System.is_valid_target_path(mql_path):
                    target_paths.append(mql_path)
                
                # Also consider the terminal ID path itself if it contains all required dirs;
                # this handles cases when Data folder is under 'C:\Program Files\MetaTrader 5'.
                if System.is_valid_target_path(terminal_id_path):
                    target_paths.append(terminal_id_path)
                
            # Only search one level deep in Terminal folders
            break

        return target_paths

    def find_mql_paths(self, target: Target) -> List[Path]:
        """
        Locates MetaTrader data directories (MQL5 or MQL4) containing essential
        sub-folders (Include, Experts, Indicators, Scripts, Libraries).

        It searches common base locations like AppData roaming and default
        Program Files installations. For each base path, it inspects
        terminal-specific sub-folders (e.g., hash-named) to confirm the presence
        of all required MQL directories.

        Parameters
        ----------
        target : Target
            The MetaTrader target platform (Target.mql5 or Target.mql4).

        Returns
        -------
        List[Path]
            A list of absolute Path objects, each pointing to a valid mql5 or mql4
            data folder. The list may be empty if no suitable directories are found.

        Notes
        -----
        * Does not raise an exception if no paths are found; returns an empty list.
        * Used by commands like `kp compile` and `kp init` for auto-detection.
        """
        possible_paths = [
            Path(PosixWineSystem.posix_normalize_path(PosixWineSystem.get_home_path())) / "AppData" / "Roaming" / "MetaQuotes" / "Terminal",
        ]

        if target == Target.mql5:
            possible_paths.append(
                Path(PosixWineSystem.posix_normalize_path("C:/Program Files/MetaTrader 5")) # Common default for MQL5
            )
        elif target == Target.mql4:
            possible_paths.append(
                Path(PosixWineSystem.posix_normalize_path("C:/Program Files (x86)/MetaTrader 4"))
            )

        found_mql_paths: List[Path] = []

        for base_path in possible_paths:
            target_path = self._get_mql_target_paths(target, base_path)
            if target_path:
                found_mql_paths.extend(target_path)

        return found_mql_paths


import platform
my_system: System = WindowsSystem() if platform.system() == "Windows" else PosixWineSystem()
