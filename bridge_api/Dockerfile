# 1. Elegimos una imagen base oficial de Python (ligera)
FROM python:3.11-slim

# Instalamos el cliente SSH para poder comunicarnos con el anfitrión
RUN apt-get update && apt-get install -y openssh-client p7zip-full sqlite3 && rm -rf /var/lib/apt/lists/*

# 2. Le decimos a Docker: "A partir de ahora, trabaja en esta carpeta dentro del contenedor"
WORKDIR /app

# 3. Copiamos el archivo de dependencias desde tu PC al contenedor
COPY requirements.txt .

# 4. Instalamos las dependencias de Python adentro del contenedor
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos el resto de tu código (main.py) al contenedor
COPY . .

# 6. Exponemos el puerto 8000 para poder comunicarnos con la API
EXPOSE 8000

# 7. El comando final que se ejecutará cuando el contenedor arranque (idéntico al que usaste)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]