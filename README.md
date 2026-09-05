# Personalised Gym Session Generator

This Streamlit app creates personalised gym, conditioning, and HYROX-style workouts. Choose your time, training level, focus areas, and available equipment; save favourite sessions in the built-in Library; then download a workout as Markdown, PDF, or JPG.

## Start it

```powershell
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

It will open in a browser. Use the sidebar to select the session format, main-work duration, level, focus areas, available equipment, and format-specific targets. Warm-up and cool-down are additional time. Generate a new session whenever you want another variation.

The app intentionally filters exercises to those whose required equipment is selected. Bodyweight moves remain available without equipment.

## Privacy

Saved Library workouts are stored only in `workout_library.json` on the device running the app. That file is excluded from version control.
