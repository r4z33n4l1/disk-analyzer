# 📊 Disk Analyzer

A simple, fast, and beautiful tool to visualize your disk usage on macOS. It helps you find what's taking up space so you can clean it up.

![Disk Analyzer UI](https://i.imgur.com/placeholder-image.png)

## ✨ Features

- **Fast Scanning**: Quickly analyzes your disk usage.
- **Beautiful UI**: Explore your files in a clean, dark-mode web interface.
- **Tree View**: Navigate deeply nested folders easily.
- **Finder Shortcuts**: Automatically create shortcuts to your largest files (optional).
- **Open in Finder**: One-click access to files directly from the UI.
- **Secure**: Runs entirely locally on your machine. No data is sent anywhere.

## 🚀 Quick Start

### 1. Scan your disk
Run the analyzer script to scan your home folder (or any other folder).

```bash
# Scan your home folder (default)
python3 analyzer.py

# Scan a specific folder
python3 analyzer.py --path ~/Downloads
```

This creates a `disk-report.json` file with your usage data.

### 2. View the results
Start a simple web server to view the interface:

```bash
python3 -m http.server 8000
```

👉 **Open [http://localhost:8000](http://localhost:8000) in your browser.**

---

## 🛠 Advanced Options

### Generate Shortcuts for Large Files
Want to easily delete the biggest space hogs? Generate 50 shortcuts to the largest files/folders:

```bash
python3 analyzer.py --shortcuts 50
```
Check the `shortcuts/` folder created in this directory. Double-click any shortcut to reveal the file in Finder.

**⚠️ Note:** Running this command wipes the `shortcuts/` directory before regenerating them. Do not store personal files there!

### Scan Deeper
By default, it scans 3 levels deep. To go deeper:

```bash
python3 analyzer.py --depth 5
```

## ❓ Troubleshooting

- **"Failed to Load Report"**: Make sure you started the server (`python3 -m http.server 8000`) and are not just opening the HTML file directly.
- **Permission Denied**: Some system folders require full disk access. The script will skip them and mark them as "🔒".

## 🔒 Security

- **Local Only**: This tool reads file sizes and paths. It does NOT read file contents.
- **Safe**: No data leaves your computer.
- **Caution**: The `--shortcuts` option deletes the `./shortcuts` folder. Keep your own files out of there!

## 📄 License

MIT License. Free to use and modify.
