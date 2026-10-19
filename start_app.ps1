$projectFolder = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectFolder
python -m streamlit run streamlit_app.py
