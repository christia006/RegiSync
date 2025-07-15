from app import create_app
import logging

# Konfigurasi logging dasar
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)