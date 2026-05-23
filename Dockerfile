FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    asymptote \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    ghostscript \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]