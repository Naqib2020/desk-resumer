# Contributing to DeskResumer

Thank you for your interest in contributing to DeskResumer! We welcome contributions to core Python modules, the Apple SwiftUI Menu Bar app, the Windows C# Tray app, and documentation.

---

## 🛠️ Development Setup

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/Naqib2020/desk-resumer.git
cd desk-resumer

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### 2. Running Unit Tests
DeskResumer uses standard `unittest` with zero extra dependencies required:
```bash
python3 -m unittest discover tests
```
All unit tests should pass with 100% success before submitting pull requests.

---

## 🍎 macOS Menu Bar App (SwiftUI)

The macOS frontend is a native Apple SwiftUI application compiled with `/usr/bin/swiftc` (no heavy Xcode project required):
```bash
# Rebuild the macOS .app bundle
./apps/macos-menubar/build-macos.sh

# Launch the menu bar app
./run-macos-menubar.sh
```

---

## 🪟 Windows System Tray App (C# / .NET)

The Windows frontend is built using standard .NET Windows Forms / WPF:
```cmd
cd apps\windows-tray
build-windows.bat
```

---

## 📋 Pull Request Guidelines

1. **Keep it Native**: Avoid adding heavy Electron, WebViews, or non-native UI toolkits. DeskResumer prides itself on being ultra-lightweight and native.
2. **Preserve Compatibility**: Keep the Python core compatible with Python 3.10+.
3. **Write Tests**: When adding new rate-limit regex patterns or queue features, add corresponding tests under `tests/`.
4. **Adhere to Code Style**:
   - Python: Follow PEP 8 guidelines.
   - Swift: Follow Apple Swift conventions with SwiftUI best practices.

---

## ⚖️ License
By contributing to DeskResumer, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
