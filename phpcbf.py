import os
import sublime
import sublime_plugin
import subprocess
import difflib
import threading

"""
Set some constants
"""
SETTINGS_FILE = 'PHP_CBF.sublime-settings'

"""
GET/SET SETTINGS CLASS FROM SUBLIME-PHPCS
THANKS AND CREDITS TO: Ben Selby (github: @BENMATSELBY)
"""
class Preferences:
    def load(self):
        self.settings = sublime.load_settings(SETTINGS_FILE)

    def get(self, key):
        if sublime.active_window() is not None and sublime.active_window().active_view() is not None:
          conf = sublime.active_window().active_view().settings().get('PHP_CBF')
          if conf is not None and key in conf:
            return conf.get(key)

        return self.settings.get(key)

"""
CHECK SUBLIME VERSION
LOAD SETTINGS
"""
settings = Preferences()

def plugin_loaded():
    settings.load()

"""
MAIN PHP_CODESNIFFER CLASS
HANDLE THE REQUESTS FROM SUBLIME
"""
class PHP_CBF:
  # Type of the view, phpcs or phpcbf.
  file_view   = None
  window      = None
  processed   = False
  process_anim_idx = 0
  process_anim = {
    'windows': ['|', '/', '-', '\\'],
    'linux': ['|', '/', '-', '\\'],
    'osx': [u'\u25d0', u'\u25d3', u'\u25d1', u'\u25d2']
  }
  regions = []

  def run(self, window , msg):
    self.window = window
    cmd = 'phpcbf'
    content = window.active_view().substr(sublime.Region(0, window.active_view().size()))

    tm = threading.Thread(target=self.loading_msg, args=([msg]))
    tm.start()

    t = threading.Thread(target=self.run_command, args=(self.get_command_args(cmd), cmd, content, window, window.active_view().file_name()))
    t.start()

  def process_phpcbf_results(self, fixed_content, stderr_str, exit_code, window, content):
    if stderr_str and exit_code not in [0, 1]:
      print("--- PHP CBF Error Output ---")
      print(stderr_str.strip())
      self.set_status_msg('PHP CBF: Error, check console for details.')
      return

    self.window    = window
    self.file_view = window.active_view()

    difftxt = self.run_diff(window, content, fixed_content)
    self.processed = True

    if not difftxt:
      return

    self.set_status_msg('');
    self.file_view.run_command('set_view_content', {'data':fixed_content, 'replace':True})

    if settings.get('fix_on_save') == True:
      self.file_view.settings().set('phpcbf_is_saving', True)
      self.file_view.run_command('save')

  def run_diff(self, window, origContent, fixed_content):
    try:
        a = origContent.splitlines()
        b = fixed_content.splitlines()
    except UnicodeDecodeError as e:
        sublime.status_message("Diff only works with UTF-8 files")
        return

    # Get the diff between original content and the fixed content.
    diff = difflib.unified_diff(a, b, 'Original', 'Fixed', lineterm='')
    difftxt = u"\n".join(line for line in diff)

    if difftxt == "":
      sublime.status_message('')
      return

    return difftxt

  def get_command_args(self, cmd_type):
    args = []
    project_folder = sublime.active_window().folders()[0]
    php_path = settings.get('php_path')
    phpcbf_path = settings.get('phpcbf_path')
    standard_setting = settings.get('phpcs_standard')
    standard = ''

    if php_path:
      args.append(php_path)
    elif os.name == 'nt':
      args.append('php')

    if phpcbf_path:
      phpcbf_path = phpcbf_path.replace('${folder}', project_folder)
      args.append(phpcbf_path)

    if type(standard_setting) is dict:
      for folder in self.window.folders():
        folder_name = os.path.basename(folder)
        if folder_name in standard_setting:
          standard = standard_setting[folder_name]
          break

      if standard == '' and '_default' in standard_setting:
        standard = standard_setting['_default']
    else:
      standard = standard_setting

    if settings.get('phpcs_standard'):
      standard = standard.replace('${folder}', project_folder)
      args.append('--standard=' + standard)

    args.append('-')

    if settings.get('additional_args'):
      args += settings.get('additional_args')

    return args

  def run_command(self, args, cmd, content, window, file_path):
    shell = False
    if os.name == 'nt':
      shell = True

    self.processed = False
    proc = subprocess.Popen(args, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

    if file_path:
      phpcs_content = 'phpcs_input_file: ' + file_path + "\n" + content
    else:
      phpcs_content = content

    if proc.stdout:

      stdout_data, stderr_data = proc.communicate(phpcs_content.encode('utf-8'))
      stdout_str = stdout_data.decode('utf-8')
      stderr_str = stderr_data.decode('utf-8')
      exit_code = proc.returncode
      sublime.set_timeout(lambda: self.process_phpcbf_results(stdout_str, stderr_str, exit_code, window, content), 0)

  def loading_msg(self, msg):
    sublime.set_timeout(lambda: self.show_loading_msg(msg), 0)

  def set_status_msg(self, msg):
    sublime.status_message(msg)

  def show_loading_msg(self, msg):
    if self.processed == True:
      return

    msg = msg[:-2]
    msg = msg + ' ' + self.process_anim[sublime.platform()][self.process_anim_idx]

    self.process_anim_idx += 1;
    if self.process_anim_idx > (len(self.process_anim[sublime.platform()]) - 1):
      self.process_anim_idx = 0

    self.set_status_msg(msg)
    sublime.set_timeout(lambda: self.show_loading_msg(msg), 300)

# Init PHPCBF.
phpcbf = PHP_CBF()

"""
START SUBLIME TEXT
COMMANDS AND EVENTS
"""
class set_view_content(sublime_plugin.TextCommand):
    def run(self, edit, data, replace=False):
      if replace == True:
        self.view.replace(edit, sublime.Region(0, self.view.size()), data)
      else:
        self.view.insert(edit, 0, data)

class PhpcbfCommand(sublime_plugin.WindowCommand):
  def run(self):
    phpcbf.run(self.window, 'Running PHPCS Fixer  ')

class PhpcbfEventListener(sublime_plugin.EventListener):
  def on_post_save(self, view):
    if view.settings().get('phpcbf_is_saving', False):
      view.settings().erase('phpcbf_is_saving')
      return

    if not view.file_name():
      return

    self.filename = os.path.basename(view.file_name())
    if (
        self.filename.endswith('.php') == True and
        self.filename.startswith('.') == False and
        settings.get('fix_on_save') == True
      ):
        sublime.active_window().run_command("phpcbf")
        return
