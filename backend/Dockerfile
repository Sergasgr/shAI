FROM python:3.12-slim
WORKDIR /app
RUN pip install fastapi uvicorn pydantic prometheus-client
COPY . .
EXPOSE 8000
CMD ["uvicorn", "controller:app", "--host", "0.0.0.0", "--port", "8000"]