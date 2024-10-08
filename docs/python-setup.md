# Python Setup Instructions

## Why using virutal environments?
Using virtual environments in the context of the bebelbetes project is highly recommended when installing modules via pip install -r requirements.txt. It ensures that all dependencies listed in the requirements.txt file are isolated to the bebelbetes project. This prevents conflicts with other projects that might require different versions of the same modules, and it keeps your system-wide Python environment clean. Additionally, it allows easy replication of the project’s environment on other systems, ensuring consistency across development setups.

## macOS
We recommend using both `pyenv` and `virtualenv` packages to manage virtual enviroments.
- **pyenv** manages multiple Python versions: This allows you to install and switch between different versions of Python system-wide.
- **virtualenv** creates isolated project environments: Each virtual environment has its own set of Python packages, isolating your project's dependencies and preventing conflicts with other projects or the system-wide Python installation.
- This allows switching between different versions of Python without affecting your current projects and working on projects that have different requirements (e.g., an older version of modules such as pandas).

1. Installing pyenv
- Install brew (if you don’t have it yet): [https://docs.brew.sh/Installation](https://docs.brew.sh/Installation)
- Install pyenv using brew:
  ```bash
  brew install pyenv
  ```

2. Installing Python
- List available versions using:
  ```bash
  pyenv versions
  ```
- Install a specific version using:
  ```bash
  pyenv install <version>  # e.g. pyenv install 3.9.6
  ```
- Note: You may need to install these dependencies before installing Python:
  ```bash
  brew install openssl readline sqlite3 xz zlib
  ```

3. Setting the global Python version
- Set a specific version as the global version using:
  ```bash
  pyenv global <version>  # e.g. pyenv global 3.9.6
  ```

4. Using pyenv with your shell (here, zsh)
- Add pyenv to your shell configuration:
  ```bash
  echo 'eval "$(pyenv init --path)"' >> ~/.zprofile
  echo 'eval "$(pyenv init -)"' >> ~/.zshrc
  ```

5. Installing the pyenv-virtualenv extension
- This extension allows you to create virtual environments using pyenv:
  ```bash
  brew install pyenv-virtualenv
  ```

6. Creating a virtual environment
- Create a virtual environment for a specific Python version and name:
  ```bash
  pyenv virtualenv <version> <name>  # e.g. pyenv virtualenv 3.9.6 my_env
  ```

7. Activating and deactivating a virtual environment (in shell)
- Activate a virtual environment:
  ```bash
  pyenv activate <environment name>  # e.g. pyenv activate my_env
  ```

8. Installing Python modules from a requirements.txt
- Make sure your virtual environment is activated (see step 7).
- Install the required modules using:
  ```bash
  pip install -r requirements.txt
  ```

## Windows

1. Ensure Python is installed: 
```bash 
python --version
```
If needed, install Python and ensure “Add Python to PATH” is checked.

2. Navigate to your project directory: `bash cd C:\path\to\your\project`
3. Create a virtual environment named babelbetes`bash python -m venv babelbetes`
4. Activate the babelbetes virtual environment:
```bash 
babelbetes\Scripts\activate
```
5. Install packages from requirements.txt :
```bash 
pip install -r requirements.txt
```
6. Install packages from requirements.txt : 
```bash 
pip install -r requirements.txt
```
7. Deactivate the virtual environment: 
```bash 
deactivate
```

That’s it! Now you’re working with the babelbetes virtual environment and can easily activate or switch to it when needed.