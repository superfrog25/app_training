# Personalised Gym Session Generator

This Streamlit app adapts the circuit, EMOM, HYROX-simulation, exercise-pool and randomisation ideas in the supplied notebook into a usable web app.

## Start it

```powershell
cd "wd"
python -m pip install -r requirements.txt
streamlit run app.py
```

It will open in a browser. Use the sidebar to select the session format, duration, level, focus areas, available equipment, and format-specific targets. “Generate a new session” makes another variation, and the download button saves the result as Markdown.

The app intentionally filters exercises to those whose required equipment is selected. Bodyweight moves remain available without equipment.
