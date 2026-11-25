Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "F:\Antigravity\iptime"
WshShell.Run "python -m streamlit run app.py --server.port 3088 --server.headless true", 0, False
