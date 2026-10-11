FROM python:3.11-slim

RUN adduser --system --no-create-home user

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bank_slip_fake.py .

USER user
EXPOSE 8080

CMD ["uvicorn", "bank_slip_fake:app", "--host", "0.0.0.0", "--port", "8080", "--no-server-header"]
