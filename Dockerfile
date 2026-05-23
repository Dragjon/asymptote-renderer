FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    asymptote \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    ghostscript \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

EXPOSE 8080

CMD ["python", "app.py"]