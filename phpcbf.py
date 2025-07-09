"""
PHP Code Beautifier and Fixer (CBF) Plugin for Sublime Text 4

This plugin provides PHP code formatting using PHP_CodeSniffer's phpcbf tool.
"""

import os
import sublime
import sublime_plugin
import subprocess
import difflib
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum


class ExitCode(Enum):
    """Exit codes for PHP CBF process."""
    SUCCESS = 0
    FIXES_APPLIED = 1
    ERROR = 2


@dataclass
class ProcessResult:
    """Result of running PHP CBF process."""
    stdout: str
    stderr: str
    exit_code: int

    @property
    def has_error(self) -> bool:
        """Check if process had an error."""
        return self.exit_code not in [ExitCode.SUCCESS.value, ExitCode.FIXES_APPLIED.value]


class SettingsManager:
    """Manages plugin settings with proper fallback handling."""

    SETTINGS_FILE = 'PHP_CBF.sublime-settings'

    def __init__(self):
        self._settings = None
        self.load()

    def load(self) -> None:
        """Load settings from file."""
        self._settings = sublime.load_settings(self.SETTINGS_FILE)

    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value with view-specific override support."""
        # Check view-specific settings first
        if (sublime.active_window() and
            sublime.active_window().active_view()):

            view_settings = sublime.active_window().active_view().settings()
            php_cbf_config = view_settings.get('PHP_CBF')

            if php_cbf_config and key in php_cbf_config:
                return php_cbf_config[key]

        # Fallback to global settings
        return self._settings.get(key, default)

    @property
    def php_path(self) -> Optional[str]:
        """Get PHP executable path."""
        return self.get('php_path')

    @property
    def phpcbf_path(self) -> Optional[str]:
        """Get PHPCBF executable path."""
        return self.get('phpcbf_path')

    @property
    def phpcs_standard(self) -> Union[str, Dict[str, str]]:
        """Get coding standard configuration."""
        return self.get('phpcs_standard', 'PSR2')

    @property
    def additional_args(self) -> List[str]:
        """Get additional command line arguments."""
        return self.get('additional_args', [])

    @property
    def fix_on_save(self) -> bool:
        """Check if auto-fix on save is enabled."""
        return self.get('fix_on_save', False)


class LoadingAnimator:
    """Handles loading animation display."""

    ANIMATIONS = {
        'windows': ['|', '/', '-', '\\'],
        'linux': ['|', '/', '-', '\\'],
        'osx': ['\u25d0', '\u25d3', '\u25d1', '\u25d2']
    }

    def __init__(self):
        self.index = 0
        self.is_running = False

    def start(self, message: str) -> None:
        """Start loading animation."""
        self.is_running = True
        self.index = 0
        sublime.set_timeout(lambda: self._animate(message), 0)

    def stop(self) -> None:
        """Stop loading animation."""
        self.is_running = False
        sublime.status_message('')

    def _animate(self, base_message: str) -> None:
        """Animate loading message."""
        if not self.is_running:
            return

        platform = sublime.platform()
        animation_chars = self.ANIMATIONS.get(platform, self.ANIMATIONS['linux'])

        message = f"{base_message.rstrip()} {animation_chars[self.index]}"
        sublime.status_message(message)

        self.index = (self.index + 1) % len(animation_chars)
        sublime.set_timeout(lambda: self._animate(base_message), 300)


class CommandBuilder:
    """Builds PHP CBF command line arguments."""

    def __init__(self, settings_manager: SettingsManager):
        self.settings = settings_manager

    def build_command(self, window: sublime.Window) -> List[str]:
        """Build complete command line arguments."""
        args = []

        # Add PHP executable
        self._add_php_executable(args)

        # Add PHPCBF path
        self._add_phpcbf_path(args, window)

        # Add coding standard
        self._add_coding_standard(args, window)

        # Add stdin flag
        args.append('-')

        # Add additional arguments
        args.extend(self.settings.additional_args)

        return args

    def _add_php_executable(self, args: List[str]) -> None:
        """Add PHP executable to command."""
        php_path = self.settings.php_path
        if php_path:
            args.append(php_path)
        elif os.name == 'nt':
            args.append('php')

    def _add_phpcbf_path(self, args: List[str], window: sublime.Window) -> None:
        """Add PHPCBF path to command."""
        phpcbf_path = self.settings.phpcbf_path
        if phpcbf_path and window.folders():
            project_folder = window.folders()[0]
            phpcbf_path = phpcbf_path.replace('${folder}', project_folder)
            args.append(phpcbf_path)

    def _add_coding_standard(self, args: List[str], window: sublime.Window) -> None:
        """Add coding standard to command."""
        standard_setting = self.settings.phpcs_standard
        if not standard_setting:
            return

        standard = self._resolve_standard(standard_setting, window)
        if standard and window.folders():
            project_folder = window.folders()[0]
            standard = standard.replace('${folder}', project_folder)
            args.append(f'--standard={standard}')

    def _resolve_standard(self, standard_setting: Union[str, Dict],
                         window: sublime.Window) -> Optional[str]:
        """Resolve coding standard based on project folder."""
        if isinstance(standard_setting, str):
            return standard_setting

        if isinstance(standard_setting, dict):
            # Check for folder-specific standard
            for folder in window.folders():
                folder_name = Path(folder).name
                if folder_name in standard_setting:
                    return standard_setting[folder_name]

            # Fallback to default
            return standard_setting.get('_default')

        return None


class DiffProcessor:
    """Processes diff between original and fixed content."""

    @staticmethod
    def create_diff(original: str, fixed: str) -> Optional[str]:
        """Create unified diff between original and fixed content."""
        try:
            original_lines = original.splitlines()
            fixed_lines = fixed.splitlines()
        except UnicodeDecodeError:
            sublime.status_message("Diff only works with UTF-8 files")
            return None

        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile='Original',
            tofile='Fixed',
            lineterm=''
        )

        diff_text = '\n'.join(diff)
        return diff_text if diff_text else None


class PHPCBFProcessor:
    """Main processor for PHP CBF operations."""

    def __init__(self):
        self.settings = SettingsManager()
        self.command_builder = CommandBuilder(self.settings)
        self.animator = LoadingAnimator()
        self.diff_processor = DiffProcessor()

    def process_file(self, window: sublime.Window, message: str = "Running PHP CBF") -> None:
        """Process current file with PHP CBF."""
        view = window.active_view()
        if not view:
            return

        content = view.substr(sublime.Region(0, view.size()))

        # Start loading animation
        self.animator.start(message)

        # Run PHP CBF in background thread
        thread = threading.Thread(
            target=self._run_phpcbf,
            args=(window, content, view.file_name())
        )
        thread.daemon = True
        thread.start()

    def _run_phpcbf(self, window: sublime.Window, content: str,
                   file_path: Optional[str]) -> None:
        """Run PHP CBF command in background."""
        try:
            args = self.command_builder.build_command(window)
            result = self._execute_command(args, content, file_path)

            # Process results on main thread
            sublime.set_timeout(
                lambda: self._process_results(result, window, content), 0
            )
        except Exception as e:
            sublime.set_timeout(
                lambda: self._handle_error(f"Error running PHP CBF: {str(e)}"), 0
            )

    def _execute_command(self, args: List[str], content: str,
                        file_path: Optional[str]) -> ProcessResult:
        """Execute PHP CBF command."""
        shell = os.name == 'nt'

        # Prepare input content
        if file_path:
            input_content = f"phpcs_input_file: {file_path}\n{content}"
        else:
            input_content = content

        # Run process
        proc = subprocess.Popen(
            args,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )

        stdout_data, stderr_data = proc.communicate(input_content.encode('utf-8'))

        return ProcessResult(
            stdout=stdout_data.decode('utf-8'),
            stderr=stderr_data.decode('utf-8'),
            exit_code=proc.returncode
        )

    def _process_results(self, result: ProcessResult, window: sublime.Window,
                        original_content: str) -> None:
        """Process PHP CBF results."""
        self.animator.stop()

        if result.has_error:
            self._handle_error(result.stderr)
            return

        # Check if there are any changes
        diff = self.diff_processor.create_diff(original_content, result.stdout)
        if not diff:
            sublime.status_message("PHP CBF: No changes needed")
            return

        # Apply changes
        view = window.active_view()
        if view:
            view.run_command('php_cbf_apply_changes', {'content': result.stdout})

            # Auto-save if enabled
            if self.settings.fix_on_save:
                view.settings().set('phpcbf_is_saving', True)
                view.run_command('save')

                # Force SublimeLinter to refresh after save
                sublime.set_timeout(lambda: self._refresh_linter(view), 100)
            else:
                # Force SublimeLinter to refresh immediately
                self._refresh_linter(view)

    def _refresh_linter(self, view: sublime.View) -> None:
        """Force SublimeLinter to refresh the current view."""
        try:
            # Try to trigger SublimeLinter refresh
            if view.window():
                # Method 1: Try to run SublimeLinter lint command
                view.window().run_command('sublime_linter_lint')
        except Exception:
            try:
                # Method 2: Simulate text change to trigger linter
                # This is a workaround to force SublimeLinter to notice changes
                edit = view.begin_edit()
                view.insert(edit, 0, '')
                view.end_edit(edit)

                # Trigger change event
                view.run_command('undo')
            except Exception:
                # Method 3: Try to access SublimeLinter directly
                try:
                    import SublimeLinter
                    if hasattr(SublimeLinter, 'lint'):
                        SublimeLinter.lint.Linter.lint_all_views()
                except ImportError:
                    pass

    def _handle_error(self, error_message: str) -> None:
        """Handle error messages."""
        print(f"--- PHP CBF Error ---\n{error_message.strip()}")
        sublime.status_message('PHP CBF: Error, check console for details')


# Global instances
settings_manager = SettingsManager()
processor = PHPCBFProcessor()


def plugin_loaded():
    """Called when plugin is loaded."""
    settings_manager.load()


class PhpCbfApplyChangesCommand(sublime_plugin.TextCommand):
    """Command to apply PHP CBF changes to view."""

    def run(self, edit, content: str):
        """Apply content changes to view."""
        self.view.replace(edit, sublime.Region(0, self.view.size()), content)

        # Mark the view as modified to ensure proper event handling
        self.view.set_scratch(False)

        # Force a selection change to trigger linter events
        current_sel = self.view.sel()
        if current_sel:
            point = current_sel[0].begin()
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(point, point))

            # Trigger a fake modification event
            sublime.set_timeout(lambda: self._trigger_modification_event(), 50)

    def _trigger_modification_event(self):
        """Trigger modification event to notify other plugins."""
        # This helps notify SublimeLinter about the changes
        self.view.run_command('move', {'by': 'characters', 'forward': True})
        self.view.run_command('move', {'by': 'characters', 'forward': False})


class PhpCbfCommand(sublime_plugin.WindowCommand):
    """Main command to run PHP CBF."""

    def run(self):
        """Execute PHP CBF on current file."""
        processor.process_file(self.window, "Running PHP CBF")


# Mantém compatibilidade com o nome antigo do comando para menus/keybindings
class PhpcbfCommand(sublime_plugin.WindowCommand):
    """Legacy command name for backward compatibility."""

    def run(self):
        """Execute PHP CBF on current file."""
        processor.process_file(self.window, "Running PHP CBF")


class PhpCbfEventListener(sublime_plugin.EventListener):
    """Event listener for auto-formatting on save."""

    def on_post_save(self, view: sublime.View) -> None:
        """Handle post-save event."""
        # Skip if this is a save triggered by PHP CBF
        if view.settings().get('phpcbf_is_saving', False):
            view.settings().erase('phpcbf_is_saving')
            return

        # Check if auto-fix is enabled and file is PHP
        if not self._should_auto_fix(view):
            return

        # Run PHP CBF
        window = view.window()
        if window:
            window.run_command("phpcbf")  # Usando o nome original do comando

    def on_modified_async(self, view: sublime.View) -> None:
        """Handle view modification to ensure linter updates."""
        # Only process if this view was recently modified by PHP CBF
        if hasattr(view, 'php_cbf_modified') and view.php_cbf_modified:
            view.php_cbf_modified = False

            # Small delay to ensure all changes are processed
            sublime.set_timeout(lambda: self._notify_linter(view), 200)

    def _notify_linter(self, view: sublime.View) -> None:
        """Notify SublimeLinter about changes."""
        try:
            # Try multiple methods to refresh SublimeLinter
            window = view.window()
            if window:
                # Method 1: Direct command
                window.run_command('sublime_linter_lint')
        except Exception:
            try:
                # Method 2: Access SublimeLinter API directly
                import SublimeLinter.lint
                if hasattr(SublimeLinter.lint, 'persist'):
                    SublimeLinter.lint.persist.on_modified_async(view)
            except (ImportError, AttributeError):
                pass

    def _should_auto_fix(self, view: sublime.View) -> bool:
        """Check if file should be auto-fixed."""
        if not settings_manager.fix_on_save:
            return False

        file_name = view.file_name()
        if not file_name:
            return False

        filename = os.path.basename(file_name)
        return (
            filename.endswith('.php') and
            not filename.startswith('.')
        )
