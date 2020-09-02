PHP_CBF for Sublime Text 3/4
========================================





Installation
--------------
- Install [PHP_CBF](https://github.com/andremacola/PHP_CBF).
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
```
"phpcs_standard": "Squiz"
```
```
"phpcs_standard": {
    "PHP_CodeSniffer": "PHPCS",
    "php-sikuli": "PSR1",
    "Sublime-PHP_CodeSniffer": "PEAR"
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
