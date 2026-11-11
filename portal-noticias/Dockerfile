FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORTAL_DADOS=/dados TZ=America/Sao_Paulo
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY briefing ./briefing
RUN useradd --create-home --uid 1000 briefing && mkdir -p /dados && chown briefing /dados
USER briefing
VOLUME ["/dados"]
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/saude', timeout=5)"
CMD ["python", "-m", "briefing", "servidor", "--porta", "8000"]
