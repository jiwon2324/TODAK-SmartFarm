FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 TZ=Asia/Seoul
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY todak_sim ./todak_sim
COPY tests ./tests
RUN useradd -r -u 1001 sim
USER sim
CMD ["python", "-m", "todak_sim"]
