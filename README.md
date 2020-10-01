PHP_CBF for Sublime Text 3/4
========================================

This is a lightweight ST Package to fix your php files with [PHP Codebeautifier](https://github.com/squizlabs/PHP_CodeSniffer/wiki/Fixing-Errors-Automatically) aka `phpcbf`. It is based on the original [PHP_CodeSniffer](https://github.com/andremacola/sublime-PHP_CodeSniffer) package without the `phpcs`.

The advantage of this plugin is that it acts directly in the Sublime Text buffer, avoiding file reloading thus being faster.

For linting your code, please use [Sublimelinter-phpcs](https://packagecontrol.io/packages/SublimeLinter-phpcs). It is a more modern package for the purpose.

Installation
--------------

### Install via Package Control

Not available yet

### Cloning the repository

- Clone the PHP_CBF Sublime Text Plugin in to ST3/ST4 Packages directory.
```
git clone https://github.com/andremacola/PHP_CBF PHP_CBF
```
- Packages directory locations:
```
Mac: /Users/{user}/Library/Application Support/Sublime Text 3/Packages
Windows: C:\Users\{user}\AppData\Roaming\Sublime Text 3\Packages
Linux: ~/.config/sublime-text-3/Packages
```

Configuration
--------------
Configuration files can be opened via Preferences > Package Settings > PHP_CBF.

Make sure the php_path and phpcbf_path paths are correct. E.g.
```
"phpcs_path": "/usr/local/bin/phpcs",
"phpcbf_path": "/usr/local/bin/phpcbf",
```


**phpcs_standard**

This settings can be the name of a single standard or a list of folder/project names and the standard to be used for each project. E.g.

```json
"phpcs_standard": "Squiz"
```
```json
// sublime-project
"settings": {
    "PHP_CBF": {
        "fix_on_save": true,
        "phpcs_standard": "~/my_project/phpcs.xml"
    }
}
```

**additional_args**

Array containing additional arguments to pass to the PHPCS/PHPCBF scripts.

**fix_on_save**

If set to *true* then buffer will be checked and fixed on each save.

Usage
--------
There are one shortcut that can be used for Sublime PHP_CBF plugin:
- **ALT + SHIFT + S**: Runs PHPCBF command for the open buffer.

These commands are also available in Tools > PHP_CBF menu.
