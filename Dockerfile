FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

EXPOSE 5000
ENV PYTHONUNBUFFERED=1

# Healthcheck without curl (executes a short Python snippet)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["bash", "-lc", "python -c \"import urllib.request,sys,socket; socket.setdefaulttimeout(3); r=urllib.request.urlopen('http://127.0.0.1:5000/health'); sys.exit(0 if r.status==200 else 1)\""]

# Gunicorn cmd (prod)
CMD ["gunicorn", "-w", "2", "-k", "gthread", "--threads", "8", \
     "-b", "0.0.0.0:5000", "--timeout", "45", "--graceful-timeout", "15", \
     "--access-logfile", "-", "--error-logfile", "-", "app:app"]
