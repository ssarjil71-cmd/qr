# LifeShield QR

Flask app for QR-based identity and emergency profiles.

Setup:

1. Create a Python virtualenv and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure MySQL credentials via environment variables or edit `config.py`.

3. Run migrations:

```bash
python migrate.py
```

4. Start the app:

```bash
python app.py
```
